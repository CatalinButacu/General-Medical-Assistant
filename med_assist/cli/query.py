"""
Smoke-test CLI: load index, run a query, print top medicines + supporting chunks.

  python -m med_assist.cli.query "mă doare burta și am diaree"
  python -m med_assist.cli.query --otc-only "tuse productivă"
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from med_assist.service import RetrievalService


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="natural-language Romanian query")
    parser.add_argument("--top", type=int, default=5, help="number of medicines to show")
    parser.add_argument("--otc-only", action="store_true",
                        help="filter to OTC and MIXED Rx status")
    parser.add_argument("--exclude-contraindications", action="store_true",
                        help="don't surface contraindication chunks")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    svc = RetrievalService()

    t0 = time.time()
    rx_filter = {"OTC", "MIXED"} if args.otc_only else None
    exclude = {"rcp_contraindications"} if args.exclude_contraindications else None
    hits = svc.query(
        args.query,
        top_k_medicines=args.top,
        rx_filter=rx_filter,
        exclude_chunk_types=exclude,
    )
    elapsed = (time.time() - t0) * 1000

    print(f'\nQuery: "{args.query}"   ({elapsed:.0f} ms)')
    print(f"OTC filter: {bool(rx_filter)}")
    print(f"Top {len(hits)} medicines:\n")
    for i, hit in enumerate(hits, start=1):
        med = hit.medicine
        print(f"{i}. {med.display_name}  [{med.rx_status}]  score={hit.score:.4f}")
        print(f"   DCI: {med.dci}  ATC: {med.atc_code}  category: {med.category}")
        if med.lay_symptoms:
            print(f"   lay symptoms: {', '.join(med.lay_symptoms)}")
        snippet = hit.best_chunk.text[:200].replace("\n", " ")
        print(f"   ↳ best chunk [{hit.best_chunk.chunk_type}]: {snippet}...")
        types = sorted({c.chunk_type for c in hit.supporting_chunks})
        print(f"   supporting chunk types: {', '.join(types)}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
