"""
Final enrichment: merge ANMDM medicines + scraped PDF links + parsed RCP sections
+ curated ATC indications -> the corpus the RAG indexes.

Inputs:
  processed/medicines_anmdm.json   (script 01)
  processed/pdf_links.json         (script 03)
  processed/rcp_parsed.json        (script 05)
Output:
  processed/medicines_enriched.json

Each output record contains:
  - regulatory facts from ANMDM (trade_name, dci, atc, form, rx_status, ...)
  - rcp_url, prospect_url
  - lay-language indication block from ATC4 map (when matched)
  - structured RCP sections (indications, contraindications, warnings, ...)
  - data_quality flags (whether RCP available, whether ATC matched)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.atc_indications import lookup as atc_lookup  # noqa: E402

ANMDM = ROOT / "data_acquisition" / "processed" / "medicines_anmdm.json"
LINKS = ROOT / "data_acquisition" / "processed" / "pdf_links.json"
RCP = ROOT / "data_acquisition" / "processed" / "rcp_parsed.json"
OUT = ROOT / "data_acquisition" / "processed" / "medicines_enriched.json"


def index_links_by_cim(rows: list[dict]) -> dict[str, dict]:
    return {r["cim"]: r for r in rows if r.get("cim")}


def build_links_by_medicine(
    medicines: list[dict],
    links_by_cim: dict[str, dict],
) -> dict[str, dict]:
    """For each medicine (CIM = first SKU), find its RCP/PRO/AMB URL."""
    out: dict[str, dict] = {}
    for med in medicines:
        cim = med["id"]
        link = links_by_cim.get(cim)
        if link:
            out[cim] = {
                "rcp_url": link.get("rcp_url", ""),
                "prospect_url": link.get("pro_url", ""),
                "package_url": link.get("amb_url", ""),
            }
    return out


def rcp_filename_from_url(url: str) -> str:
    if not url:
        return ""
    return Path(urlparse(url).path).name


def enrich(med: dict, link: dict | None, rcp_data: dict[str, dict]) -> dict:
    out = dict(med)
    out["links"] = link or {"rcp_url": "", "prospect_url": "", "package_url": ""}

    atc_match = atc_lookup(med.get("atc_code", ""))
    if atc_match:
        out["category"] = atc_match["category"]
        out["lay_symptoms"] = list(atc_match["symptoms"])
        out["lay_description"] = atc_match["description"]
        out["atc_indication_source"] = "curated"
    else:
        therap = (med.get("therapeutic_action") or "").strip()
        out["category"] = therap.title() or "Necategorizat"
        out["lay_symptoms"] = []
        out["lay_description"] = therap.capitalize()
        out["atc_indication_source"] = "regulatory_fallback"

    rcp_filename = rcp_filename_from_url(out["links"]["rcp_url"])
    rcp_entry = rcp_data.get(rcp_filename)
    if rcp_entry:
        out["rcp_sections"] = {k: v["text"] for k, v in rcp_entry["sections"].items()}
        out["rcp_filename"] = rcp_filename
    else:
        out["rcp_sections"] = {}
        out["rcp_filename"] = ""

    out["data_quality"] = {
        "has_rcp_url": bool(out["links"]["rcp_url"]),
        "has_rcp_text": bool(out["rcp_sections"]),
        "has_atc_curated": atc_match is not None,
        "rcp_section_count": len(out["rcp_sections"]),
    }
    return out


def report(enriched: list[dict]) -> dict:
    by_status = defaultdict(int)
    has_rcp_url = 0
    has_rcp_text = 0
    has_atc_curated = 0
    full_signal_otc = 0
    for med in enriched:
        by_status[med["rx_status"]] += 1
        dq = med["data_quality"]
        has_rcp_url += int(dq["has_rcp_url"])
        has_rcp_text += int(dq["has_rcp_text"])
        has_atc_curated += int(dq["has_atc_curated"])
        if (
            med["rx_status"] in ("OTC", "MIXED")
            and dq["has_rcp_text"]
            and dq["has_atc_curated"]
        ):
            full_signal_otc += 1
    return {
        "total": len(enriched),
        "by_rx_status": dict(by_status),
        "has_rcp_url": has_rcp_url,
        "has_rcp_text": has_rcp_text,
        "has_atc_curated": has_atc_curated,
        "otc_or_mixed_with_full_signal": full_signal_otc,
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-missing-rcp", action="store_true",
                        help="don't fail if RCP files aren't downloaded yet")
    args = parser.parse_args()

    if not ANMDM.exists():
        logging.error("missing: %s — run 01_parse_anmdm.py", ANMDM)
        return 2
    medicines = json.loads(ANMDM.read_text(encoding="utf-8"))

    links_rows = json.loads(LINKS.read_text(encoding="utf-8")) if LINKS.exists() else []
    if not links_rows:
        logging.warning("no PDF links available (run 03_scrape_pdf_links.py)")
    links_by_cim = index_links_by_cim(links_rows)

    rcp_data = json.loads(RCP.read_text(encoding="utf-8")) if RCP.exists() else {}
    if not rcp_data and not args.allow_missing_rcp:
        logging.warning("no RCP parse output (run 05_parse_pdfs.py); proceeding anyway")

    links_by_medicine = build_links_by_medicine(medicines, links_by_cim)
    enriched = [enrich(m, links_by_medicine.get(m["id"]), rcp_data) for m in medicines]

    summary = report(enriched)
    logging.info("=== enrichment summary ===")
    logging.info("total medicines: %d", summary["total"])
    for k, v in summary["by_rx_status"].items():
        logging.info("  rx=%-12s %d", k, v)
    logging.info("with RCP url:        %d", summary["has_rcp_url"])
    logging.info("with parsed RCP text: %d", summary["has_rcp_text"])
    logging.info("with curated ATC:     %d", summary["has_atc_curated"])
    logging.info("OTC/MIXED with full signal (rcp + curated atc): %d",
                 summary["otc_or_mixed_with_full_signal"])

    OUT.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
    logging.info("wrote %s", OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
