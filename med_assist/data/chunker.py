"""
Turn each Medicine into 1-7 retrievable Chunks.

Chunk types:
  title         : trade_name + dci + form + concentration  (exact-match anchor)
  lay_summary   : category + lay_description + lay_symptoms  (symptom queries)
  rcp_indications, rcp_contraindications, rcp_warnings,
  rcp_interactions, rcp_side_effects                       (clinical queries)

RCP sections can be very long; we cap each at MAX_SECTION_CHARS
because (a) embedding model context is bounded and (b) the leading
text of a regulatory section carries most retrieval signal.
"""

from __future__ import annotations

from typing import Iterable

from .models import Chunk, ChunkType, Medicine

MAX_SECTION_CHARS = 800
RCP_SECTION_TYPES: dict[str, ChunkType] = {
    "indications": "rcp_indications",
    "contraindications": "rcp_contraindications",
    "warnings": "rcp_warnings",
    "interactions": "rcp_interactions",
    "side_effects": "rcp_side_effects",
}


def _make_metadata(med: Medicine) -> dict:
    return {
        "rx_status": med.rx_status,
        "atc_prefix": med.atc_code[:5] if med.atc_code else "",
        "dci": med.dci,
        "category": med.category,
    }


def _title_chunk(med: Medicine) -> Chunk:
    text_parts = [med.trade_name]
    if med.dci:
        text_parts.append(med.dci)
    if med.form:
        text_parts.append(med.form.lower())
    if med.concentration:
        text_parts.append(med.concentration)
    return Chunk(
        id=f"{med.id}#title",
        medicine_id=med.id,
        text=" — ".join(text_parts),
        chunk_type="title",
        metadata=_make_metadata(med),
    )


def _lay_summary_chunk(med: Medicine) -> Chunk | None:
    parts: list[str] = []
    if med.category:
        parts.append(med.category)
    if med.lay_description:
        parts.append(med.lay_description)
    if med.lay_symptoms:
        parts.append("Folosit pentru: " + ", ".join(med.lay_symptoms) + ".")
    if not parts:
        return None
    return Chunk(
        id=f"{med.id}#lay_summary",
        medicine_id=med.id,
        text=f"{med.trade_name} — " + " ".join(parts),
        chunk_type="lay_summary",
        metadata=_make_metadata(med),
    )


def _rcp_chunks(med: Medicine) -> Iterable[Chunk]:
    for section_key, chunk_type in RCP_SECTION_TYPES.items():
        body = med.rcp_sections.get(section_key, "").strip()
        if not body:
            continue
        text = f"{med.trade_name} ({med.dci}) — {section_key}: {body[:MAX_SECTION_CHARS]}"
        yield Chunk(
            id=f"{med.id}#{chunk_type}",
            medicine_id=med.id,
            text=text,
            chunk_type=chunk_type,
            metadata=_make_metadata(med),
        )


def chunk_medicine(med: Medicine) -> list[Chunk]:
    chunks: list[Chunk] = [_title_chunk(med)]
    summary = _lay_summary_chunk(med)
    if summary is not None:
        chunks.append(summary)
    chunks.extend(_rcp_chunks(med))
    return chunks


def chunk_corpus(medicines: list[Medicine]) -> list[Chunk]:
    out: list[Chunk] = []
    for med in medicines:
        out.extend(chunk_medicine(med))
    return out
