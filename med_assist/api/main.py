"""
FastAPI service for the med_assist conversational triage chatbot.

Endpoints:
  GET  /health    liveness probe
  GET  /manifest  index manifest (model id, dim, chunk count, build time)
  POST /chat      Server-Sent Events stream — full conversational pipeline
                  (red-flag triage, follow-up gating, retrieval, grounded LLM)

Run locally:
  uvicorn med_assist.api.main:app --port 8000 --reload
.env.local is loaded automatically — no shell sourcing needed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

# Load .env.local before anything that reads env vars (e.g. GOOGLE_API_KEY).
# Works the same on Windows, macOS, Linux — no shell sourcing needed.
from dotenv import load_dotenv
_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env.local")
load_dotenv(_ROOT / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from med_assist.conversation import ChatMessageIn, ConversationService
from med_assist.llm.client import GeminiClient
from med_assist.service import RetrievalService

app = FastAPI(
    title="Med Assist API",
    description="Romanian RAG triage chatbot over the ANMDM nomenclator.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


_service: Optional[RetrievalService] = None
_conversation: Optional[ConversationService] = None


def get_service() -> RetrievalService:
    global _service
    if _service is None:
        _service = RetrievalService()
    return _service


def get_conversation() -> ConversationService:
    global _conversation
    if _conversation is None:
        _conversation = ConversationService(retrieval=get_service(), llm=GeminiClient())
    return _conversation


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/manifest")
def manifest() -> dict:
    return get_service().manifest


# ───────────────── /chat — streaming conversational endpoint ─────────────────


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    text: str = Field(..., min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=20)


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Server-Sent Events stream. Frontend reads with fetch+ReadableStream
    and splits on '\\n\\n'.

    Event kinds (one JSON payload per event):
      triage     emitted first, contains label + red_flags + action
                 label is 'EMERGENCY' | 'OTC_SAFE' | 'UNCERTAIN' | 'FOLLOWUP'
      medicines  list of structured medicine cards (skipped on EMERGENCY/FOLLOWUP)
      token      text fragment from the LLM (skipped on EMERGENCY)
      done       final event, indicates clean stream end
      error      on failure
    """
    convo = get_conversation()
    history = [ChatMessageIn(role=m.role, text=m.text) for m in req.messages]

    async def sse_stream():
        try:
            async for event in convo.stream_turn(history):
                yield f"event: {event.kind}\ndata: {json.dumps(event.payload, ensure_ascii=False)}\n\n"
        except Exception as exc:
            payload = {"message": f"server error: {str(exc)[:200]}"}
            yield f"event: error\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        sse_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
