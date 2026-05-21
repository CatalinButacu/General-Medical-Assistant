"""
Run the eval harness and print a comparable, hand-readable report.

  python -m med_assist.cli.eval                  # full report
  python -m med_assist.cli.eval --failed-only    # only failing cases
  python -m med_assist.cli.eval --json out.json  # machine-readable export
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from med_assist.eval.runner import run


def _print_report(report, failed_only: bool) -> None:
    t = report.triage
    r = report.retrieval
    lat = report.latency

    print("\n# Eval report")
    print(f"\ncases: {len(report.cases)}")

    print("\n## Triage")
    print(f"  accuracy: {t.accuracy:.1%}")
    print(f"  false_negative_emergency_rate: {t.false_negative_emergency_rate:.1%}   (CRITICAL — keep at 0%)")
    print(f"  false_positive_emergency_rate: {t.false_positive_emergency_rate:.1%}")
    if t.red_flag_match_rate is not None:
        print(f"  red_flag_match_rate:           {t.red_flag_match_rate:.1%}")
    print("\n  confusion (expected -> actual):")
    print("    " + "".join(f"{a:<14}" for a in ["", "EMERGENCY", "OTC_SAFE", "UNCERTAIN"]))
    for exp in ("EMERGENCY", "OTC_SAFE", "UNCERTAIN"):
        row = [f"{exp:<14}"]
        for act in ("EMERGENCY", "OTC_SAFE", "UNCERTAIN"):
            row.append(f"{t.confusion.get((exp, act), 0):<14}")
        print("    " + "".join(row))

    print("\n## Retrieval (OTC_SAFE expected only)")
    print(f"  n: {r.n_evaluated}")
    for k, v in r.recall_at_k.items():
        print(f"  recall@{k:<2}: {v:.1%}")
    print(f"  MRR:        {r.mrr:.3f}")
    print("  context_precision (top-K retrieved medicines that match expected ATC/DCI):")
    for k, v in r.context_precision_at_k.items():
        print(f"    precision@{k}: {v:.1%}")

    if report.faithfulness is not None:
        f = report.faithfulness
        print("\n## Faithfulness (LLM-as-judge, OTC_SAFE cases with retrieval)")
        print(f"  graded:           {f.n_evaluated}")
        print(f"  faithful:         {f.faithful_count}")
        print(f"  faithfulness_rate: {f.faithfulness_rate:.1%}")

    print("\n## Latency")
    print(f"  p50: {lat.p50_ms:.0f} ms")
    print(f"  p95: {lat.p95_ms:.0f} ms")
    print(f"  max: {lat.max_ms:.0f} ms")

    cases_to_show = [c for c in report.cases if not c.triage_correct] if failed_only else report.cases
    if not cases_to_show:
        print("\nAll cases passed.\n")
        return

    print(f"\n## {'Failed cases' if failed_only else 'All cases'}")
    for c in cases_to_show:
        ok = "OK" if c.triage_correct else "FAIL"
        rank_str = f"r={c.retrieval_rank}({c.retrieval_match_dimension})" if c.retrieval_rank is not None else "r=miss"
        if c.expected_triage != "OTC_SAFE":
            rank_str = ""
        print(f"  [{ok}] {c.case_id:<32} {c.expected_triage:<10} -> {c.actual_triage:<10} {rank_str:<12} {c.latency_ms:>5.0f}ms")
        if c.notes:
            print(f"         {c.notes}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--failed-only", action="store_true")
    parser.add_argument("--json", type=Path, help="export full report as JSON")
    parser.add_argument(
        "--faithfulness",
        action="store_true",
        help="grade OTC_SAFE answers with an LLM-as-judge (adds ~2 Gemini calls per case)",
    )
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    report = run(with_faithfulness=args.faithfulness)
    _print_report(report, failed_only=args.failed_only)

    if args.json:
        # Manually serialize since CaseEval has Optional fields
        payload = {
            "triage": {
                "accuracy": report.triage.accuracy,
                "false_negative_emergency_rate": report.triage.false_negative_emergency_rate,
                "false_positive_emergency_rate": report.triage.false_positive_emergency_rate,
                "red_flag_match_rate": report.triage.red_flag_match_rate,
                "confusion": {f"{e}->{a}": v for (e, a), v in report.triage.confusion.items()},
            },
            "retrieval": {
                "n_evaluated": report.retrieval.n_evaluated,
                "recall_at_k": report.retrieval.recall_at_k,
                "mrr": report.retrieval.mrr,
                "context_precision_at_k": report.retrieval.context_precision_at_k,
            },
            "faithfulness": (
                {
                    "n_evaluated": report.faithfulness.n_evaluated,
                    "faithful_count": report.faithfulness.faithful_count,
                    "faithfulness_rate": report.faithfulness.faithfulness_rate,
                }
                if report.faithfulness is not None
                else None
            ),
            "latency": asdict(report.latency),
            "cases": [asdict(c) for c in report.cases],
        }
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
