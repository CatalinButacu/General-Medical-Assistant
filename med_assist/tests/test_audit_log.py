"""Audit-record and citation-validator behaviour.

The audit-log path is the project's compliance hook for the EU AI Act high-risk
obligations (every (input, retrieved context, output, rule fired) tuple must
be queryable). These tests pin the contract end-to-end through stream_turn()
because the load-bearing wire-ups (record population per phase, citation
substring match, sink invocation) are easy to break in a refactor."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from med_assist.conversation import (
    AuditRecord,
    ChatMessageIn,
    ConversationService,
    _check_citation,
)
from med_assist.data.models import Chunk, Medicine, MedicineHit
from med_assist.intent.types import IntentResult
from med_assist.triage.classifier import TriageDecision


def _aspirin() -> Medicine:
    return Medicine(
        id="A001",
        trade_name="Aspirin",
        dci="acid acetilsalicilic",
        form="COMPRIMATE",
        concentration="500 mg",
        atc_code="N02BA01",
        rx_status="OTC",
        category="Durere și inflamație",
        lay_description="Analgezic.",
        lay_symptoms=["durere", "febră"],
        rcp_sections={},
        rcp_url="", prospect_url="", therapeutic_action="",
        has_rcp_text=True, has_curated_atc=True,
    )


class _StubRetrieval:
    def __init__(self, meds, advise_decision=None):
        self._meds = list(meds)
        self._advise = advise_decision

    def medicines(self):
        return self._meds

    def advise(self, query, top_k_medicines=5, otc_only=True) -> TriageDecision:
        if self._advise is None:
            raise AssertionError("retrieval should not run for this test")
        return self._advise


class _StubLLM:
    def __init__(self, reply: str = "Aspirin (acid acetilsalicilic) este un analgezic.") -> None:
        self._reply = reply

    async def stream(self, *, system_instruction, contents, **kwargs) -> AsyncIterator[str]:
        yield self._reply


class _StubIntent:
    def __init__(self, result: IntentResult) -> None:
        self._result = result

    def classify(self, text: str) -> IntentResult:
        return self._result


def _drive_with_sink(history, retrieval, llm, intent=None, sink=None, user_id=None, request_id=None):
    convo = ConversationService(
        retrieval=retrieval, llm=llm, intent=intent, audit_sink=sink,  # type: ignore[arg-type]
    )

    async def collect():
        out = []
        async for ev in convo.stream_turn(
            history, user_id=user_id, request_id=request_id,
        ):
            out.append(ev)
        return out

    return asyncio.run(collect())


# ─── Citation validator (pure function) ───────────────────────────────


def test_citation_valid_when_trade_name_mentioned():
    assert _check_citation("Aspirin (acid acetilsalicilic) este un analgezic.", [_aspirin()]) is True


def test_citation_valid_when_dci_mentioned_without_trade_name():
    # The DCI is a generic drug name — citing it is still grounded evidence.
    assert _check_citation("Acid acetilsalicilic este indicat pentru durere.", [_aspirin()]) is True


def test_citation_valid_when_atc_code_mentioned():
    assert _check_citation("Cod ATC N02BA01 — analgezic.", [_aspirin()]) is True


def test_citation_invalid_when_answer_avoids_any_retrieved_medicine():
    text = "Pentru durere, încercați odihnă și hidratare. Consultați farmacistul."
    assert _check_citation(text, [_aspirin()]) is False


def test_citation_returns_none_when_no_medicines_retrieved():
    """Followup / emergency phases retrieve nothing — citation_valid stays N/A."""
    assert _check_citation("Care este simptomul principal?", []) is None


def test_citation_invalid_on_empty_or_whitespace_only_output():
    assert _check_citation("", [_aspirin()]) is False
    assert _check_citation("   \n  ", [_aspirin()]) is False


# ─── End-to-end audit-record population ───────────────────────────────


def test_audit_sink_invoked_with_emergency_phase_record():
    captured: list[AuditRecord] = []

    def sink(r: AuditRecord) -> None:
        captured.append(r)

    retrieval = _StubRetrieval([_aspirin()])
    llm = _StubLLM()
    history = [ChatMessageIn(role="user", text="am o durere puternică în piept și transpir")]

    _drive_with_sink(history, retrieval, llm, sink=sink, request_id="req-abc")

    assert len(captured) == 1
    rec = captured[0]
    assert rec.phase == "emergency"
    assert rec.triage_label == "EMERGENCY"
    assert rec.request_id == "req-abc"
    assert rec.user_input == history[0].text
    assert len(rec.red_flags) >= 1
    # No LLM was invoked, so no assistant_output and citation N/A.
    assert rec.assistant_output is None
    assert rec.citation_valid is None
    # Intent classification was short-circuited.
    assert rec.intent_label is None


def test_audit_sink_invoked_with_explain_phase_record_and_citation():
    captured: list[AuditRecord] = []

    def sink(r: AuditRecord) -> None:
        captured.append(r)

    retrieval = _StubRetrieval([_aspirin()])
    llm = _StubLLM(reply="Aspirin este un analgezic eficient pentru durere ușoară.")
    intent = _StubIntent(IntentResult(
        label="MEDICINE_LOOKUP",
        confidence=0.9,
        medicine=_aspirin(),
        matched_terms=["Aspirin"],
        rationale="stub",
    ))
    history = [ChatMessageIn(role="user", text="ce este Aspirin?")]

    _drive_with_sink(history, retrieval, llm, intent=intent, sink=sink, user_id="auth0|123")

    assert len(captured) == 1
    rec = captured[0]
    assert rec.phase == "explain"
    assert rec.intent_label == "MEDICINE_LOOKUP"
    assert rec.intent_confidence == 0.9
    assert rec.user_id == "auth0|123"
    assert rec.assistant_output and "Aspirin" in rec.assistant_output
    assert rec.citation_valid is True
    assert len(rec.retrieved) == 1
    assert rec.retrieved[0]["trade_name"] == "Aspirin"
    assert rec.retrieved[0]["atc_code"] == "N02BA01"


def test_audit_sink_records_uncited_recommend_as_invalid():
    """If the LLM stream produces a generic answer that doesn't mention any
    retrieved medicine, the audit flags it. This is the early-warning signal
    for ungrounded recommendations."""
    captured: list[AuditRecord] = []

    def sink(r: AuditRecord) -> None:
        captured.append(r)

    aspirin = _aspirin()
    hit = MedicineHit(
        medicine=aspirin,
        score=0.8,
        best_chunk=Chunk(id="A001_lay", medicine_id="A001", text="Analgezic.", chunk_type="lay_summary"),
        supporting_chunks=[],
    )
    retrieval = _StubRetrieval(
        [aspirin],
        advise_decision=TriageDecision(
            label="OTC_SAFE",
            rationale="strong match",
            recommended_action_ro="",
            confidence=0.8,
            red_flags=[],
            medicine_hits=[hit],
        ),
    )
    # Reply that deliberately avoids any retrieved medicine attribute.
    llm = _StubLLM(reply="Pentru durere ușoară, odihna și hidratarea sunt de obicei suficiente.")
    history = [
        ChatMessageIn(role="user", text="durere de cap"),
        ChatMessageIn(role="assistant", text="..."),
        ChatMessageIn(role="user", text="de două zile"),
        ChatMessageIn(role="assistant", text="..."),
        ChatMessageIn(role="user", text="continuă"),
        ChatMessageIn(role="assistant", text="..."),
        ChatMessageIn(role="user", text="continuă"),
    ]

    _drive_with_sink(history, retrieval, llm, sink=sink)

    assert len(captured) == 1
    rec = captured[0]
    assert rec.phase == "recommend"
    assert rec.triage_label == "OTC_SAFE"
    assert rec.citation_valid is False, "ungrounded answer must be flagged"


def test_sink_failure_is_swallowed_and_doesnt_break_chat():
    """A broken audit sink must never propagate — chat experience comes first."""
    def bad_sink(_r: AuditRecord) -> None:
        raise RuntimeError("DB down")

    retrieval = _StubRetrieval(
        [_aspirin()],
        advise_decision=TriageDecision(
            label="UNCERTAIN", rationale="stub", recommended_action_ro="",
            confidence=0.1, red_flags=[], medicine_hits=[],
        ),
    )
    llm = _StubLLM()
    history = [ChatMessageIn(role="user", text="durere de cap")]

    events = _drive_with_sink(history, retrieval, llm, sink=bad_sink)
    # The turn still completed normally (intent + symptom-triage followup).
    kinds = [ev.kind for ev in events]
    assert "intent" in kinds
    assert kinds[-1] == "done"
