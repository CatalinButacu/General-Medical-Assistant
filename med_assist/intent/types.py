"""Public types for intent detection."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from med_assist.data.models import Medicine

IntentLabel = Literal[
    "SYMPTOM_TRIAGE",
    "MEDICINE_LOOKUP",
]


class IntentResult(BaseModel):
    model_config = ConfigDict(frozen=False, arbitrary_types_allowed=True)

    label: IntentLabel
    confidence: float = Field(ge=0.0, le=1.0)
    medicine: Optional[Medicine] = None
    matched_terms: list[str] = Field(default_factory=list)
    rationale: str = ""
