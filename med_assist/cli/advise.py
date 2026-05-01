"""
End-to-end triage + recommendation demo.

  python -m med_assist.cli.advise "mă doare burta și am diaree"
  python -m med_assist.cli.advise "am dureri în piept și transpir, brațul stâng amorțit"
  python -m med_assist.cli.advise "nu pot respira"
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from med_assist.service import RetrievalService


LABEL_COLORS = {
    "EMERGENCY": "\033[91m",
    "OTC_SAFE": "\033[92m",
    "UNCERTAIN": "\033[93m",
}
RESET = "\033[0m"


def render(decision, query: str, elapsed_ms: float, color: bool) -> None:
    pre = LABEL_COLORS.get(decision.label, "") if color else ""
    post = RESET if color else ""

    print(f'\nQuery: "{query}"   ({elapsed_ms:.0f} ms)')
    print(f"Label: {pre}{decision.label}{post}")
    print(f"Rationale: {decision.rationale}")

    if decision.red_flags:
        print(f"\nRed flags detected ({len(decision.red_flags)}):")
        for f in decision.red_flags:
            print(f"  - [{f.severity}] {f.description}")
            print(f"    matched: '{f.matched_pattern}'")

    if decision.recommended_action_ro:
        print(f"\nAction: {decision.recommended_action_ro}")

    if decision.medicine_hits:
        print(f"\nTop {len(decision.medicine_hits)} medicines (confidence={decision.confidence:.2f}):")
        for i, hit in enumerate(decision.medicine_hits, start=1):
            med = hit.medicine
            print(f"  {i}. {med.display_name}  [{med.rx_status}]  score={hit.score:.4f}")
            print(f"     {med.dci} ({med.atc_code})  {med.category}")
            if med.lay_symptoms:
                print(f"     pentru: {', '.join(med.lay_symptoms)}")


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="natural-language Romanian query")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--include-rx", action="store_true",
                        help="don't restrict to OTC-only (include Rx in candidate pool)")
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    svc = RetrievalService()

    t0 = time.time()
    decision = svc.advise(
        args.query,
        top_k_medicines=args.top,
        otc_only=not args.include_rx,
    )
    elapsed = (time.time() - t0) * 1000

    render(decision, args.query, elapsed, color=not args.no_color)
    return 0


if __name__ == "__main__":
    sys.exit(main())
