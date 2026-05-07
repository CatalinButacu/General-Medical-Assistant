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

from collections import Counter
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


# Two parallel paths qualify a query as OTC_SAFE:
#
#  1. Strong score path: top fused score >= 0.020 (both retrievers agreed)
#     AND at least MIN_RELEVANT_HITS medicines above RELEVANT_SCORE_FLOOR.
#  2. Coherence path:    top score is weaker (>= WEAK_FLOOR) but the top-3
#     medicines clearly agree on a drug class — either >=2 share the same
#     ATC level-4 prefix, or >=2 share the same trade-name brand root.
#     This catches single-retriever hits that are nonetheless coherent
#     (e.g. brand-name queries that BM25 nails but dense doesn't).
#
# Off-topic queries fail both paths: their weak score has no coherent
# clustering in top-3, so they correctly route to UNCERTAIN.
MIN_TOP_SCORE = 0.020
WEAK_FLOOR = 0.018           # bumped from 0.014: prevents accidental ATC clustering noise from passing as OTC_SAFE
MIN_RELEVANT_HITS = 2
RELEVANT_SCORE_FLOOR = 0.018
COHERENCE_TOP_K = 3
COHERENCE_MIN_SHARED = 2


def classify(
    query: str,
    medicine_hits: list[MedicineHit] | None = None,
    sparse_signal: bool = True,
) -> TriageDecision:
    """
    Decide the triage label for a query.

    `sparse_signal` indicates whether BM25 returned non-zero hits.
    When False, the query has no real Romanian medical terms (gibberish,
    off-topic) — we then refuse the weak/coherent path and force UNCERTAIN.
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
            rationale=(
                "Nu am identificat simptome sau medicamente specifice. "
                "Vă rugăm să descrieți mai detaliat sau să consultați un farmacist."
            ),
            recommended_action_ro="Consultați un farmacist pentru sfat personalizat.",
        )

    top_score = medicine_hits[0].score
    relevant_hits = sum(1 for h in medicine_hits if h.score >= RELEVANT_SCORE_FLOOR)

    top_k_for_coherence = medicine_hits[:COHERENCE_TOP_K]
    atc4_counts = Counter(
        h.medicine.atc_code[:5]
        for h in top_k_for_coherence
        if h.medicine.atc_code
    )
    brand_counts = Counter(
        h.medicine.trade_name.split()[0].upper()
        for h in top_k_for_coherence
        if h.medicine.trade_name
    )
    top_atc_share = max(atc4_counts.values()) if atc4_counts else 0
    top_brand_share = max(brand_counts.values()) if brand_counts else 0
    coherent = top_atc_share >= COHERENCE_MIN_SHARED or top_brand_share >= COHERENCE_MIN_SHARED

    strong = top_score >= MIN_TOP_SCORE and relevant_hits >= MIN_RELEVANT_HITS
    coherent_path = top_score >= WEAK_FLOOR and coherent and sparse_signal

    if strong or coherent_path:
        rationale_bits = []
        if strong:
            rationale_bits.append(f"{relevant_hits} medicamente cu scor mare")
        if coherent_path:
            if top_atc_share >= COHERENCE_MIN_SHARED:
                rationale_bits.append(f"top-{COHERENCE_TOP_K} agree pe clasa ATC")
            elif top_brand_share >= COHERENCE_MIN_SHARED:
                rationale_bits.append(f"top-{COHERENCE_TOP_K} agree pe brand")
        return TriageDecision(
            label="OTC_SAFE",
            rationale="Retrieval coerent: " + "; ".join(rationale_bits) + f" (scor maxim {top_score:.3f}).",
            medicine_hits=medicine_hits,
            confidence=min(top_score / 0.04, 1.0),
            recommended_action_ro="Vedeți recomandările de mai jos. Consultați farmacistul dacă simptomele persistă.",
        )

    return TriageDecision(
        label="UNCERTAIN",
        rationale=(
            f"Rezultate slabe pentru întrebarea dvs. "
            f"(scor maxim {top_score:.3f}, top-{COHERENCE_TOP_K} share ATC={top_atc_share}, brand={top_brand_share}). "
            f"Recomandăm consultul unui farmacist."
        ),
        medicine_hits=medicine_hits[:3],
        confidence=min(top_score / 0.04, 1.0),
        recommended_action_ro="Consultați un farmacist sau medicul dvs.",
    )
