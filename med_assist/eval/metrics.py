"""
Eval metrics for the triage + retrieval pipeline.

Triage:
  - confusion matrix (3x3 over EMERGENCY/OTC_SAFE/UNCERTAIN)
  - false_negative_emergency_rate    THE critical safety metric
  - false_positive_emergency_rate    over-triage cost
  - red_flag_match_rate              right rule fired for right reason

Retrieval (only for OTC_SAFE expected entries):
  - recall_at_k for k in {1, 3, 5, 10}
  - mrr (mean reciprocal rank, capped at 10)

Latency:
  - p50, p95, max in milliseconds
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CaseEval:
    case_id: str
    query: str
    category: str
    expected_triage: str
    actual_triage: str
    triage_correct: bool
    red_flag_correct: Optional[bool]
    retrieval_rank: Optional[int]      # rank of first matching expected medicine, None if not in top-10
    retrieval_match_dimension: str     # "atc" | "dci" | "none"
    latency_ms: float
    notes: str = ""


@dataclass
class TriageMetrics:
    confusion: dict                     # {(expected, actual): count}
    accuracy: float
    false_negative_emergency_rate: float
    false_positive_emergency_rate: float
    red_flag_match_rate: Optional[float]


@dataclass
class RetrievalMetrics:
    n_evaluated: int
    recall_at_k: dict                   # {1: 0.85, 3: 0.92, ...}
    mrr: float


@dataclass
class LatencyMetrics:
    p50_ms: float
    p95_ms: float
    max_ms: float


@dataclass
class EvalReport:
    triage: TriageMetrics
    retrieval: RetrievalMetrics
    latency: LatencyMetrics
    cases: list[CaseEval] = field(default_factory=list)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(pct * (len(s) - 1))))
    return s[k]


def aggregate(cases: list[CaseEval]) -> EvalReport:
    confusion: dict = {}
    triage_correct = 0
    fn_emerg = 0
    fp_emerg = 0
    n_emerg_expected = 0
    n_otc_or_uncert_expected = 0

    rf_matches = []
    recall_hits = {1: 0, 3: 0, 5: 0, 10: 0}
    rr_total = 0.0
    n_retrieval = 0

    for c in cases:
        key = (c.expected_triage, c.actual_triage)
        confusion[key] = confusion.get(key, 0) + 1
        if c.triage_correct:
            triage_correct += 1

        if c.expected_triage == "EMERGENCY":
            n_emerg_expected += 1
            if c.actual_triage != "EMERGENCY":
                fn_emerg += 1
            if c.red_flag_correct is not None:
                rf_matches.append(c.red_flag_correct)
        else:
            n_otc_or_uncert_expected += 1
            if c.actual_triage == "EMERGENCY":
                fp_emerg += 1

        if c.expected_triage == "OTC_SAFE" and c.retrieval_rank is not None:
            n_retrieval += 1
            for k in (1, 3, 5, 10):
                if c.retrieval_rank < k:
                    recall_hits[k] += 1
            rr_total += 1.0 / (c.retrieval_rank + 1)
        elif c.expected_triage == "OTC_SAFE":
            n_retrieval += 1  # missed entirely (not in top-10) — counts in denominator

    n = len(cases)
    triage_metrics = TriageMetrics(
        confusion=confusion,
        accuracy=triage_correct / n if n else 0.0,
        false_negative_emergency_rate=(fn_emerg / n_emerg_expected) if n_emerg_expected else 0.0,
        false_positive_emergency_rate=(fp_emerg / n_otc_or_uncert_expected) if n_otc_or_uncert_expected else 0.0,
        red_flag_match_rate=(sum(rf_matches) / len(rf_matches)) if rf_matches else None,
    )

    recall_at_k = {k: (v / n_retrieval) if n_retrieval else 0.0 for k, v in recall_hits.items()}
    retrieval_metrics = RetrievalMetrics(
        n_evaluated=n_retrieval,
        recall_at_k=recall_at_k,
        mrr=(rr_total / n_retrieval) if n_retrieval else 0.0,
    )

    latencies = [c.latency_ms for c in cases]
    latency_metrics = LatencyMetrics(
        p50_ms=_percentile(latencies, 0.50),
        p95_ms=_percentile(latencies, 0.95),
        max_ms=max(latencies) if latencies else 0.0,
    )

    return EvalReport(
        triage=triage_metrics,
        retrieval=retrieval_metrics,
        latency=latency_metrics,
        cases=cases,
    )
