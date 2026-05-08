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

Analizează imaginea și extrage următoarele informații:
- denumirea comercială (trade name) — numele cel mai vizibil pe cutie, dacă poți alege unul
- data expirării (expiration date) — caută "EXP", "Valabil până la", "Best before"
- concentrația (dosage) — ex: "500mg", "20mg/ml"
- forma farmaceutică (form) — comprimate, capsule, sirop, unguent, etc.
- TOT TEXTUL VIZIBIL pe cutie (all_text) — transcrie absolut tot ce poți citi:
  numele de mărci, substanțe active, indicații, producător, coduri, totul.
  Păstrează ordinea și liniile noi. Acest câmp e critic pentru identificare.

REGULI:
1. Returnează DOAR JSON, fără text suplimentar.
2. Pentru câmpurile structurate pe care nu le poți determina cu siguranță, returnează null.
3. all_text NU este nullable — dacă imaginea are orice text, transcrie-l. Dacă nu vezi
   absolut niciun text, returnează șir gol.
4. Data expirării în format YYYY-MM-DD. Dacă vezi doar luna și anul (ex: "08/2027"),
   folosește ultima zi din luna respectivă (ex: "2027-08-31").
5. Estimează propria încredere între 0.0 și 1.0.
"""

# JSON schema enforced by Gemini's structured-output mode.
_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "required": ["trade_name", "expiration_date", "dosage", "form", "confidence", "all_text"],
    "properties": {
        "trade_name":      {"type": "STRING", "nullable": True},
        "expiration_date": {"type": "STRING", "nullable": True},
        "dosage":          {"type": "STRING", "nullable": True},
        "form":            {"type": "STRING", "nullable": True},
        "confidence":      {"type": "NUMBER"},
        "all_text":        {"type": "STRING"},
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
        """Returns {trade_name, expiration_date, dosage, form, confidence, all_text}."""
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_RESPONSE_SCHEMA,  # type: ignore[arg-type]
            temperature=0.1,
            max_output_tokens=1024,
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
                "dosage": None, "form": None, "confidence": 0.0, "all_text": "",
            }
