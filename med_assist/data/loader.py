"""
Load enriched medicines from data_acquisition output -> typed Medicine list.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import Medicine

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data_acquisition" / "processed" / "medicines_enriched.json"


def load_medicines(path: Path | None = None) -> list[Medicine]:
    src = path or DEFAULT_PATH
    if not src.exists():
        raise FileNotFoundError(
            f"enriched corpus not found at {src}. "
            "Run `python data_acquisition/scripts/update_all.py --allow-missing-rcp` "
            "or `python data_acquisition/scripts/06_enrich.py --allow-missing-rcp` first."
        )

    raw = json.loads(src.read_text(encoding="utf-8"))
    out: list[Medicine] = []
    for entry in raw:
        links = entry.get("links", {})
        dq = entry.get("data_quality", {})
        out.append(
            Medicine(
                id=entry["id"],
                trade_name=entry["trade_name"],
                dci=entry["dci"],
                form=entry["form"],
                concentration=entry["concentration"] or "",
                atc_code=entry["atc_code"],
                rx_status=entry["rx_status"],
                category=entry.get("category", ""),
                lay_description=entry.get("lay_description", ""),
                lay_symptoms=list(entry.get("lay_symptoms", [])),
                rcp_sections=dict(entry.get("rcp_sections", {})),
                rcp_url=links.get("rcp_url", ""),
                prospect_url=links.get("prospect_url", ""),
                therapeutic_action=entry.get("therapeutic_action", ""),
                has_rcp_text=bool(dq.get("has_rcp_text", False)),
                has_curated_atc=bool(dq.get("has_atc_curated", False)),
            )
        )
    return out
