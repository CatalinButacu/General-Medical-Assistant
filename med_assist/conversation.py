"""Conversation orchestrator.

Flow (top to bottom):

  1. Red-flag scan on the last user message. Emergencies short-circuit.
  2. Intent classification. Two branches:
       • MEDICINE_LOOKUP → explain branch: emit the matched medicine and
         have the LLM describe it using only its RCP sections. NO symptom
         questions — this is the bug `IntentClassifier` exists to fix.
       • SYMPTOM_TRIAGE  → existing followup-or-recommend loop.

  3. Inside SYMPTOM_TRIAGE: cumulative-query retrieval, then either ask
     the next followup or recommend an OTC.

Each branch yields the same event vocabulary so the SSE consumer can stay
naive: `intent`, `triage`, `medicines`, `token`, `done`, `error`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Awaitable, Callable, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from med_assist.data.models import Medicine, MedicineHit
from med_assist.intent import IntentClassifier, IntentResult
from med_assist.llm.client import GeminiClient, build_history
from med_assist.llm.prompts import (
    render_explain,
    render_followup,
    render_recommend,
    retrieval_hint_from_hits,
)
from med_assist.profile import UserProfile
from med_assist.service import RetrievalService
from med_assist.triage.classifier import TriageDecision
from med_assist.triage.redflags import RedFlag, has_emergency, has_urgent
from med_assist.triage.redflags import scan as scan_redflags

log = logging.getLogger("medassist.chat")

MAX_HISTORY_TURNS = 8
TOP_K_MEDICINES = 5
# Both profile and non-profile users now hit the same minimum. The previous
# 3-turn gate for anonymous users was an over-correction — the 1-turn jump
# from 2 → 3 forced a 50% interrogation tax for marginal safety gain. The
# red-flag scan still fires every turn, so emergencies short-circuit either
# way; the MAX_FOLLOWUPS=4 cap still bounds the loop.
MIN_FOLLOWUPS_NO_PROFILE = 2
MIN_FOLLOWUPS_WITH_PROFILE = 2
MAX_FOLLOWUPS = 4
STRONG_CONFIDENCE = 0.5
MEDICINE_LOOKUP_MIN_CONFIDENCE = 0.7


# When the first user turn lands in one of these categories, force the
# first followup question to ask about the trigger of this episode rather
# than letting the LLM pick.
FORCED_FIRST_FOLLOWUP_BY_CATEGORY: dict[str, str] = {
    "alergii": (
        "Întrebare OBLIGATORIE: ce a declanșat reacția alergică acum — mâncare, plantă "
        "(polen, păr de animal), medicament, înțepătură de insectă, sau contact cu "
        "o substanță (detergent, cosmetic)? Fără această informație nu putem decide "
        "între un antihistaminic OTC și o evaluare medicală urgentă. Dacă utilizatorul "
        "menționează deja respirație dificilă, umflare a feței/gâtului, sau amețeală, "
        "NU întreba despre trigger — direcționează imediat la 112."
    ),
}


class ChatMessageIn(BaseModel):
    role: str
    text: str


class ChatStreamEvent(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    kind: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ConversationOutcome(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    triage: TriageDecision
    medicines: list[MedicineHit] = Field(default_factory=list)
    full_text: str = ""
    used_llm: bool = True
    error: Optional[str] = None


class AuditRecord(BaseModel):
    """One turn's full forensic context. Written to `triage_audit_log` for
    compliance / 'why did the model say X' debugging. Fields mirror the DB
    schema 1:1; see db/schema.sql."""

    user_id: Optional[str] = None
    request_id: Optional[str] = None
    user_input: str
    retrieved: list[dict] = Field(default_factory=list)
    triage_label: Optional[str] = None
    red_flags: list[str] = Field(default_factory=list)
    intent_label: Optional[str] = None
    intent_confidence: Optional[float] = None
    phase: Optional[str] = None
    assistant_output: Optional[str] = None
    citation_valid: Optional[bool] = None


# A sink that the orchestrator calls once per turn with the populated record.
# Sync callables get called inline; async ones are awaited. Errors are caught
# and logged — a broken audit sink must never break the chat.
AuditSink = Callable[[AuditRecord], Union[None, Awaitable[None]]]


def _check_citation(text: Optional[str], medicines: list[Medicine]) -> Optional[bool]:
    """Did the LLM's reply mention at least one retrieved medicine?

    Substring match (case-insensitive) on trade_name, DCI, or ATC code.
    Returns None when there are no medicines (followup / emergency), so the
    caller can leave citation_valid as 'not applicable' in those phases.
    """
    if not medicines:
        return None
    body = (text or "").lower()
    if not body.strip():
        return False
    for med in medicines:
        if med.trade_name and med.trade_name.lower() in body:
            return True
        if med.dci and len(med.dci) > 3 and med.dci.lower() in body:
            return True
        if med.atc_code and med.atc_code.lower() in body:
            return True
    return False


def _retrieved_for_audit(hits: list[MedicineHit]) -> list[dict]:
    return [
        {
            "medicine_id": h.medicine.id,
            "trade_name": h.medicine.trade_name,
            "atc_code": h.medicine.atc_code,
            "score": float(h.score),
        }
        for h in hits
    ]


# SSE payload contracts mirrored 1:1 by src/types/index.ts. Constructing them as
# typed models (rather than free-form dicts) catches field drift between the
# orchestrator and the frontend at boundary time, not at the next manual test.


class RedFlagPayload(BaseModel):
    name: str
    category: str
    description: str
    severity: str
    matched_pattern: str

    @classmethod
    def from_red_flag(cls, rf: RedFlag) -> "RedFlagPayload":
        return cls(
            name=rf.name,
            category=rf.category,
            description=rf.description,
            severity=str(rf.severity),
            matched_pattern=rf.matched_pattern,
        )


class IntentPayload(BaseModel):
    label: str
    confidence: float
    matched_terms: list[str]
    rationale: str
    medicine_trade_name: Optional[str]

    @classmethod
    def from_intent(cls, intent: IntentResult) -> "IntentPayload":
        return cls(
            label=intent.label,
            confidence=float(intent.confidence),
            matched_terms=list(intent.matched_terms),
            rationale=intent.rationale,
            medicine_trade_name=intent.medicine.trade_name if intent.medicine else None,
        )


class MedicineCardPayload(BaseModel):
    medicine_id: str
    trade_name: str
    dci: str
    form: str
    concentration: str
    atc_code: str
    rx_status: str
    category: str
    lay_symptoms: list[str]
    score: float
    best_chunk_type: str
    best_chunk_snippet: str
    rcp_url: str
    prospect_url: str

    @classmethod
    def from_medicine_hit(cls, hit: MedicineHit) -> "MedicineCardPayload":
        med = hit.medicine
        return cls(
            medicine_id=med.id,
            trade_name=med.trade_name,
            dci=med.dci,
            form=med.form,
            concentration=med.concentration,
            atc_code=med.atc_code,
            rx_status=med.rx_status,
            category=med.category,
            lay_symptoms=list(med.lay_symptoms),
            score=float(hit.score),
            best_chunk_type=hit.best_chunk.chunk_type,
            best_chunk_snippet=hit.best_chunk.text[:300],
            rcp_url=med.rcp_url,
            prospect_url=med.prospect_url,
        )

    @classmethod
    def from_medicine(cls, med: Medicine) -> "MedicineCardPayload":
        """Compact card for the explain branch — no retrieval score."""
        return cls(
            medicine_id=med.id,
            trade_name=med.trade_name,
            dci=med.dci,
            form=med.form,
            concentration=med.concentration,
            atc_code=med.atc_code,
            rx_status=med.rx_status,
            category=med.category,
            lay_symptoms=list(med.lay_symptoms),
            score=1.0,
            best_chunk_type="lay_summary",
            best_chunk_snippet=(med.lay_description or "")[:300],
            rcp_url=med.rcp_url,
            prospect_url=med.prospect_url,
        )


def _coerce_profile(profile: Any) -> Optional[UserProfile]:
    """Accept None, a UserProfile, or a raw dict (legacy callers)."""
    if profile is None:
        return None
    if isinstance(profile, UserProfile):
        return profile
    if isinstance(profile, dict):
        return UserProfile.model_validate(profile)
    raise TypeError(f"Unsupported profile type: {type(profile).__name__}")


class ConversationService:
    def __init__(
        self,
        retrieval: RetrievalService,
        llm: GeminiClient,
        intent: Optional[IntentClassifier] = None,
        audit_sink: Optional[AuditSink] = None,
    ):
        self.retrieval = retrieval
        self.llm = llm
        # The intent classifier needs the medicine catalogue; pull it
        # from the retrieval service so callers don't have to thread it.
        self.intent = intent or IntentClassifier(retrieval.medicines())
        self.audit_sink = audit_sink

    @staticmethod
    def _trim_history(messages: list[ChatMessageIn]) -> list[ChatMessageIn]:
        return messages[-MAX_HISTORY_TURNS:] if len(messages) > MAX_HISTORY_TURNS else list(messages)

    async def _emit_audit(self, record: AuditRecord) -> None:
        """Call the audit sink (sync or async). Never raises."""
        if self.audit_sink is None:
            return
        try:
            result = self.audit_sink(record)
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            log.exception("audit_sink failed; record dropped (request_id=%s)", record.request_id)

    async def stream_turn(
        self,
        history: list[ChatMessageIn],
        profile: Any = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        skip_followups: bool = False,
    ) -> AsyncIterator[ChatStreamEvent]:
        if not history:
            yield ChatStreamEvent(kind="error", payload={"message": "empty history"})
            return

        last_user = next((m for m in reversed(history) if m.role == "user"), None)
        if last_user is None or not last_user.text.strip():
            yield ChatStreamEvent(kind="error", payload={"message": "no user message in history"})
            return

        typed_profile = _coerce_profile(profile)
        audit = AuditRecord(
            user_id=user_id,
            request_id=request_id,
            user_input=last_user.text,
        )

        # Step 1: red-flag scan ALWAYS runs first — even a medicine-lookup
        # query gets the emergency layer because a user could write
        # "am luat Aspirin si nu pot respira".
        flags = scan_redflags(last_user.text)
        if has_emergency(flags) or has_urgent(flags):
            primary = next(f for f in flags if f.severity in ("emergency", "urgent"))
            audit.phase = "emergency"
            audit.triage_label = "EMERGENCY"
            audit.red_flags = [f.name for f in flags]
            yield ChatStreamEvent(kind="triage", payload={
                "label": "EMERGENCY",
                "rationale": f"Detectat: {primary.description}.",
                "recommended_action_ro": primary.action_ro,
                "confidence": 0.0,
                "red_flags": [RedFlagPayload.from_red_flag(f).model_dump() for f in flags],
            })
            yield ChatStreamEvent(kind="done", payload={"used_llm": False, "phase": "emergency"})
            await self._emit_audit(audit)
            return

        # Step 2: intent classification on the LAST user turn.
        intent_result = self.intent.classify(last_user.text)
        audit.intent_label = intent_result.label
        audit.intent_confidence = float(intent_result.confidence)
        yield ChatStreamEvent(kind="intent", payload=IntentPayload.from_intent(intent_result).model_dump())

        if (
            intent_result.label == "MEDICINE_LOOKUP"
            and intent_result.medicine is not None
            and intent_result.confidence >= MEDICINE_LOOKUP_MIN_CONFIDENCE
        ):
            async for ev in self._handle_explain(
                history=history,
                medicine=intent_result.medicine,
                profile=typed_profile,
                audit=audit,
            ):
                yield ev
            await self._emit_audit(audit)
            return

        # Step 3: symptom-triage branch (legacy flow).
        async for ev in self._handle_symptom_triage(
            history=history,
            profile=typed_profile,
            audit=audit,
            skip_followups=skip_followups,
        ):
            yield ev
        await self._emit_audit(audit)

    async def _handle_explain(
        self,
        *,
        history: list[ChatMessageIn],
        medicine: Medicine,
        profile: Optional[UserProfile],
        audit: AuditRecord,
    ) -> AsyncIterator[ChatStreamEvent]:
        """Emit the medicine card and stream a grounded explanation."""
        audit.phase = "explain"
        audit.retrieved = [{
            "medicine_id": medicine.id,
            "trade_name": medicine.trade_name,
            "atc_code": medicine.atc_code,
            "score": 1.0,
        }]

        yield ChatStreamEvent(kind="medicines", payload={
            "items": [MedicineCardPayload.from_medicine(medicine).model_dump()],
        })

        system = render_explain(medicine=medicine, profile=profile)
        parts: list[str] = []
        async for ev in self._stream_llm_yielding(history=history, system=system, output_accumulator=parts):
            yield ev
        audit.assistant_output = "".join(parts)
        audit.citation_valid = _check_citation(audit.assistant_output, [medicine])
        if audit.citation_valid is False:
            log.warning(
                "citation_valid=False on explain phase (medicine=%s request_id=%s)",
                medicine.trade_name, audit.request_id,
            )
        yield ChatStreamEvent(kind="done", payload={
            "used_llm": True,
            "phase": "explain",
            "citation_valid": audit.citation_valid,
            "request_id": audit.request_id,
        })

    async def _handle_symptom_triage(
        self,
        *,
        history: list[ChatMessageIn],
        profile: Optional[UserProfile],
        audit: AuditRecord,
        skip_followups: bool = False,
    ) -> AsyncIterator[ChatStreamEvent]:
        user_messages = [m for m in history if m.role == "user"]
        user_turn_count = len(user_messages)

        cumulative_query = " ".join(m.text for m in user_messages).strip()
        decision = self.retrieval.advise(
            cumulative_query,
            top_k_medicines=TOP_K_MEDICINES,
            otc_only=True,
        )
        audit.retrieved = _retrieved_for_audit(decision.medicine_hits)
        audit.red_flags = [f.name for f in decision.red_flags]

        has_profile = profile is not None and profile.has_meaningful_data()
        min_followups = MIN_FOLLOWUPS_WITH_PROFILE if has_profile else MIN_FOLLOWUPS_NO_PROFILE
        strong_match = decision.label == "OTC_SAFE" and decision.confidence >= STRONG_CONFIDENCE
        hit_cap = user_turn_count >= MAX_FOLLOWUPS
        # User can request to skip remaining followups once they've answered
        # at least one question. The MIN_FOLLOWUPS gate stays at 1+ to ensure
        # we never recommend on a single ambiguous opener. Red-flag scan and
        # intent classification still run before this branch — the skip flag
        # only short-circuits the 'keep asking until confidence is strong'
        # loop, never the safety layers.
        force_skip = skip_followups and user_turn_count >= max(1, min_followups)
        in_followup_phase = (
            (user_turn_count < min_followups or not (strong_match or hit_cap))
            and not force_skip
        )

        if in_followup_phase:
            audit.phase = "followup"
            audit.triage_label = "FOLLOWUP"
            yield ChatStreamEvent(kind="triage", payload={
                "label": "FOLLOWUP",
                "rationale": f"Colectare informații (întrebarea {user_turn_count}, prag {min_followups}).",
                "recommended_action_ro": "",
                "confidence": float(decision.confidence),
                "red_flags": [RedFlagPayload.from_red_flag(f).model_dump() for f in decision.red_flags],
            })
            user_history_text = [m.text for m in user_messages]
            forced_topic = (
                _forced_first_followup(decision.medicine_hits)
                if user_turn_count == 1
                else None
            )
            system = render_followup(
                user_history_text=user_history_text,
                profile=profile,
                retrieval_hint=retrieval_hint_from_hits(decision.medicine_hits),
                forced_topic=forced_topic,
            )
            parts: list[str] = []
            async for ev in self._stream_llm_yielding(history=history, system=system, output_accumulator=parts):
                yield ev
            audit.assistant_output = "".join(parts)
            # Followups don't recommend; citation_valid stays None.
            yield ChatStreamEvent(kind="done", payload={"used_llm": True, "phase": "followup"})
            return

        audit.phase = "recommend"
        audit.triage_label = decision.label
        yield ChatStreamEvent(kind="triage", payload={
            "label": decision.label,
            "rationale": decision.rationale,
            "recommended_action_ro": decision.recommended_action_ro,
            "confidence": float(decision.confidence),
            "red_flags": [RedFlagPayload.from_red_flag(f).model_dump() for f in decision.red_flags],
        })
        if strong_match:
            medicines_payload = [
                MedicineCardPayload.from_medicine_hit(h).model_dump()
                for h in decision.medicine_hits
            ]
            yield ChatStreamEvent(kind="medicines", payload={"items": medicines_payload})
            system = render_recommend(
                hits=decision.medicine_hits,
                profile=profile,
                forced_low_confidence=False,
            )
        else:
            system = render_recommend(
                hits=[],
                profile=profile,
                forced_low_confidence=True,
            )
        parts = []
        async for ev in self._stream_llm_yielding(history=history, system=system, output_accumulator=parts):
            yield ev
        audit.assistant_output = "".join(parts)
        audit.citation_valid = _check_citation(
            audit.assistant_output,
            [h.medicine for h in decision.medicine_hits] if strong_match else [],
        )
        if strong_match and audit.citation_valid is False:
            log.warning(
                "citation_valid=False on recommend phase — answer doesn't reference retrieved medicines "
                "(request_id=%s, hits=%d)", audit.request_id, len(decision.medicine_hits),
            )
        yield ChatStreamEvent(kind="done", payload={
            "used_llm": True,
            "phase": "recommend",
            "citation_valid": audit.citation_valid,
            "request_id": audit.request_id,
        })

    async def _stream_llm_yielding(
        self,
        history: list[ChatMessageIn],
        system: str,
        output_accumulator: Optional[list[str]] = None,
    ) -> AsyncIterator[ChatStreamEvent]:
        trimmed = self._trim_history(history)
        contents = build_history([{"role": m.role, "text": m.text} for m in trimmed])
        try:
            async for chunk in self.llm.stream(system_instruction=system, contents=contents):
                if output_accumulator is not None:
                    output_accumulator.append(chunk)
                yield ChatStreamEvent(kind="token", payload={"text": chunk})
        except Exception as exc:
            log.exception("LLM stream failed")
            yield ChatStreamEvent(kind="error", payload={"message": str(exc)[:200]})


def _forced_first_followup(hits: list[MedicineHit]) -> str | None:
    """Substring match on the top-3 medicines' category (case-insensitive)."""
    for hit in hits[:3]:
        cat = (hit.medicine.category or "").lower()
        if not cat:
            continue
        for key, directive in FORCED_FIRST_FOLLOWUP_BY_CATEGORY.items():
            if key in cat:
                return directive
    return None
