"""
Run the golden set through the live RetrievalService and compute metrics.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from med_assist.eval.metrics import CaseEval, EvalReport, aggregate
from med_assist.service import RetrievalService

GOLDEN = Path(__file__).resolve().parent / "golden_set.json"


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
    if expected_triage == "OTC_SAFE":
        rank, dimension = _retrieval_rank(decision, expected_atc, expected_dci)

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
        latency_ms=latency_ms,
        notes=notes,
    )


def run(svc: Optional[RetrievalService] = None, golden_path: Optional[Path] = None) -> EvalReport:
    svc = svc or RetrievalService()
    golden = json.loads((golden_path or GOLDEN).read_text(encoding="utf-8"))
    cases = [_evaluate_case(svc, c) for c in golden]
    return aggregate(cases)
