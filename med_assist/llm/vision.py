"""Gemini Vision OCR for medicine packages. Returns a typed VisionExtraction."""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from google import genai
from google.genai import types
from pydantic import BaseModel

from med_assist.observability import observe

log = logging.getLogger("medassist.vision")

DEFAULT_VISION_MODEL = os.getenv("VISION_MODEL", "gemini-2.5-flash")


class VisionExtraction(BaseModel):
    """OCR result for a medicine package. Mirrors the SSE `ScanExtraction`
    shape consumed by the frontend; field names are snake_case to match
    the JSON schema enforced on Gemini's structured output."""

    trade_name: Optional[str] = None
    expiration_date: Optional[str] = None
    dosage: Optional[str] = None
    form: Optional[str] = None
    confidence: float = 0.0
    all_text: str = ""

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

    @observe(name="gemini.vision.extract_medicine")
    def extract_medicine(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> VisionExtraction:
        """OCR a medicine package. On API errors or empty responses, the
        diagnostic is surfaced via `all_text` so the frontend can show it."""
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_RESPONSE_SCHEMA,  # type: ignore[arg-type]
            temperature=0.1,
            max_output_tokens=1024,
        )
        try:
            response = self._client.models.generate_content(
                model=self._model_id,
                contents=[  # type: ignore[arg-type]
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    EXTRACTION_PROMPT_RO,
                ],
                config=config,
            )
        except Exception as exc:
            log.exception("Vision API call failed (model=%s)", self._model_id)
            return _empty_extraction(f"[VISION API ERROR] {type(exc).__name__}: {exc}")

        raw = (response.text or "").strip()
        log.info("Vision raw response (model=%s, %d chars): %s", self._model_id, len(raw), raw[:600])

        if not raw:
            finish_reason = ""
            try:
                finish_reason = str(response.candidates[0].finish_reason) if response.candidates else ""
            except Exception:
                pass
            return _empty_extraction(f"[VISION EMPTY RESPONSE] model={self._model_id} finish_reason={finish_reason}")

        try:
            data = json.loads(raw)
            if not data.get("all_text"):
                data["all_text"] = raw
            return VisionExtraction.model_validate(data)
        except json.JSONDecodeError as exc:
            log.warning("vision returned non-JSON: %s", raw[:500])
            return _empty_extraction(f"[VISION NON-JSON] {exc}\n--- raw response ---\n{raw[:1500]}")


def _empty_extraction(diagnostic: str) -> VisionExtraction:
    return VisionExtraction(all_text=diagnostic)
