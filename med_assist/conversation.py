"""Conversation orchestrator: red-flag scan -> retrieve -> followup or recommend -> stream LLM."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

from med_assist.data.models import MedicineHit
from med_assist.llm.client import GeminiClient, build_history
from med_assist.llm.prompts import (
    has_meaningful_profile,
    retrieval_hint_from_hits,
    system_followup,
    system_recommend,
)
from med_assist.service import RetrievalService
from med_assist.triage.classifier import TriageDecision
from med_assist.triage.redflags import has_emergency, has_urgent
from med_assist.triage.redflags import scan as scan_redflags

log = logging.getLogger(__name__)

MAX_HISTORY_TURNS = 8                   # last N turns sent to the LLM
TOP_K_MEDICINES = 5
MIN_FOLLOWUPS_NO_PROFILE = 2            # ask at least 2 questions if profile is empty
MIN_FOLLOWUPS_WITH_PROFILE = 1          # one is enough if we already know allergies/conditions
MAX_FOLLOWUPS = 4                       # hard cap — recommend even if uncertain after this
STRONG_CONFIDENCE = 0.5                 # OTC_SAFE label alone isn't enough — need score-backed confidence too


@dataclass
class ChatMessageIn:
    role: str       # 'user' | 'assistant'
    text: str


@dataclass
class ChatStreamEvent:
    kind: str       # 'triage' | 'token' | 'medicines' | 'done' | 'error'
    payload: dict


@dataclass
class ConversationOutcome:
    triage: TriageDecision
    medicines: list[MedicineHit] = field(default_factory=list)
    full_text: str = ""
    used_llm: bool = True
    error: Optional[str] = None


class ConversationService:
    def __init__(self, retrieval: RetrievalService, llm: GeminiClient):
        self.retrieval = retrieval
        self.llm = llm

    @staticmethod
    def _trim_history(messages: list[ChatMessageIn]) -> list[ChatMessageIn]:
        return messages[-MAX_HISTORY_TURNS:] if len(messages) > MAX_HISTORY_TURNS else list(messages)

    async def stream_turn(
        self,
        history: list[ChatMessageIn],
        profile: dict[str, Any] | None = None,
    ) -> AsyncIterator[ChatStreamEvent]:
        if not history:
            yield ChatStreamEvent("error", {"message": "empty history"})
            return

        last_user = next((m for m in reversed(history) if m.role == "user"), None)
        if last_user is None or not last_user.text.strip():
            yield ChatStreamEvent("error", {"message": "no user message in history"})
            return

        user_messages = [m for m in history if m.role == "user"]
        user_turn_count = len(user_messages)

        # Step 1: red flags short-circuit everything.
        flags = scan_redflags(last_user.text)
        if has_emergency(flags) or has_urgent(flags):
            primary = next(f for f in flags if f.severity in ("emergency", "urgent"))
            yield ChatStreamEvent("triage", {
                "label": "EMERGENCY",
                "rationale": f"Detectat: {primary.description}.",
                "recommended_action_ro": primary.action_ro,
                "confidence": 0.0,
                "red_flags": [_redflag_dto(f) for f in flags],
            })
            yield ChatStreamEvent("done", {"used_llm": False, "phase": "emergency"})
            return

        # Step 2: cumulative retrieval. Joins ALL user turns so we don't lose
        # earlier context like the original symptom when later turns add detail.
        cumulative_query = " ".join(m.text for m in user_messages).strip()
        decision = self.retrieval.advise(
            cumulative_query,
            top_k_medicines=TOP_K_MEDICINES,
            otc_only=True,
        )

        # Step 3: decide phase.
        min_followups = MIN_FOLLOWUPS_WITH_PROFILE if has_meaningful_profile(profile) else MIN_FOLLOWUPS_NO_PROFILE
        strong_match = decision.label == "OTC_SAFE" and decision.confidence >= STRONG_CONFIDENCE
        hit_cap = user_turn_count >= MAX_FOLLOWUPS

        in_followup_phase = (
            user_turn_count < min_followups
            or not (strong_match or hit_cap)
        )

        if in_followup_phase:
            yield ChatStreamEvent("triage", {
                "label": "FOLLOWUP",
                "rationale": f"Colectare informații (întrebarea {user_turn_count}, prag {min_followups}).",
                "recommended_action_ro": "",
                "confidence": float(decision.confidence),
                "red_flags": [_redflag_dto(f) for f in decision.red_flags],
            })
            user_history_text = [m.text for m in user_messages]
            system = system_followup(
                user_history_text=user_history_text,
                profile=profile,
                retrieval_hint=retrieval_hint_from_hits(decision.medicine_hits),
            )
            async for ev in self._stream_llm_yielding(history=history, system=system):
                yield ev
            yield ChatStreamEvent("done", {"used_llm": True, "phase": "followup"})
            return

        # Step 4: recommend. Two sub-cases:
        # - strong_match: emit medicine cards + grounded recommend prompt.
        # - hit_cap without strong_match: skip cards, force a graceful refusal.
        yield ChatStreamEvent("triage", {
            "label": decision.label,
            "rationale": decision.rationale,
            "recommended_action_ro": decision.recommended_action_ro,
            "confidence": float(decision.confidence),
            "red_flags": [_redflag_dto(f) for f in decision.red_flags],
        })
        if strong_match:
            medicines_payload = [_medicine_to_dto(h) for h in decision.medicine_hits]
            yield ChatStreamEvent("medicines", {"items": medicines_payload})
            system = system_recommend(
                hits=decision.medicine_hits,
                profile=profile,
                forced_low_confidence=False,
            )
        else:
            system = system_recommend(
                hits=[],
                profile=profile,
                forced_low_confidence=True,
            )
        async for ev in self._stream_llm_yielding(history=history, system=system):
            yield ev
        yield ChatStreamEvent("done", {"used_llm": True, "phase": "recommend"})

    async def _stream_llm_yielding(
        self,
        history: list[ChatMessageIn],
        system: str,
    ) -> AsyncIterator[ChatStreamEvent]:
        trimmed = self._trim_history(history)
        contents = build_history([{"role": m.role, "text": m.text} for m in trimmed])
        try:
            async for chunk in self.llm.stream(system_instruction=system, contents=contents):
                yield ChatStreamEvent("token", {"text": chunk})
        except Exception as exc:
            log.exception("LLM stream failed")
            yield ChatStreamEvent("error", {"message": str(exc)[:200]})


def _redflag_dto(rf) -> dict:
    return {
        "name": rf.name, "category": rf.category,
        "description": rf.description, "severity": rf.severity,
        "matched_pattern": rf.matched_pattern,
    }


def _medicine_to_dto(hit: MedicineHit) -> dict:
    med = hit.medicine
    return {
        "trade_name": med.trade_name,
        "dci": med.dci,
        "form": med.form,
        "concentration": med.concentration,
        "atc_code": med.atc_code,
        "rx_status": med.rx_status,
        "category": med.category,
        "lay_symptoms": med.lay_symptoms,
        "score": hit.score,
        "best_chunk_type": hit.best_chunk.chunk_type,
        "best_chunk_snippet": hit.best_chunk.text[:300],
        "rcp_url": med.rcp_url,
        "prospect_url": med.prospect_url,
    }
