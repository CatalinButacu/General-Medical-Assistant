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

import logging
from typing import Any, AsyncIterator, Optional

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
MIN_FOLLOWUPS_NO_PROFILE = 3
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
    ):
        self.retrieval = retrieval
        self.llm = llm
        # The intent classifier needs the medicine catalogue; pull it
        # from the retrieval service so callers don't have to thread it.
        self.intent = intent or IntentClassifier(retrieval.medicines())

    @staticmethod
    def _trim_history(messages: list[ChatMessageIn]) -> list[ChatMessageIn]:
        return messages[-MAX_HISTORY_TURNS:] if len(messages) > MAX_HISTORY_TURNS else list(messages)

    async def stream_turn(
        self,
        history: list[ChatMessageIn],
        profile: Any = None,
    ) -> AsyncIterator[ChatStreamEvent]:
        if not history:
            yield ChatStreamEvent(kind="error", payload={"message": "empty history"})
            return

        last_user = next((m for m in reversed(history) if m.role == "user"), None)
        if last_user is None or not last_user.text.strip():
            yield ChatStreamEvent(kind="error", payload={"message": "no user message in history"})
            return

        typed_profile = _coerce_profile(profile)

        # Step 1: red-flag scan ALWAYS runs first — even a medicine-lookup
        # query gets the emergency layer because a user could write
        # "am luat Aspirin si nu pot respira".
        flags = scan_redflags(last_user.text)
        if has_emergency(flags) or has_urgent(flags):
            primary = next(f for f in flags if f.severity in ("emergency", "urgent"))
            yield ChatStreamEvent(kind="triage", payload={
                "label": "EMERGENCY",
                "rationale": f"Detectat: {primary.description}.",
                "recommended_action_ro": primary.action_ro,
                "confidence": 0.0,
                "red_flags": [RedFlagPayload.from_red_flag(f).model_dump() for f in flags],
            })
            yield ChatStreamEvent(kind="done", payload={"used_llm": False, "phase": "emergency"})
            return

        # Step 2: intent classification on the LAST user turn.
        intent_result = self.intent.classify(last_user.text)
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
            ):
                yield ev
            return

        # Step 3: symptom-triage branch (legacy flow).
        async for ev in self._handle_symptom_triage(
            history=history,
            profile=typed_profile,
        ):
            yield ev

    async def _handle_explain(
        self,
        *,
        history: list[ChatMessageIn],
        medicine: Medicine,
        profile: Optional[UserProfile],
    ) -> AsyncIterator[ChatStreamEvent]:
        """Emit the medicine card and stream a grounded explanation."""
        yield ChatStreamEvent(kind="medicines", payload={
            "items": [MedicineCardPayload.from_medicine(medicine).model_dump()],
        })

        system = render_explain(medicine=medicine, profile=profile)
        async for ev in self._stream_llm_yielding(history=history, system=system):
            yield ev
        yield ChatStreamEvent(kind="done", payload={"used_llm": True, "phase": "explain"})

    async def _handle_symptom_triage(
        self,
        *,
        history: list[ChatMessageIn],
        profile: Optional[UserProfile],
    ) -> AsyncIterator[ChatStreamEvent]:
        user_messages = [m for m in history if m.role == "user"]
        user_turn_count = len(user_messages)

        cumulative_query = " ".join(m.text for m in user_messages).strip()
        decision = self.retrieval.advise(
            cumulative_query,
            top_k_medicines=TOP_K_MEDICINES,
            otc_only=True,
        )

        has_profile = profile is not None and profile.has_meaningful_data()
        min_followups = MIN_FOLLOWUPS_WITH_PROFILE if has_profile else MIN_FOLLOWUPS_NO_PROFILE
        strong_match = decision.label == "OTC_SAFE" and decision.confidence >= STRONG_CONFIDENCE
        hit_cap = user_turn_count >= MAX_FOLLOWUPS
        in_followup_phase = user_turn_count < min_followups or not (strong_match or hit_cap)

        if in_followup_phase:
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
            async for ev in self._stream_llm_yielding(history=history, system=system):
                yield ev
            yield ChatStreamEvent(kind="done", payload={"used_llm": True, "phase": "followup"})
            return

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
        async for ev in self._stream_llm_yielding(history=history, system=system):
            yield ev
        yield ChatStreamEvent(kind="done", payload={"used_llm": True, "phase": "recommend"})

    async def _stream_llm_yielding(
        self,
        history: list[ChatMessageIn],
        system: str,
    ) -> AsyncIterator[ChatStreamEvent]:
        trimmed = self._trim_history(history)
        contents = build_history([{"role": m.role, "text": m.text} for m in trimmed])
        try:
            async for chunk in self.llm.stream(system_instruction=system, contents=contents):
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
