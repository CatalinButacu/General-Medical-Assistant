"""Followup-phase invariants: forced trigger question for allergy-flavored hits,
and the prompt-builder honors the forced_topic override."""

from __future__ import annotations

from dataclasses import dataclass

from med_assist.conversation import _forced_first_followup
from med_assist.llm.prompts import render_followup


@dataclass
class _FakeMed:
    category: str


@dataclass
class _FakeChunk:
    text: str = ""
    chunk_type: str = "indication"


@dataclass
class _FakeHit:
    medicine: _FakeMed
    score: float = 0.5
    best_chunk: _FakeChunk = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.best_chunk is None:
            self.best_chunk = _FakeChunk()


def test_forced_topic_fires_for_allergy_category():
    hits = [_FakeHit(medicine=_FakeMed(category="Alergii"))]
    directive = _forced_first_followup(hits)  # type: ignore[arg-type]
    assert directive is not None
    assert "declanșat" in directive  # asks about the trigger


def test_forced_topic_substring_match_is_case_insensitive():
    hits = [_FakeHit(medicine=_FakeMed(category="ALERGII sezoniere"))]
    result = _forced_first_followup(hits)  # type: ignore[arg-type]
    assert result is not None


def test_forced_topic_skips_unrelated_categories():
    hits = [_FakeHit(medicine=_FakeMed(category="Durere și inflamație"))]
    result = _forced_first_followup(hits)  # type: ignore[arg-type]
    assert result is None


def test_forced_topic_only_inspects_top_3_hits():
    hits = [
        _FakeHit(medicine=_FakeMed(category="Durere și febră")),
        _FakeHit(medicine=_FakeMed(category="Tuse productivă")),
        _FakeHit(medicine=_FakeMed(category="Hiperaciditate gastrică")),
        # 4th would match but should be ignored
        _FakeHit(medicine=_FakeMed(category="Alergii")),
    ]
    result = _forced_first_followup(hits)  # type: ignore[arg-type]
    assert result is None


def test_render_followup_includes_directive_at_top():
    prompt = render_followup(
        user_history_text=["alergie cu mâncărime"],
        profile=None,
        retrieval_hint="Alergii",
        forced_topic="Întreabă întâi de trigger.",
    )
    directive_pos = prompt.find("DIRECTIVĂ STRICTĂ")
    history_pos = prompt.find("SIMPTOME / DETALII")
    assert directive_pos != -1
    assert history_pos != -1
    assert directive_pos < history_pos  # directive comes before history block


def test_render_followup_omits_directive_when_none():
    prompt = render_followup(
        user_history_text=["mă doare capul"],
        profile=None,
        retrieval_hint="",
        forced_topic=None,
    )
    assert "DIRECTIVĂ STRICTĂ" not in prompt
