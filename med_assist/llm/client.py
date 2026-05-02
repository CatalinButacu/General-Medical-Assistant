"""
Gemini Flash client wrapper.

Provider-agnostic enough that swapping to OpenAI / Anthropic later means
implementing the same `LLMClient` protocol — but for now we hardcode the
google-genai SDK against gemini-3.0-flash on the free tier.

Reads `GOOGLE_API_KEY` from the environment. The frontend posts to /chat
without ever seeing the key.
"""

from __future__ import annotations

import logging
import os
from typing import AsyncIterator, Iterable

from google import genai
from google.genai import types

log = logging.getLogger(__name__)

# Latest Gemini 3 Flash (preview as of May 2026). Swap to
# `gemini-flash-latest` for the auto-tracked stable channel,
# or `gemini-2.5-flash` for the previous GA release.
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

    async def stream(
        self,
        system_instruction: str,
        contents: list[types.ContentDict],
        temperature: float = 0.6,
        max_output_tokens: int = 400,
    ) -> AsyncIterator[str]:
        """Yield text chunks from a streaming generation."""
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
    """
    Frontend sends a list of {role: 'user'|'assistant', text: str}.
    Convert to Gemini's ContentDict shape with role 'user'|'model' and
    parts[{text}]. Drop empty/system messages — system goes via system_instruction.
    """
    out: list[types.ContentDict] = []
    for m in messages:
        role = m.get("role", "")
        text = (m.get("text") or "").strip()
        if not text or role == "system":
            continue
        gemini_role = "model" if role in ("assistant", "model", "ai") else "user"
        out.append({"role": gemini_role, "parts": [{"text": text}]})
    return out
