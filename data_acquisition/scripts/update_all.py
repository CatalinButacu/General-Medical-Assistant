"""
Daily auto-update orchestrator.

Runs the data acquisition pipeline end-to-end with drift detection:

  1. Re-download nomenclator.xlsx
  2. Parse it (medicines_anmdm.json)
  3. Diff vs previous run -> emit added / removed / rx_changed sets
  4. Re-scrape PDF link pages (paginate ANMDM portal)
  5. Download new/changed PDFs (rcp + prospect)
  6. Parse RCP PDFs into structured sections
  7. Build the final enriched corpus
  8. Validate quality (drift > 5% triggers alarm)
  9. Append to CHANGELOG.md

Designed for unattended cron / GitHub Actions invocation:
  python data_acquisition/scripts/update_all.py
Exit code 0 on success, 1 on quality alarm, 2 on hard failure.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "data_acquisition" / "scripts"
RAW = ROOT / "data_acquisition" / "raw"
PROC = ROOT / "data_acquisition" / "processed"
SNAPSHOTS = ROOT / "data_acquisition" / "snapshots"
CHANGELOG = ROOT / "data_acquisition" / "CHANGELOG.md"

DRIFT_ALARM_THRESHOLD = 0.05  # 5% record-count change in any direction


def run_step(name: str, cmd: list[str]) -> None:
    logging.info("=== %s ===", name)
    logging.info("$ %s", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        raise RuntimeError(f"step '{name}' failed with exit code {result.returncode}")


def fetch_xlsx(refresh: bool) -> None:
    target = RAW / "anmdm_nomenclator.xlsx"
    if target.exists() and not refresh:
        logging.info("xlsx already present (--refresh to re-download)")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "curl", "-fL",
        "-A", "MedAssistResearch/0.1 (educational; contact butacu.catalin@yahoo.com)",
        "-o", str(target),
        "https://nomenclator.anm.ro/files/nomenclator.xlsx",
    ]
    run_step("fetch_xlsx", cmd)


def diff_against_snapshot(current: list[dict], snapshot_path: Path) -> dict:
    if not snapshot_path.exists():
        return {"first_run": True, "added": [], "removed": [], "rx_changed": []}

    prev_list = json.loads(snapshot_path.read_text(encoding="utf-8"))
    prev_by_id = {m["id"]: m for m in prev_list}
    cur_by_id = {m["id"]: m for m in current}

    added = sorted(set(cur_by_id) - set(prev_by_id))
    removed = sorted(set(prev_by_id) - set(cur_by_id))
    rx_changed = []
    for mid in set(cur_by_id) & set(prev_by_id):
        if cur_by_id[mid]["rx_status"] != prev_by_id[mid]["rx_status"]:
            rx_changed.append(
                {"id": mid,
                 "from": prev_by_id[mid]["rx_status"],
                 "to": cur_by_id[mid]["rx_status"]}
            )
    return {"first_run": False, "added": added, "removed": removed, "rx_changed": rx_changed}


def quality_check(diff: dict, current_count: int) -> tuple[bool, list[str]]:
    """Returns (ok, messages)."""
    msgs: list[str] = []
    if diff["first_run"]:
        msgs.append(f"first run: {current_count} medicines")
        return True, msgs

    drift = (len(diff["added"]) + len(diff["removed"])) / max(current_count, 1)
    msgs.append(f"added={len(diff['added'])} removed={len(diff['removed'])} "
                f"rx_changed={len(diff['rx_changed'])} drift={drift:.2%}")
    if drift > DRIFT_ALARM_THRESHOLD:
        msgs.append(f"ALARM: drift {drift:.2%} exceeds threshold {DRIFT_ALARM_THRESHOLD:.0%}")
        return False, msgs
    return True, msgs


def write_changelog(diff: dict, summary_messages: list[str]) -> None:
    CHANGELOG.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [f"## {timestamp}", ""]
    parts.extend(f"- {m}" for m in summary_messages)
    parts.append("")
    if diff["added"]:
        parts.append(f"### Added ({len(diff['added'])})")
        parts.extend(f"- {cim}" for cim in diff["added"][:50])
        if len(diff["added"]) > 50:
            parts.append(f"- ... and {len(diff['added']) - 50} more")
        parts.append("")
    if diff["removed"]:
        parts.append(f"### Removed ({len(diff['removed'])})")
        parts.extend(f"- {cim}" for cim in diff["removed"][:50])
        if len(diff["removed"]) > 50:
            parts.append(f"- ... and {len(diff['removed']) - 50} more")
        parts.append("")
    if diff["rx_changed"]:
        parts.append(f"### Rx status changes ({len(diff['rx_changed'])})")
        for change in diff["rx_changed"][:50]:
            parts.append(f"- {change['id']}: {change['from']} -> {change['to']}")
        parts.append("")

    block = "\n".join(parts) + "\n"
    existing = CHANGELOG.read_text(encoding="utf-8") if CHANGELOG.exists() else "# Data acquisition changelog\n\n"
    # Insert new block right after the H1 title to keep most-recent first
    if existing.startswith("# "):
        head, _, rest = existing.partition("\n\n")
        CHANGELOG.write_text(head + "\n\n" + block + rest, encoding="utf-8")
    else:
        CHANGELOG.write_text(block + existing, encoding="utf-8")


def snapshot_current() -> None:
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    src = PROC / "medicines_anmdm.json"
    if src.exists():
        shutil.copy2(src, SNAPSHOTS / "medicines_anmdm.previous.json")


def python_step(script: str, *args: str) -> list[str]:
    return [sys.executable, str(SCRIPTS / script), *args]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="force re-download of cached files")
    parser.add_argument("--skip-pdfs", action="store_true", help="skip PDF download/parse (for fast dev runs)")
    args = parser.parse_args()

    snapshot_path = SNAPSHOTS / "medicines_anmdm.previous.json"

    try:
        fetch_xlsx(refresh=args.refresh)
        run_step("parse_anmdm", python_step("01_parse_anmdm.py"))

        current = json.loads((PROC / "medicines_anmdm.json").read_text(encoding="utf-8"))
        diff = diff_against_snapshot(current, snapshot_path)

        ok, messages = quality_check(diff, len(current))
        for m in messages:
            logging.info(m)
        write_changelog(diff, messages)

        if not ok:
            logging.error("quality alarm — aborting before downstream steps")
            return 1

        scrape_args = ["--max-pages", "1580"]
        if args.refresh:
            shutil.rmtree(RAW / "pages", ignore_errors=True)
        run_step("scrape_pdf_links", python_step("03_scrape_pdf_links.py", *scrape_args))

        if not args.skip_pdfs:
            run_step("download_pdfs", python_step("04_download_pdfs.py"))
            run_step("parse_pdfs", python_step("05_parse_pdfs.py"))

        run_step("enrich", python_step("06_enrich.py", "--allow-missing-rcp"))

        snapshot_current()
        logging.info("update complete")
        return 0
    except Exception as exc:
        logging.exception("update_all failed: %s", exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
