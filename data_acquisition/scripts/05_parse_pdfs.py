"""
Parse downloaded RCP and prospect PDFs -> structured fields per medicine.

RCP follows EU QRD template; key sections we extract:
  4.1  Indicaţii terapeutice
  4.3  Contraindicaţii
  4.4  Atenţionări şi precauţii speciale
  4.5  Interacţiuni
  4.8  Reacţii adverse
Indexed by RCP filename (auth_number + date), since RCPs are shared across
multiple SKU packagings.

Output:
  processed/rcp_parsed.json  {filename: {trade_name, sections: {...}, source_path}}
  processed/parse_report.json  {ok, headerless, empty_sections, failed}
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parents[2]
RCP_DIR = ROOT / "data_acquisition" / "raw" / "pdfs" / "rcp"
OUT = ROOT / "data_acquisition" / "processed" / "rcp_parsed.json"
REPORT = ROOT / "data_acquisition" / "processed" / "parse_report.json"

# Sections we care about for the chatbot, by hierarchical id
TARGET_SECTIONS = {
    "4.1": "indications",
    "4.3": "contraindications",
    "4.4": "warnings",
    "4.5": "interactions",
    "4.8": "side_effects",
}

# A section header is: a numeric id (possibly multi-level), optional dot, then a TITLE.
# In Romanian RCPs the id and title are often on separate lines after PDF text extraction:
#     "4.1\nIndicaţii terapeutice"
# We allow whitespace/newlines between id and title and require the title to start
# with a capital Romanian letter.
SECTION_HEADER_RE = re.compile(
    r"""(?xm)
    ^[\ \t]*
    (?P<id>\d+(?:\.\d+){0,2})
    \.?[\ \t]*
    \n?[\ \t]*
    (?P<title>[A-ZĂÂÎȘȚ][^\n]{4,80})
    \s*$
    """
)

# Lines we strip out before section parsing (footers, page numbers, anexa markers)
NOISE_LINE_RE = re.compile(
    r"""(?ix)
    ^(
      \d{1,3}                                               # bare page number
      | pagina[\ \t]+\d+
      | anexa[\ \t]+\d+
      | autoriza\w+\ de\ punere\ pe\ piat[aă][\ \t][^\n]+   # auth header
      | rezumatul\ caracteristicilor\ produsului
      | prospect[\s:][^\n]*                                  # prospect header
    )\s*$
    """
)


def extract_text(path: Path) -> str:
    doc = fitz.open(path)
    pages: list[str] = [str(p.get_text("text")) for p in doc]
    doc.close()
    return "\n".join(pages)


def normalize(text: str) -> str:
    # Strip noise lines, collapse runs of whitespace inside lines, drop empty lines.
    out_lines: list[str] = []
    for raw in text.splitlines():
        line = re.sub(r"[ \t]+", " ", raw).strip()
        if not line:
            continue
        if NOISE_LINE_RE.match(line):
            continue
        out_lines.append(line)
    return "\n".join(out_lines)


def find_sections(text: str) -> list[tuple[str, str, int, int]]:
    """Return (section_id, title, start, end) tuples sorted by start position."""
    matches = list(SECTION_HEADER_RE.finditer(text))
    sections: list[tuple[str, str, int, int]] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((m.group("id"), m.group("title").strip(), m.end(), end))
    return sections


def extract_targets(text: str) -> dict:
    sections = find_sections(text)
    out: dict = {}
    for sid, title, start, end in sections:
        if sid not in TARGET_SECTIONS:
            continue
        body = text[start:end].strip()
        body = re.sub(r"\n{2,}", "\n", body)
        if body:
            out[TARGET_SECTIONS[sid]] = {"title": title, "text": body[:8000]}  # cap to avoid runaway
    return out


def parse_rcp(path: Path) -> dict | None:
    raw = extract_text(path)
    text = normalize(raw)
    sections = extract_targets(text)
    if not sections:
        return None
    return {"filename": path.name, "sections": sections}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=None, help="cap PDFs parsed for smoke test")
    args = parser.parse_args()

    if not RCP_DIR.exists():
        logging.error("RCP dir does not exist: %s", RCP_DIR)
        return 2

    files = sorted(RCP_DIR.glob("*.pdf"))
    if args.max is not None:
        files = files[: args.max]
    logging.info("parsing %d RCP PDFs", len(files))

    parsed: dict[str, dict] = {}
    report = {"ok": 0, "headerless": [], "empty_sections": [], "failed": []}

    for idx, path in enumerate(files, start=1):
        try:
            result = parse_rcp(path)
            if result is None:
                report["headerless"].append(path.name)
                continue
            if not result["sections"]:
                report["empty_sections"].append(path.name)
                continue
            parsed[path.name] = result
            report["ok"] += 1
        except Exception as exc:
            report["failed"].append({"file": path.name, "error": str(exc)[:200]})
            logging.warning("parse failed %s: %s", path.name, exc)

        if idx == 1 or idx % 200 == 0 or idx == len(files):
            logging.info("progress %d/%d  ok=%d headerless=%d empty=%d failed=%d",
                         idx, len(files), report["ok"], len(report["headerless"]),
                         len(report["empty_sections"]), len(report["failed"]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    sec_coverage = {k: 0 for k in TARGET_SECTIONS.values() if k != "trade_name"}
    for entry in parsed.values():
        for sec in entry["sections"]:
            sec_coverage[sec] = sec_coverage.get(sec, 0) + 1
    logging.info("section coverage (out of %d ok):", report["ok"])
    for sec, n in sorted(sec_coverage.items(), key=lambda kv: -kv[1]):
        pct = 100 * n / report["ok"] if report["ok"] else 0
        logging.info("  %-18s %4d  (%.1f%%)", sec, n, pct)

    logging.info("wrote %s and %s", OUT.relative_to(ROOT), REPORT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
