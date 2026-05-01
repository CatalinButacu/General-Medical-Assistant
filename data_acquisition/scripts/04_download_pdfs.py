"""
Download unique RCP and prospect PDFs from anm.ro.

Reads pdf_links.json (produced by 03_scrape_pdf_links.py).
Deduplicates by URL (same RCP is shared across many SKUs).
Skips files already on disk -> idempotent + resumable.
EU-centrally-authorized medicines link to ec.europa.eu instead of anm.ro;
we log them as deferred and skip (handled in a later EMA-specific script).

Output:
  raw/pdfs/rcp/<basename>.pdf
  raw/pdfs/pro/<basename>.pdf
  processed/download_manifest.json   (per-URL outcome: ok | cached | deferred | failed)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.http import PoliteFetcher  # noqa: E402

LINKS = ROOT / "data_acquisition" / "processed" / "pdf_links.json"
PDF_ROOT = ROOT / "data_acquisition" / "raw" / "pdfs"
MANIFEST = ROOT / "data_acquisition" / "processed" / "download_manifest.json"

ANM_HOSTS = {"www.anm.ro", "anm.ro"}


def basename_from_url(url: str) -> str:
    return Path(urlparse(url).path).name


def classify(url: str) -> str:
    if not url:
        return "missing"
    host = urlparse(url).hostname or ""
    if host in ANM_HOSTS:
        return "anm"
    return "external"


def collect_unique_targets(rows: list[dict]) -> list[tuple[str, str]]:
    """Return list of (kind, url) tuples — deduped by url, kind in {rcp, pro}."""
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []
    for row in rows:
        for kind in ("rcp", "pro"):
            url = row.get(f"{kind}_url", "")
            if not url:
                continue
            key = (kind, url)
            if key in seen:
                continue
            seen.add(key)
            out.append(key)
    return out


def download_all(targets: list[tuple[str, str]], fetcher: PoliteFetcher, max_count: int | None) -> dict:
    PDF_ROOT.mkdir(parents=True, exist_ok=True)
    (PDF_ROOT / "rcp").mkdir(exist_ok=True)
    (PDF_ROOT / "pro").mkdir(exist_ok=True)

    outcomes: list[dict] = []
    counts = {"ok": 0, "cached": 0, "deferred": 0, "failed": 0}

    iterable = targets if max_count is None else targets[:max_count]
    total = len(iterable)

    for idx, (kind, url) in enumerate(iterable, start=1):
        bucket = classify(url)
        if bucket == "external":
            outcomes.append({"kind": kind, "url": url, "status": "deferred", "reason": "non-anm.ro host"})
            counts["deferred"] += 1
            continue

        basename = basename_from_url(url)
        if not basename:
            outcomes.append({"kind": kind, "url": url, "status": "failed", "reason": "no basename"})
            counts["failed"] += 1
            continue

        target_path = PDF_ROOT / kind / basename
        if target_path.exists() and target_path.stat().st_size > 0:
            outcomes.append({"kind": kind, "url": url, "status": "cached", "path": str(target_path.relative_to(ROOT))})
            counts["cached"] += 1
            continue

        try:
            content = fetcher.get_bytes(url)
            target_path.write_bytes(content)
            outcomes.append({
                "kind": kind, "url": url, "status": "ok",
                "path": str(target_path.relative_to(ROOT)), "bytes": len(content),
            })
            counts["ok"] += 1
        except Exception as exc:
            outcomes.append({"kind": kind, "url": url, "status": "failed", "reason": str(exc)[:200]})
            counts["failed"] += 1
            logging.warning("failed %s: %s", url, exc)

        if idx == 1 or idx % 50 == 0 or idx == total:
            logging.info(
                "progress %d/%d  ok=%d cached=%d deferred=%d failed=%d",
                idx, total, counts["ok"], counts["cached"], counts["deferred"], counts["failed"],
            )

    return {"outcomes": outcomes, "counts": counts, "total_targets": total}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=None, help="cap downloads for smoke test")
    parser.add_argument("--rate", type=float, default=2.0)
    args = parser.parse_args()

    if not LINKS.exists():
        logging.error("links file not found: %s — run 03_scrape_pdf_links.py first", LINKS)
        return 2

    rows = json.loads(LINKS.read_text(encoding="utf-8"))
    logging.info("loaded %d link rows from %s", len(rows), LINKS.name)

    targets = collect_unique_targets(rows)
    logging.info(
        "unique download targets: %d (%d RCP, %d PRO)",
        len(targets),
        sum(1 for k, _ in targets if k == "rcp"),
        sum(1 for k, _ in targets if k == "pro"),
    )

    fetcher = PoliteFetcher(min_interval_s=args.rate)
    result = download_all(targets, fetcher, max_count=args.max)

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logging.info("wrote manifest -> %s", MANIFEST.relative_to(ROOT))

    counts = result["counts"]
    logging.info(
        "FINAL  ok=%d cached=%d deferred=%d failed=%d total=%d",
        counts["ok"], counts["cached"], counts["deferred"], counts["failed"], result["total_targets"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
