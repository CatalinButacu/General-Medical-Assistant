"""End-to-end conversation flow: a medicine-lookup question takes the
explain branch and never falls into symptom-followup territory."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from med_assist.conversation import ChatMessageIn, ConversationService
from med_assist.data.models import Medicine
from med_assist.triage.classifier import TriageDecision


def _sinupret() -> Medicine:
    return Medicine(
        id="W001",
        trade_name="Sinupret",
        dci="extract plante",
        form="COMPRIMATE",
        concentration="filmate",
        atc_code="R05CA10",
        rx_status="OTC",
        category="Sinuzită",
        lay_description="Fitoterapeutic pentru tratamentul rinosinuzitei.",
        lay_symptoms=["nas înfundat", "sinuzită acută"],
        rcp_sections={
            "indications": "Tratamentul rinosinuzitei acute și cronice.",
            "contraindications": "Hipersensibilitate la oricare component.",
        },
        rcp_url="",
        prospect_url="",
        therapeutic_action="",
        has_rcp_text=True,
        has_curated_atc=True,
    )


class _StubRetrieval:
    """Looks like a RetrievalService for the parts ConversationService touches."""

    def __init__(self, meds: list[Medicine]) -> None:
        self._medicines_by_id = {m.id: m for m in meds}

    def advise(self, query, top_k_medicines=5, otc_only=True) -> TriageDecision:
        # The explain branch must not reach retrieval. Returning a stub
        # value here would falsely succeed — raise instead so we catch
        # mis-routing in the test.
        raise AssertionError("retrieval should not run during explain branch")


class _StubLLM:
    def __init__(self) -> None:
        self.last_system: str = ""

    async def stream(self, *, system_instruction, contents, **kwargs) -> AsyncIterator[str]:
        self.last_system = system_instruction
        yield "Sinupret este un fitoterapeutic pentru sinuzită."


def _drive(history: list[ChatMessageIn], retrieval, llm, profile=None) -> tuple[list, str]:
    convo = ConversationService(retrieval=retrieval, llm=llm)  # type: ignore[arg-type]

    async def collect():
        out = []
        async for ev in convo.stream_turn(history, profile=profile):
            out.append(ev)
        return out

    events = asyncio.run(collect())
    return events, llm.last_system


def test_medicine_lookup_takes_explain_branch_and_skips_symptom_questions():
    retrieval = _StubRetrieval([_sinupret()])
    llm = _StubLLM()
    history = [ChatMessageIn(role="user", text="ce este Sinupret?")]

    events, system_prompt = _drive(history, retrieval, llm)

    kinds = [ev.kind for ev in events]
    assert kinds[0] == "intent"
    assert events[0].payload["label"] == "MEDICINE_LOOKUP"
    assert "medicines" in kinds
    assert "token" in kinds
    assert kinds[-1] == "done"
    assert events[-1].payload["phase"] == "explain"

    # The followup prompt is the bug we're fixing — must NOT appear.
    assert "FAZA DE COLECTARE DE INFORMAȚII" not in system_prompt
    assert "FAZA: EXPLICARE MEDICAMENT" in system_prompt
    assert "Sinupret" in system_prompt


def test_medicine_card_emitted_for_explain_branch():
    retrieval = _StubRetrieval([_sinupret()])
    llm = _StubLLM()
    history = [ChatMessageIn(role="user", text="Sinupret")]

    events, _ = _drive(history, retrieval, llm)

    med_events = [ev for ev in events if ev.kind == "medicines"]
    assert len(med_events) == 1
    items = med_events[0].payload["items"]
    assert len(items) == 1
    assert items[0]["trade_name"] == "Sinupret"
    assert items[0]["dci"] == "extract plante"


def test_symptom_message_still_uses_legacy_followup_flow():
    """If the user describes symptoms (no medicine named), the explain
    branch must NOT run — we fall back to symptom triage. We can't drive
    that all the way through without a real retrieval index, so we just
    assert the intent classifier doesn't route to MEDICINE_LOOKUP."""
    retrieval = _StubRetrieval([_sinupret()])
    from med_assist.intent.classifier import IntentClassifier
    clf = IntentClassifier(retrieval._medicines_by_id.values())
    intent = clf.classify("mă doare capul de două zile")
    assert intent.label == "SYMPTOM_TRIAGE"
