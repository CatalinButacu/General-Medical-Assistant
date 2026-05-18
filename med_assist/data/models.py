"""
Core domain types for the med_assist package.

A `Medicine` is the unit the chatbot recommends and cites.
A `Chunk` is a unit of retrieval — usually a paragraph-sized excerpt
of a medicine's text, indexed independently and traceable back to the
parent medicine via `medicine_id`.

Pydantic v2 models give us boundary validation (FastAPI request bodies,
template render contexts) and a single source of truth for the chatbot's
data contract.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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


class Medicine(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str
    trade_name: str
    dci: str
    form: str
    concentration: str
    atc_code: str
    rx_status: RxStatus
    category: str
    lay_description: str
    lay_symptoms: list[str] = Field(default_factory=list)
    rcp_sections: dict[str, str] = Field(default_factory=dict)
    rcp_url: str
    prospect_url: str
    therapeutic_action: str
    has_rcp_text: bool
    has_curated_atc: bool

    @property
    def display_name(self) -> str:
        return f"{self.trade_name} ({self.concentration}, {self.form.lower()})"


class Chunk(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str
    medicine_id: str
    text: str
    chunk_type: ChunkType
    metadata: dict = Field(default_factory=dict)


class RetrievalHit(BaseModel):
    model_config = ConfigDict(frozen=False, arbitrary_types_allowed=True)

    chunk: Chunk
    score: float
    source: str
    rank: int = 0


class MedicineHit(BaseModel):
    """De-duplicated, medicine-level result with the best supporting chunk."""

    model_config = ConfigDict(frozen=False, arbitrary_types_allowed=True)

    medicine: Medicine
    score: float
    best_chunk: Chunk
    supporting_chunks: list[Chunk] = Field(default_factory=list)
