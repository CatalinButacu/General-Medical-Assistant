"""Gemini Vision OCR for medicine packages. Returns structured JSON."""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from google import genai
from google.genai import types

log = logging.getLogger(__name__)

DEFAULT_VISION_MODEL = "gemini-3-flash-preview"

EXTRACTION_PROMPT_RO = """\
Ești un asistent care identifică medicamente din fotografia ambalajului.

Analizează imaginea și extrage următoarele informații, dacă sunt vizibile:
- denumirea comercială (trade name) — numele cel mai vizibil pe cutie
- data expirării (expiration date) — caută "EXP", "Valabil până la", "Best before"
- concentrația (dosage) — ex: "500mg", "20mg/ml"
- forma farmaceutică (form) — comprimate, capsule, sirop, unguent, etc.

REGULI:
1. Returnează DOAR JSON, fără text suplimentar.
2. Pentru câmpurile pe care nu le poți determina, returnează null.
3. Data expirării în format YYYY-MM-DD. Dacă vezi doar luna și anul (ex: "08/2027"),
   folosește ultima zi din luna respectivă (ex: "2027-08-31").
4. Estimează propria încredere între 0.0 și 1.0:
   - 1.0 = totul foarte clar
   - 0.5 = imagine neclară sau text parțial vizibil
   - 0.2 = nu pot identifica nimic cu siguranță
"""

# JSON schema enforced by Gemini's structured-output mode.
_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "required": ["trade_name", "expiration_date", "dosage", "form", "confidence"],
    "properties": {
        "trade_name":      {"type": "STRING", "nullable": True},
        "expiration_date": {"type": "STRING", "nullable": True},
        "dosage":          {"type": "STRING", "nullable": True},
        "form":            {"type": "STRING", "nullable": True},
        "confidence":      {"type": "NUMBER"},
    },
}


class VisionClient:
    def __init__(self, model_id: str = DEFAULT_VISION_MODEL, api_key: Optional[str] = None):
        key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("Missing GOOGLE_API_KEY (set in .env.local).")
        self._client = genai.Client(api_key=key)
        self._model_id = model_id

    def extract_medicine(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
        """Returns {trade_name, expiration_date, dosage, form, confidence}."""
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_RESPONSE_SCHEMA,  # type: ignore[arg-type]
            temperature=0.1,
            max_output_tokens=300,
        )
        response = self._client.models.generate_content(
            model=self._model_id,
            contents=[  # type: ignore[arg-type]
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                EXTRACTION_PROMPT_RO,
            ],
            config=config,
        )
        try:
            return json.loads(response.text or "{}")
        except json.JSONDecodeError:
            log.warning("vision returned non-JSON: %s", (response.text or "")[:200])
            return {
                "trade_name": None, "expiration_date": None,
                "dosage": None, "form": None, "confidence": 0.0,
            }
