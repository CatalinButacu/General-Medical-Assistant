"""
Run the golden set through the live RetrievalService and compute metrics.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

from med_assist.eval.metrics import CaseEval, EvalReport, aggregate
from med_assist.service import RetrievalService

GOLDEN = Path(__file__).resolve().parent / "golden_set.json"

log = logging.getLogger("medassist.eval")


def _retrieval_rank(decision, expected_atc_prefixes: list, expected_dci_keywords: list) -> tuple[Optional[int], str]:
    """Return (rank, dimension) of first expected match in decision.medicine_hits."""
    for rank, hit in enumerate(decision.medicine_hits):
        med = hit.medicine
        if expected_atc_prefixes:
            for prefix in expected_atc_prefixes:
                if med.atc_code.startswith(prefix):
                    return rank, "atc"
        if expected_dci_keywords:
            for kw in expected_dci_keywords:
                if kw.upper() in med.dci.upper():
                    return rank, "dci"
    return None, "none"


def _context_precision_at_5(decision, expected_atc_prefixes: list, expected_dci_keywords: list) -> float:
    """Fraction of top-5 retrieved medicines that match expected ATC or DCI.

    RAGAS-style context_precision proxy without LLM judge: a chunk is 'relevant'
    if its parent medicine matches the case's expected_atc_prefixes or
    expected_dci_keywords. Pure metric, deterministic.
    """
    top5 = decision.medicine_hits[:5]
    if not top5:
        return 0.0
    relevant = 0
    for hit in top5:
        med = hit.medicine
        is_relevant = False
        if expected_atc_prefixes and any(med.atc_code.startswith(p) for p in expected_atc_prefixes):
            is_relevant = True
        elif expected_dci_keywords and any(kw.upper() in med.dci.upper() for kw in expected_dci_keywords):
            is_relevant = True
        if is_relevant:
            relevant += 1
    return relevant / len(top5)


def _evaluate_case(svc: RetrievalService, case: dict) -> CaseEval:
    query = case["query"]
    expected_triage = case["expected_triage"]
    expected_red_flag = case.get("expected_red_flag")
    expected_atc = case.get("expected_atc_prefixes", [])
    expected_dci = case.get("expected_dci_keywords", [])

    t0 = time.time()
    decision = svc.advise(query, top_k_medicines=10, otc_only=True)
    latency_ms = (time.time() - t0) * 1000

    triage_correct = decision.label == expected_triage

    red_flag_correct: Optional[bool] = None
    if expected_red_flag is not None:
        red_flag_correct = any(rf.name == expected_red_flag for rf in decision.red_flags)

    rank, dimension = (None, "none")
    ctx_precision: Optional[float] = None
    if expected_triage == "OTC_SAFE":
        rank, dimension = _retrieval_rank(decision, expected_atc, expected_dci)
        ctx_precision = _context_precision_at_5(decision, expected_atc, expected_dci)

    notes = ""
    if not triage_correct:
        notes = f"actual={decision.label}; rationale={decision.rationale[:120]}"

    return CaseEval(
        case_id=case["id"],
        query=query,
        category=case.get("category", ""),
        expected_triage=expected_triage,
        actual_triage=decision.label,
        triage_correct=triage_correct,
        red_flag_correct=red_flag_correct,
        retrieval_rank=rank,
        retrieval_match_dimension=dimension,
        context_precision_at_5=ctx_precision,
        latency_ms=latency_ms,
        notes=notes,
    )


def run(
    svc: Optional[RetrievalService] = None,
    golden_path: Optional[Path] = None,
    with_faithfulness: bool = False,
) -> EvalReport:
    """Drive the golden set through the service.

    When `with_faithfulness=True`, OTC_SAFE cases with at least one retrieved
    medicine also generate an LLM answer and submit it to an LLM-as-judge.
    Requires GOOGLE_API_KEY. Adds ~2 Gemini calls per OTC_SAFE case, so the
    full eval runs noticeably slower and consumes quota.
    """
    svc = svc or RetrievalService()
    golden = json.loads((golden_path or GOLDEN).read_text(encoding="utf-8"))
    cases = [_evaluate_case(svc, c) for c in golden]

    if with_faithfulness:
        from med_assist.eval.faithfulness import grade_cases
        log.info("running faithfulness grading on %d cases (LLM-as-judge)", len(cases))
        grade_cases(svc, golden, cases)

    return aggregate(cases)
