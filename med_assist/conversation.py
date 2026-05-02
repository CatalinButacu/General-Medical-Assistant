"""
Conversation orchestrator — wraps RetrievalService.advise() with an LLM
turn that produces natural Romanian text grounded in retrieved evidence.

Flow per user turn:
  1. Triage red-flag scan on the latest user message.
     -> EMERGENCY  : skip LLM entirely, return decision verbatim.
  2. Run retrieval to get top-K candidate medicines.
  3. Stream LLM response with evidence in system prompt + last N turns
     of conversation history.
  4. Assemble structured medicine list to attach to the assistant turn.

The /chat endpoint consumes this as a generator and yields SSE events.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

from med_assist.data.models import MedicineHit
from med_assist.llm.client import GeminiClient, build_history
from med_assist.llm.prompts import system_followup, system_with_evidence
from med_assist.service import RetrievalService
from med_assist.triage.classifier import TriageDecision
from med_assist.triage.redflags import scan as scan_redflags, has_emergency, has_urgent

log = logging.getLogger(__name__)

MAX_HISTORY_TURNS = 6              # last N turns sent to the LLM (user+assistant counted as 2)
TOP_K_MEDICINES = 5                # candidates handed to LLM and shown as cards in UI
MIN_USER_TURNS_BEFORE_RECOMMEND = 3  # 2 follow-up questions, then recommend on turn 3


@dataclass
class ChatMessageIn:
    role: str       # 'user' | 'assistant'
    text: str


@dataclass
class ChatStreamEvent:
    """One streamed event sent over SSE to the frontend."""
    kind: str       # 'triage' | 'token' | 'medicines' | 'done' | 'error'
    payload: dict


@dataclass
class ConversationOutcome:
    """Final state captured after the stream closes (for telemetry / logging)."""
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
    ) -> AsyncIterator[ChatStreamEvent]:
        if not history:
            yield ChatStreamEvent("error", {"message": "empty history"})
            return

        last_user = next((m for m in reversed(history) if m.role == "user"), None)
        if last_user is None or not last_user.text.strip():
            yield ChatStreamEvent("error", {"message": "no user message in history"})
            return

        user_turn_count = sum(1 for m in history if m.role == "user")
        in_followup_phase = user_turn_count < MIN_USER_TURNS_BEFORE_RECOMMEND

        # --- Step 1: red-flag scan ALWAYS runs first, regardless of phase.
        # Even mid-conversation, an emergency mention bypasses everything.
        flags = scan_redflags(last_user.text)
        if has_emergency(flags) or has_urgent(flags):
            primary = next(f for f in flags if f.severity in ("emergency", "urgent"))
            yield ChatStreamEvent("triage", {
                "label": "EMERGENCY",
                "rationale": f"Detectat: {primary.description}.",
                "recommended_action_ro": primary.action_ro,
                "confidence": 0.0,
                "red_flags": [
                    {
                        "name": f.name, "category": f.category,
                        "description": f.description, "severity": f.severity,
                        "matched_pattern": f.matched_pattern,
                    }
                    for f in flags
                ],
            })
            yield ChatStreamEvent("done", {"used_llm": False, "phase": "emergency"})
            return

        # --- Step 2 (follow-up phase): no retrieval, no medicines, only ask a question.
        if in_followup_phase:
            yield ChatStreamEvent("triage", {
                "label": "FOLLOWUP",
                "rationale": f"Colectare informații (întrebarea {user_turn_count}/2).",
                "recommended_action_ro": "",
                "confidence": 0.0,
                "red_flags": [],
            })
            async for ev in self._stream_llm_yielding(
                history=history,
                system=system_followup(turn_index=user_turn_count),
            ):
                yield ev
            yield ChatStreamEvent("done", {"used_llm": True, "phase": "followup"})
            return

        # --- Step 3 (recommendation phase): full retrieval + grounded LLM.
        # Concatenate ALL user turns so retrieval sees the accumulated context
        # ("burta + de două zile + diaree fără febră"), not just the last reply.
        # Mitigates BM25's lack of negation handling and surfaces the dominant
        # symptom theme.
        retrieval_query = " ".join(m.text for m in history if m.role == "user").strip()
        decision = self.retrieval.advise(
            retrieval_query,
            top_k_medicines=TOP_K_MEDICINES,
            otc_only=True,
        )
        yield ChatStreamEvent("triage", {
            "label": decision.label,
            "rationale": decision.rationale,
            "recommended_action_ro": decision.recommended_action_ro,
            "confidence": decision.confidence,
            "red_flags": [
                {
                    "name": rf.name, "category": rf.category,
                    "description": rf.description, "severity": rf.severity,
                    "matched_pattern": rf.matched_pattern,
                }
                for rf in decision.red_flags
            ],
        })

        medicines_payload = [_medicine_to_dto(h) for h in decision.medicine_hits]
        yield ChatStreamEvent("medicines", {"items": medicines_payload})

        async for ev in self._stream_llm_yielding(
            history=history,
            system=system_with_evidence(decision.medicine_hits),
        ):
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
