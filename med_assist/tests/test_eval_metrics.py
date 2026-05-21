"""Unit tests for the RAGAS-style additions to the eval metrics.

The aggregate() function is fed hand-crafted CaseEval lists rather than
running the full pipeline — that's the manual `--faithfulness` path. These
tests pin the math so the formulas can't silently regress."""

from __future__ import annotations

from med_assist.eval.metrics import CaseEval, aggregate


def _otc_case(
    *,
    case_id: str = "c1",
    triage_correct: bool = True,
    rank=None,
    ctx_precision_at_5=None,
    faithful=None,
    latency_ms: float = 50.0,
) -> CaseEval:
    return CaseEval(
        case_id=case_id,
        query="durere",
        category="durere",
        expected_triage="OTC_SAFE",
        actual_triage="OTC_SAFE" if triage_correct else "UNCERTAIN",
        triage_correct=triage_correct,
        red_flag_correct=None,
        retrieval_rank=rank,
        retrieval_match_dimension="atc" if rank is not None else "none",
        context_precision_at_5=ctx_precision_at_5,
        latency_ms=latency_ms,
        faithful=faithful,
    )


def test_context_precision_at_5_averages_across_otc_cases():
    cases = [
        _otc_case(case_id="a", rank=0, ctx_precision_at_5=0.6),
        _otc_case(case_id="b", rank=1, ctx_precision_at_5=0.4),
        _otc_case(case_id="c", rank=None, ctx_precision_at_5=0.0),
    ]
    rep = aggregate(cases)
    # (0.6 + 0.4 + 0.0) / 3 = 0.333...
    assert abs(rep.retrieval.context_precision_at_k[5] - (0.6 + 0.4) / 3) < 1e-9


def test_context_precision_at_1_derived_from_rank():
    # rank=0 → top-1 hit, contributes 1.0; rank=2 → miss at top-1, contributes 0
    cases = [
        _otc_case(case_id="a", rank=0, ctx_precision_at_5=0.4),
        _otc_case(case_id="b", rank=2, ctx_precision_at_5=0.4),
    ]
    rep = aggregate(cases)
    assert rep.retrieval.context_precision_at_k[1] == 0.5


def test_context_precision_at_3_uses_third_of_rank_zero_hit():
    # Both cases have a hit somewhere in top-3 → each contributes 1/3
    cases = [
        _otc_case(case_id="a", rank=0, ctx_precision_at_5=0.4),
        _otc_case(case_id="b", rank=2, ctx_precision_at_5=0.4),
    ]
    rep = aggregate(cases)
    assert abs(rep.retrieval.context_precision_at_k[3] - (1 / 3)) < 1e-9


def test_context_precision_skipped_for_non_otc_cases():
    cases = [
        _otc_case(case_id="otc", rank=0, ctx_precision_at_5=0.6),
        CaseEval(
            case_id="emg",
            query="x", category="cardiac",
            expected_triage="EMERGENCY", actual_triage="EMERGENCY",
            triage_correct=True, red_flag_correct=True,
            retrieval_rank=None, retrieval_match_dimension="none",
            context_precision_at_5=None,  # N/A for emergency
            latency_ms=10.0,
        ),
    ]
    rep = aggregate(cases)
    # Only the otc case counts → precision@5 == 0.6
    assert rep.retrieval.context_precision_at_k[5] == 0.6


def test_faithfulness_metrics_present_only_when_graded():
    cases_without = [_otc_case(case_id="a", rank=0, ctx_precision_at_5=0.5)]
    assert aggregate(cases_without).faithfulness is None


def test_faithfulness_rate_is_correct_ratio():
    cases = [
        _otc_case(case_id="a", rank=0, ctx_precision_at_5=0.5, faithful=True),
        _otc_case(case_id="b", rank=0, ctx_precision_at_5=0.5, faithful=True),
        _otc_case(case_id="c", rank=0, ctx_precision_at_5=0.5, faithful=False),
        # judge-error cases don't count toward the denominator
        _otc_case(case_id="d", rank=0, ctx_precision_at_5=0.5, faithful=None),
    ]
    rep = aggregate(cases)
    assert rep.faithfulness is not None
    assert rep.faithfulness.n_evaluated == 3
    assert rep.faithfulness.faithful_count == 2
    assert abs(rep.faithfulness.faithfulness_rate - (2 / 3)) < 1e-9
