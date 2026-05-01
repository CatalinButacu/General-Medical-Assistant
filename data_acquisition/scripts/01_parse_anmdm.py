"""
Parse ANMDM nomenclator Excel -> normalized JSON of unique medicines.

Source: https://nomenclator.anm.ro/files/nomenclator.xlsx (daily refresh).
Output: data_acquisition/processed/medicines_anmdm.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data_acquisition" / "raw" / "anmdm_nomenclator.xlsx"
OUT = ROOT / "data_acquisition" / "processed" / "medicines_anmdm.json"

RX_MAP = {
    "OTC": "OTC",
    "PR": "RX",
    "PRF": "RX",
    "P-RF": "RX",
    "P6L": "RX",
    "P-6L": "RX",
    "PS": "RESTRICTED",
    "S": "RESTRICTED",
    "P-RF/R": "RX",
    "P-RF/S": "RESTRICTED",
    "S/P-RF": "RESTRICTED",
    "P-6L/S": "RESTRICTED",
}

CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f]+")


def clean_str(value: object) -> str:
    if pd.isna(value):
        return ""
    return CONTROL_CHAR_RE.sub("", str(value)).strip()


def normalize_rx(value: str) -> str:
    base = value.split("/")[0].strip()
    return RX_MAP.get(base, "UNKNOWN")


def split_holder(value: str) -> tuple[str, str]:
    if " - " not in value:
        return value, ""
    name, country = value.rsplit(" - ", 1)
    return name.strip(), country.strip()


def parse() -> list[dict]:
    df = pd.read_excel(RAW)
    print(f"loaded {len(df)} SKU rows from {RAW.name}", file=sys.stderr)

    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].map(clean_str)

    df["rx_status"] = df["Prescriptie"].map(normalize_rx)

    # collapse SKU-level rows to medicine-level by (trade_name, concentration, form)
    grouped = df.groupby(
        ["Denumire comerciala", "Concentratie", "Forma farmaceutica"],
        dropna=False,
        sort=False,
    )

    medicines: list[dict] = []
    for (trade_name, concentration, form), group in grouped:
        first = group.iloc[0]
        producer_name, producer_country = split_holder(first["Firma / tara producatoare APP"])
        holder_name, holder_country = split_holder(first["Firma / tara detinatoare APP"])

        rx_values = set(group["rx_status"].unique()) - {"UNKNOWN"}
        rx_status = next(iter(rx_values), "UNKNOWN") if len(rx_values) == 1 else "MIXED"

        packagings = sorted({clean_str(a) for a in group["Ambalaj"] if clean_str(a)})

        medicines.append(
            {
                "id": str(first["Cod CIM"]),
                "trade_name": trade_name,
                "dci": first["DCI"],
                "form": form,
                "concentration": concentration,
                "atc_code": first["Cod ATC"],
                "therapeutic_action": first["Actiune terapeutica"],
                "rx_status": rx_status,
                "producer": {"name": producer_name, "country": producer_country},
                "marketing_holder": {"name": holder_name, "country": holder_country},
                "packagings": packagings,
                "package_count": len(group),
                "data_source": "ANMDM Nomenclator",
                "data_updated": clean_str(first["Data actualizare"]),
            }
        )

    return medicines


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    medicines = parse()

    rx_counts: dict[str, int] = {}
    for med in medicines:
        rx_counts[med["rx_status"]] = rx_counts.get(med["rx_status"], 0) + 1

    print(f"unique medicines: {len(medicines)}", file=sys.stderr)
    for status, n in sorted(rx_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {status:<12} {n}", file=sys.stderr)

    with OUT.open("w", encoding="utf-8") as f:
        json.dump(medicines, f, ensure_ascii=False, indent=2)
    print(f"wrote {OUT.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
