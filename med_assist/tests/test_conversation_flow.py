"""End-to-end conversation flow: a medicine-lookup question takes the
explain branch and never falls into symptom-followup territory."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Optional

from med_assist.conversation import ChatMessageIn, ConversationService
from med_assist.data.models import Chunk, Medicine, MedicineHit
from med_assist.intent.types import IntentResult
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
    """Looks like a RetrievalService for the parts ConversationService touches.

    By default `advise()` raises — explain-branch tests expect retrieval to
    never run. Pass `advise_decision=...` to enable the symptom-triage branch.
    """

    def __init__(
        self,
        meds: list[Medicine],
        advise_decision: Optional[TriageDecision] = None,
    ) -> None:
        self._meds = list(meds)
        self._advise = advise_decision

    def medicines(self):
        return self._meds

    def advise(self, query, top_k_medicines=5, otc_only=True) -> TriageDecision:
        if self._advise is None:
            raise AssertionError("retrieval should not run during explain branch")
        return self._advise


class _StubLLM:
    def __init__(self) -> None:
        self.last_system: str = ""
        self.calls: int = 0

    async def stream(self, *, system_instruction, contents, **kwargs) -> AsyncIterator[str]:
        self.last_system = system_instruction
        self.calls += 1
        yield "Sinupret este un fitoterapeutic pentru sinuzită."


class _StubIntent:
    """Pinned IntentClassifier output — lets tests target the confidence gate."""

    def __init__(self, result: IntentResult) -> None:
        self._result = result

    def classify(self, text: str) -> IntentResult:
        return self._result


def _drive(
    history: list[ChatMessageIn],
    retrieval,
    llm,
    profile=None,
    intent=None,
    skip_followups: bool = False,
) -> tuple[list, str]:
    convo = ConversationService(retrieval=retrieval, llm=llm, intent=intent)  # type: ignore[arg-type]

    async def collect():
        out = []
        async for ev in convo.stream_turn(history, profile=profile, skip_followups=skip_followups):
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
    clf = IntentClassifier(retrieval.medicines())
    intent = clf.classify("mă doare capul de două zile")
    assert intent.label == "SYMPTOM_TRIAGE"


# ─── Wire-up coverage requested by the audit ──────────────────────────


def test_red_flag_emergency_wins_over_medicine_lookup_intent():
    """If the user names a medicine AND describes an emergency, the red-flag
    layer must short-circuit BEFORE intent classification runs. The intent
    classifier never executing is the safety invariant — without it a
    MEDICINE_LOOKUP route would silently bypass the 112 redirect."""
    retrieval = _StubRetrieval([_sinupret()])
    llm = _StubLLM()
    # "nu pot respira" trips the severe_dyspnea emergency rule; "Sinupret"
    # would otherwise route to the explain branch on its own.
    history = [ChatMessageIn(role="user", text="am luat Sinupret și nu pot respira")]

    events, _ = _drive(history, retrieval, llm)

    kinds = [ev.kind for ev in events]
    assert "intent" not in kinds, "intent classification must NOT fire when red-flag short-circuits"
    triage = next(ev for ev in events if ev.kind == "triage")
    assert triage.payload["label"] == "EMERGENCY"
    assert kinds[-1] == "done"
    assert events[-1].payload["phase"] == "emergency"
    assert llm.calls == 0, "LLM must not be invoked on emergency"


def test_explain_branch_is_gated_by_confidence_threshold():
    """MEDICINE_LOOKUP_MIN_CONFIDENCE = 0.7 — a 0.69 result must NOT take
    the explain branch (falls back to symptom triage), a 0.70 result must."""
    retrieval_with_advise = _StubRetrieval(
        [_sinupret()],
        advise_decision=TriageDecision(
            label="UNCERTAIN",
            rationale="stub",
            recommended_action_ro="",
            confidence=0.1,
            red_flags=[],
            medicine_hits=[],
        ),
    )

    below = IntentResult(
        label="MEDICINE_LOOKUP",
        confidence=0.69,
        medicine=_sinupret(),
        matched_terms=["Sinupret"],
        rationale="stub",
    )
    events_below, _ = _drive(
        [ChatMessageIn(role="user", text="Sinupret")],
        retrieval_with_advise,
        _StubLLM(),
        intent=_StubIntent(below),
    )
    # Below threshold falls through to symptom-triage; UNCERTAIN + n=1 turn
    # ⇒ followup phase, not explain.
    done_below = next(ev for ev in events_below if ev.kind == "done")
    assert done_below.payload["phase"] != "explain"

    at_threshold = IntentResult(
        label="MEDICINE_LOOKUP",
        confidence=0.70,
        medicine=_sinupret(),
        matched_terms=["Sinupret"],
        rationale="stub",
    )
    retrieval_no_advise = _StubRetrieval([_sinupret()])
    events_at, _ = _drive(
        [ChatMessageIn(role="user", text="Sinupret")],
        retrieval_no_advise,
        _StubLLM(),
        intent=_StubIntent(at_threshold),
    )
    done_at = next(ev for ev in events_at if ev.kind == "done")
    assert done_at.payload["phase"] == "explain"


def _allergy_medicine() -> Medicine:
    return Medicine(
        id="A001",
        trade_name="Aerius",
        dci="desloratadină",
        form="COMPRIMATE",
        concentration="5 mg",
        atc_code="R06AX27",
        rx_status="OTC",
        category="Alergii",
        lay_description="Antihistaminic pentru rinită alergică.",
        lay_symptoms=["mâncărimi", "strănut", "urticarie"],
        rcp_sections={"indications": "Rinită alergică, urticarie cronică."},
        rcp_url="",
        prospect_url="",
        therapeutic_action="",
        has_rcp_text=True,
        has_curated_atc=True,
    )


def test_skip_followups_short_circuits_to_recommend_phase():
    """User who's answered at least one question can tap 'Sari direct la
    sugestii' to bypass the remaining followup gate. The orchestrator must
    skip the followup branch even when retrieval confidence stays weak."""
    retrieval = _StubRetrieval(
        [_sinupret()],
        advise_decision=TriageDecision(
            label="UNCERTAIN", rationale="stub", recommended_action_ro="",
            confidence=0.1, red_flags=[], medicine_hits=[],
        ),
    )
    llm = _StubLLM()
    # Two user turns — answered one followup; now asking to skip ahead.
    history = [
        ChatMessageIn(role="user", text="durere de cap"),
        ChatMessageIn(role="assistant", text="De cât timp?"),
        ChatMessageIn(role="user", text="Vreau sugestii cu ce am spus deja."),
    ]

    events, _ = _drive(history, retrieval, llm, skip_followups=True)

    done = next(ev for ev in events if ev.kind == "done")
    assert done.payload["phase"] == "recommend"


def test_skip_followups_ignored_on_very_first_turn():
    """The skip flag must not let a user with zero answered questions bypass
    the safety gate. user_turn_count must be >= MIN_FOLLOWUPS to skip."""
    retrieval = _StubRetrieval(
        [_sinupret()],
        advise_decision=TriageDecision(
            label="UNCERTAIN", rationale="stub", recommended_action_ro="",
            confidence=0.1, red_flags=[], medicine_hits=[],
        ),
    )
    llm = _StubLLM()
    history = [ChatMessageIn(role="user", text="vreau direct sugestii")]

    events, _ = _drive(history, retrieval, llm, skip_followups=True)

    done = next(ev for ev in events if ev.kind == "done")
    # First turn → still has to answer at least one question first.
    assert done.payload["phase"] == "followup"


def test_forced_allergy_directive_reaches_llm_system_prompt():
    """The category-driven first-followup override is the only thing
    preventing the LLM from picking the wrong opener for an allergy
    presentation. This test asserts the directive lives in the system
    prompt the LLM actually receives — covering the wire-up, not just
    the helper function tested in test_followup_logic.py."""
    aerius = _allergy_medicine()
    hit = MedicineHit(
        medicine=aerius,
        score=0.6,
        best_chunk=Chunk(
            id="A001_lay", medicine_id="A001",
            text="Antihistaminic pentru rinită alergică.", chunk_type="lay_summary",
        ),
        supporting_chunks=[],
    )
    retrieval = _StubRetrieval(
        [aerius],
        advise_decision=TriageDecision(
            label="UNCERTAIN",
            rationale="stub",
            recommended_action_ro="",
            confidence=0.1,
            red_flags=[],
            medicine_hits=[hit],
        ),
    )
    llm = _StubLLM()
    history = [ChatMessageIn(role="user", text="mă mănâncă pielea de două zile")]

    events, system_prompt = _drive(history, retrieval, llm)

    done = next(ev for ev in events if ev.kind == "done")
    assert done.payload["phase"] == "followup"
    # Anchor on a distinctive substring of FORCED_FIRST_FOLLOWUP_BY_CATEGORY["alergii"].
    assert "declanșat reacția alergică" in system_prompt
