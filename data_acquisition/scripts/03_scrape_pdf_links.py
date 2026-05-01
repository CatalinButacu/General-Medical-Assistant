"""
Scrape ANMDM /medicamente HTML pages -> CIM -> {RCP url, prospect url}.

Each row in the HTML carries:
  data-cim       e.g. "W43451001"
  data-linkrcp   e.g. "http://www.anm.ro/_/_RCP/RCP_7321_22.01.15.pdf"
  data-linkpro   e.g. "http://www.anm.ro/_/_PRO/PRO_7321_22.01.15.pdf"
  data-linkamb   e.g. "http://www.anm.ro/_/_AMB/AMB_7321_22.01.15.pdf"
  data-nrdtamb   e.g. "7321/2015/01"

Output:
  data_acquisition/processed/pdf_links.json
    [{cim, rcp_url, pro_url, amb_url, auth_number, auth_year, sku_suffix}, ...]
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.http import PoliteFetcher  # noqa: E402

PAGES_CACHE = ROOT / "data_acquisition" / "raw" / "pages"
OUT = ROOT / "data_acquisition" / "processed" / "pdf_links.json"
BASE_URL = "https://nomenclator.anm.ro/medicamente"

# Match a single medicine row's data attributes. Each row spans multiple lines.
# We use a per-attr regex and a row delimiter approach: rows are separated by
# data-cim occurrences. Capture between consecutive data-cim markers.
ROW_SPLIT_RE = re.compile(r'(data-cim="[^"]*")')
ATTR_RE = re.compile(r'data-(cim|linkrcp|linkpro|linkamb|nrdtamb)="([^"]*)"')


def parse_page(html: str) -> list[dict]:
    """Extract all (cim, rcp_url, pro_url, amb_url, nrdtamb) tuples from one page."""
    rows: list[dict] = []
    # Split on data-cim markers; each fragment is one row's attribute block
    fragments = ROW_SPLIT_RE.split(html)
    # fragments[0] is pre-row preamble; pairs follow as (data-cim="...", body)
    for i in range(1, len(fragments) - 1, 2):
        marker = fragments[i]
        body = fragments[i + 1]
        block = marker + body
        attrs = dict(ATTR_RE.findall(block))
        if "cim" not in attrs:
            continue
        rows.append({
            "cim": attrs.get("cim", ""),
            "rcp_url": attrs.get("linkrcp", ""),
            "pro_url": attrs.get("linkpro", ""),
            "amb_url": attrs.get("linkamb", ""),
            "nrdtamb": attrs.get("nrdtamb", ""),
        })
    return rows


_NRDTAMB_RE = re.compile(r"^(\d+)/(\d{4})/(\d+)$")


def parse_nrdtamb(value: str) -> tuple[str, str, str]:
    m = _NRDTAMB_RE.match(value.strip())
    if not m:
        return "", "", ""
    return m.group(1), m.group(2), m.group(3)


def scrape(max_pages: int, fetcher: PoliteFetcher) -> list[dict]:
    all_rows: list[dict] = []
    seen_cim: set[str] = set()

    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}?page={page}"
        cache_key = f"page_{page:04d}.html"
        html = fetcher.get_text(url, cache_key=cache_key)
        rows = parse_page(html)

        if not rows:
            logging.info("page %d: empty -> stopping pagination", page)
            break

        new_count = 0
        for row in rows:
            if row["cim"] in seen_cim:
                continue
            seen_cim.add(row["cim"])
            auth_num, auth_year, sku_suffix = parse_nrdtamb(row["nrdtamb"])
            row["auth_number"] = auth_num
            row["auth_year"] = auth_year
            row["sku_suffix"] = sku_suffix
            all_rows.append(row)
            new_count += 1

        if page == 1 or page % 100 == 0:
            logging.info("page %d: %d rows (%d new, total=%d)", page, len(rows), new_count, len(all_rows))

    return all_rows


def summarize(rows: list[dict]) -> None:
    total = len(rows)
    rcp_present = sum(1 for r in rows if r["rcp_url"])
    pro_present = sum(1 for r in rows if r["pro_url"])
    unique_rcp = len({r["rcp_url"] for r in rows if r["rcp_url"]})
    unique_pro = len({r["pro_url"] for r in rows if r["pro_url"]})
    no_link = [r for r in rows if not r["rcp_url"] and not r["pro_url"]]
    logging.info("scraped CIMs: %d", total)
    logging.info("with RCP link: %d (%.1f%%) | unique RCP files: %d", rcp_present, 100 * rcp_present / max(total, 1), unique_rcp)
    logging.info("with PRO link: %d (%.1f%%) | unique PRO files: %d", pro_present, 100 * pro_present / max(total, 1), unique_pro)
    if no_link:
        logging.warning("CIMs with no RCP and no PRO link: %d (sample: %s)", len(no_link), [r["cim"] for r in no_link[:5]])


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pages", type=int, default=1580, help="ANMDM max page; smoke-test with --max-pages 3")
    parser.add_argument("--rate", type=float, default=2.0, help="min seconds between requests (default 2.0 = 0.5 req/s)")
    args = parser.parse_args()

    fetcher = PoliteFetcher(cache_dir=PAGES_CACHE, min_interval_s=args.rate)
    rows = scrape(args.max_pages, fetcher)
    summarize(rows)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    logging.info("wrote %s", OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
