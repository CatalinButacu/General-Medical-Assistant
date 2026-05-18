"""Intent classifier invariants — drives the routing decision before
the chatbot picks a system prompt."""

from __future__ import annotations

import pytest

from med_assist.data.models import Medicine, RxStatus
from med_assist.intent.classifier import IntentClassifier


def _mk(trade_name: str, dci: str, rx_status: RxStatus = "OTC") -> Medicine:
    return Medicine(
        id=f"X-{trade_name}",
        trade_name=trade_name,
        dci=dci,
        form="COMPRIMATE",
        concentration="",
        atc_code="N02BE01",
        rx_status=rx_status,
        category="",
        lay_description="",
        lay_symptoms=[],
        rcp_sections={},
        rcp_url="",
        prospect_url="",
        therapeutic_action="",
        has_rcp_text=False,
        has_curated_atc=False,
    )


@pytest.fixture
def classifier() -> IntentClassifier:
    return IntentClassifier([
        _mk("Sinupret", "extract plante"),
        _mk("Nurofen", "ibuprofen"),
        _mk("Paracetamol Zentiva", "paracetamol"),
        _mk("Aspen 80mg", "acid acetilsalicilic", rx_status="RX"),
    ])


def test_lookup_phrase_with_trade_name_routes_to_lookup(classifier):
    r = classifier.classify("ce este Sinupret?")
    assert r.label == "MEDICINE_LOOKUP"
    assert r.confidence >= 0.8
    assert r.medicine is not None
    assert r.medicine.trade_name == "Sinupret"


def test_bare_trade_name_in_short_message_routes_to_lookup(classifier):
    r = classifier.classify("Nurofen")
    assert r.label == "MEDICINE_LOOKUP"
    assert r.medicine.trade_name == "Nurofen"


def test_dci_match_routes_to_lookup(classifier):
    r = classifier.classify("la ce e bun paracetamol?")
    assert r.label == "MEDICINE_LOOKUP"
    # DCI 'paracetamol' indexed via the OTC entry.
    assert r.medicine is not None
    assert r.medicine.dci == "paracetamol"


def test_symptom_phrase_wins_even_if_medicine_named(classifier):
    """If the user says they hurt AND mentions a medicine, we still triage symptoms."""
    r = classifier.classify("ma doare capul si am Sinupret in dulap")
    assert r.label == "SYMPTOM_TRIAGE"
    # Medicine is still detected for telemetry but doesn't drive the branch.
    assert r.medicine is not None and r.medicine.trade_name == "Sinupret"


def test_multiword_trade_name_match(classifier):
    r = classifier.classify("Aspen 80mg ce face?")
    assert r.label == "MEDICINE_LOOKUP"
    assert r.medicine.trade_name == "Aspen 80mg"


def test_rx_medicine_is_not_routed_via_dci_fallback():
    """RX-only DCIs shouldn't pop up as DCI-search hits — the explain
    branch is OTC-leaning; for RX-only meds you typically know the brand."""
    clf = IntentClassifier([_mk("Brand-RX", "tramadol", rx_status="RX")])
    r = clf.classify("pentru ce e tramadol?")
    # No trade-name match in the message, DCI hit is suppressed for RX.
    assert r.label == "SYMPTOM_TRIAGE"


def test_ambiguous_everyday_words_dont_trigger():
    """If a brand is also a common Romanian word ('apa', 'sare') the
    classifier must not route to MEDICINE_LOOKUP on that alone."""
    clf = IntentClassifier([_mk("Apa", "apa minerala")])
    r = clf.classify("beau apa cu lamaie")
    assert r.label == "SYMPTOM_TRIAGE"
    assert r.medicine is None


def test_empty_input_is_symptom_default():
    clf = IntentClassifier([_mk("Sinupret", "extract plante")])
    r = clf.classify("   ")
    assert r.label == "SYMPTOM_TRIAGE"


def test_unknown_message_routes_to_symptom_default(classifier):
    r = classifier.classify("salut, ce mai faci")
    assert r.label == "SYMPTOM_TRIAGE"
    assert r.medicine is None
