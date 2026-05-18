"""Shared user-profile model.

The FastAPI /chat endpoint validates incoming JSON against this schema; the
conversation service consumes the same object so we never juggle untyped
dicts past the HTTP boundary.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Gender = Literal["male", "female", "other"]


class UserProfile(BaseModel):
    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[Gender] = None
    isPregnant: Optional[bool] = None
    allergies: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)

    def has_meaningful_data(self) -> bool:
        return bool(
            self.age
            or self.gender
            or self.isPregnant
            or self.allergies
            or self.conditions
            or self.medications
        )
