"""
Core domain types for the med_assist package.

A `Medicine` is the unit the chatbot recommends and cites.
A `Chunk` is a unit of retrieval — usually a paragraph-sized excerpt
of a medicine's text, indexed independently and traceable back to the
parent medicine via `medicine_id`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ChunkType = Literal[
    "title",
    "lay_summary",
    "rcp_indications",
    "rcp_contraindications",
    "rcp_warnings",
    "rcp_interactions",
    "rcp_side_effects",
]

RxStatus = Literal["OTC", "RX", "RESTRICTED", "MIXED", "UNKNOWN"]


@dataclass
class Medicine:
    id: str                     # CIM code, e.g. "W43451001"
    trade_name: str
    dci: str                    # active substance (INN)
    form: str
    concentration: str
    atc_code: str
    rx_status: RxStatus
    category: str               # patient-friendly Romanian category
    lay_description: str        # short Romanian description
    lay_symptoms: list[str]     # lay-Romanian symptom strings
    rcp_sections: dict[str, str]  # {indications, contraindications, warnings, interactions, side_effects}
    rcp_url: str
    prospect_url: str
    therapeutic_action: str     # raw regulatory text (uppercase)
    has_rcp_text: bool
    has_curated_atc: bool

    @property
    def display_name(self) -> str:
        return f"{self.trade_name} ({self.concentration}, {self.form.lower()})"


@dataclass
class Chunk:
    id: str                     # e.g. "W43451001#rcp_indications"
    medicine_id: str            # CIM code
    text: str                   # the searchable text body
    chunk_type: ChunkType
    metadata: dict = field(default_factory=dict)  # rx_status, atc_prefix, etc. for filtering


@dataclass
class RetrievalHit:
    chunk: Chunk
    score: float
    source: str                 # which retriever produced it: "dense", "sparse", "fusion", "rerank"
    rank: int = 0


@dataclass
class MedicineHit:
    """De-duplicated, medicine-level result with the best supporting chunk."""
    medicine: Medicine
    score: float
    best_chunk: Chunk
    supporting_chunks: list[Chunk] = field(default_factory=list)
