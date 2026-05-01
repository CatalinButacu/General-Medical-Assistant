"""
Three-way triage classifier.

Decides whether a user query represents:
  EMERGENCY    -> red-flag rule fired, route to 112/ER immediately
  OTC_SAFE     -> retrieval found high-confidence OTC matches, recommend
  UNCERTAIN    -> retrieval is weak, route user to a pharmacist

Keeps the rules-first design (deterministic, explainable) and uses
retrieval signal as a confidence proxy. An LLM second opinion is a
Phase 3 add-on; for now we trust the rule engine + retrieval scores.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from med_assist.data.models import MedicineHit
from med_assist.triage.redflags import RedFlag, has_emergency, has_urgent, scan

TriageLabel = Literal["EMERGENCY", "OTC_SAFE", "UNCERTAIN"]


@dataclass
class TriageDecision:
    label: TriageLabel
    rationale: str                              # human-readable RO explanation
    red_flags: list[RedFlag] = field(default_factory=list)
    recommended_action_ro: str = ""
    medicine_hits: list[MedicineHit] = field(default_factory=list)
    confidence: float = 0.0                     # 0.0–1.0


# Empirical thresholds — tuned on smoke queries.
# RRF with k=60 caps single-retriever rank-0 contribution at 1/61 ≈ 0.0164;
# a medicine that lands rank 0 in only one retriever therefore scores ~0.016.
# We accept that as the lower bound for "real signal" and require >=2 hits
# in that band to avoid recommending on weak retrieval.
MIN_TOP_SCORE = 0.014
MIN_RELEVANT_HITS = 2


def classify(
    query: str,
    medicine_hits: list[MedicineHit] | None = None,
) -> TriageDecision:
    """
    Decide the triage label for a query.

    Pass `medicine_hits` already produced by RetrievalService.query() —
    the classifier reads top-N hit scores to gauge retrieval confidence.
    """
    flags = scan(query)

    if has_emergency(flags):
        primary = next(f for f in flags if f.severity == "emergency")
        return TriageDecision(
            label="EMERGENCY",
            rationale=f"Detectat: {primary.description}.",
            red_flags=flags,
            recommended_action_ro=primary.action_ro,
        )

    if has_urgent(flags):
        primary = next(f for f in flags if f.severity == "urgent")
        return TriageDecision(
            label="EMERGENCY",  # urgent still routes to ER, not OTC pool
            rationale=f"Semn de gravitate: {primary.description}.",
            red_flags=flags,
            recommended_action_ro=primary.action_ro,
        )

    if not medicine_hits:
        return TriageDecision(
            label="UNCERTAIN",
            rationale="Nu am identificat simptome sau medicamente specifice. Vă rugăm să descrieți mai detaliat sau să consultați un farmacist.",
            recommended_action_ro="Consultați un farmacist pentru sfat personalizat.",
        )

    top_score = medicine_hits[0].score
    relevant_hits = sum(1 for h in medicine_hits if h.score >= MIN_TOP_SCORE * 0.8)

    if top_score >= MIN_TOP_SCORE and relevant_hits >= MIN_RELEVANT_HITS:
        return TriageDecision(
            label="OTC_SAFE",
            rationale=f"Identificate {relevant_hits} medicamente potrivite (scor maxim {top_score:.3f}).",
            medicine_hits=medicine_hits,
            confidence=min(top_score / 0.04, 1.0),  # 0.04 ≈ very confident, clamped
            recommended_action_ro="Vedeți recomandările de mai jos. Consultați farmacistul dacă simptomele persistă.",
        )

    return TriageDecision(
        label="UNCERTAIN",
        rationale=f"Rezultate slabe pentru întrebarea dvs. (scor maxim {top_score:.3f}). Recomandăm consultul unui farmacist.",
        medicine_hits=medicine_hits[:3],  # show weak hits for transparency
        confidence=min(top_score / 0.04, 1.0),
        recommended_action_ro="Consultați un farmacist sau medicul dvs.",
    )
