"""Gemini Flash client. GOOGLE_API_KEY from env, never reaches the frontend."""

from __future__ import annotations

import logging
import os
from typing import AsyncIterator, Iterable

from google import genai
from google.genai import types

from med_assist.observability import observe

log = logging.getLogger("medassist.llm")

DEFAULT_MODEL = "gemini-3-flash-preview"


class GeminiClient:
    def __init__(self, model_id: str = DEFAULT_MODEL, api_key: str | None = None):
        key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError(
                "Missing GOOGLE_API_KEY. Add to .env.local "
                "(get one free at https://aistudio.google.com/apikey)."
            )
        self._client = genai.Client(api_key=key)
        self._model_id = model_id

    @observe(name="gemini.stream", as_type="generation")
    async def stream(
        self,
        system_instruction: str,
        contents: list[types.ContentDict],
        temperature: float = 0.6,
        max_output_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        # thinking_config disables reasoning tokens (which silently consume max_output_tokens
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            )
        except (AttributeError, TypeError):
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
        try:
            stream = await self._client.aio.models.generate_content_stream(
                model=self._model_id,
                contents=contents,  # type: ignore[arg-type]
                config=config,
            )
            async for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except Exception as exc:  # surface upstream so /chat can return a clean error
            log.exception("Gemini stream failed: %s", exc)
            raise

    def model_id(self) -> str:
        return self._model_id


def build_history(messages: Iterable[dict]) -> list[types.ContentDict]:
    """Convert {role,text} list to Gemini ContentDict; system goes via system_instruction."""
    out: list[types.ContentDict] = []
    for m in messages:
        role = m.get("role", "")
        text = (m.get("text") or "").strip()
        if not text or role == "system":
            continue
        gemini_role = "model" if role in ("assistant", "model", "ai") else "user"
        out.append({"role": gemini_role, "parts": [{"text": text}]})
    return out
