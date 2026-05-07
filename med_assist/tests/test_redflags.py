"""Smoke tests for the red-flag scanner — the most safety-critical layer.

Pure-Python module, no external dependencies, so these run cleanly in CI
without needing torch/faiss/etc. They lock in the 0% false-negative-emergency
baseline reported in the README.
"""

from med_assist.triage.redflags import has_emergency, has_urgent, scan


def _severities(text: str) -> set[str]:
    return {f.severity for f in scan(text)}


# ───────────────── must fire ─────────────────


def test_chest_pain_with_radiation_is_emergency():
    assert "emergency" in _severities("durere severă în piept care iradiază în braț")


def test_anaphylaxis_is_emergency():
    assert "emergency" in _severities("șoc anafilactic după antibiotic")


def test_suicidal_ideation_routes_to_emergency():
    flags = scan("vreau sa ma sinucid")
    assert has_emergency(flags) or has_urgent(flags)


# ───────────────── must NOT fire ─────────────────


def test_mild_cold_is_not_emergency():
    flags = scan("am nasul înfundat și tușesc puțin")
    assert not has_emergency(flags)
    assert not has_urgent(flags)


def test_routine_headache_is_not_emergency():
    flags = scan("ma doare capul de cateva ore")
    assert not has_emergency(flags)


def test_diacritics_normalized():
    """Romanian users type both with and without diacritics; the scanner must handle both."""
    with_diacritics = scan("durere severă în piept care iradiază în braț")
    without = scan("durere severa in piept care iradiaza in brat")
    assert bool(with_diacritics) == bool(without)
