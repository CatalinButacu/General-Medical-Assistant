"""
FastAPI service wrapping the med_assist triage + retrieval pipeline.

Endpoints:
  GET  /          -> built-in single-page HTML test UI (offline demo)
  GET  /health    -> liveness probe (used by ALB/App Runner health checks)
  POST /advise    -> {query, otc_only?, top_k?} -> structured TriageDecision
  GET  /manifest  -> index manifest (model id, dim, chunk count, build time)

Run locally:
  uvicorn med_assist.api.main:app --reload --port 8000
Then open http://localhost:8000 in a browser.
"""

from __future__ import annotations

import json
import time
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
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from med_assist.conversation import ChatMessageIn, ConversationService
from med_assist.llm.client import GeminiClient
from med_assist.service import RetrievalService

app = FastAPI(
    title="Med Assist API",
    description="Romanian RAG triage + medicine recommendation over the ANMDM nomenclator.",
    version="0.1.0",
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


class AdviseRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    otc_only: bool = True
    top_k: int = Field(5, ge=1, le=20)


class MedicineDTO(BaseModel):
    trade_name: str
    dci: str
    form: str
    concentration: str
    atc_code: str
    rx_status: str
    category: str
    lay_symptoms: list[str]
    score: float
    best_chunk_type: str
    best_chunk_snippet: str
    rcp_url: str
    prospect_url: str


class RedFlagDTO(BaseModel):
    name: str
    category: str
    description: str
    severity: str
    matched_pattern: str


class AdviseResponse(BaseModel):
    label: str
    rationale: str
    recommended_action_ro: str
    confidence: float
    red_flags: list[RedFlagDTO]
    medicines: list[MedicineDTO]
    latency_ms: float


def _to_dto(decision, latency_ms: float) -> AdviseResponse:
    medicines = [
        MedicineDTO(
            trade_name=h.medicine.trade_name,
            dci=h.medicine.dci,
            form=h.medicine.form,
            concentration=h.medicine.concentration,
            atc_code=h.medicine.atc_code,
            rx_status=h.medicine.rx_status,
            category=h.medicine.category,
            lay_symptoms=h.medicine.lay_symptoms,
            score=h.score,
            best_chunk_type=h.best_chunk.chunk_type,
            best_chunk_snippet=h.best_chunk.text[:300],
            rcp_url=h.medicine.rcp_url,
            prospect_url=h.medicine.prospect_url,
        )
        for h in decision.medicine_hits
    ]
    red_flags = [
        RedFlagDTO(
            name=rf.name,
            category=rf.category,
            description=rf.description,
            severity=rf.severity,
            matched_pattern=rf.matched_pattern,
        )
        for rf in decision.red_flags
    ]
    return AdviseResponse(
        label=decision.label,
        rationale=decision.rationale,
        recommended_action_ro=decision.recommended_action_ro,
        confidence=decision.confidence,
        red_flags=red_flags,
        medicines=medicines,
        latency_ms=round(latency_ms, 1),
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/manifest")
def manifest() -> dict:
    svc = get_service()
    return svc.manifest


@app.post("/advise", response_model=AdviseResponse)
def advise(req: AdviseRequest) -> AdviseResponse:
    svc = get_service()
    t0 = time.time()
    decision = svc.advise(req.query, top_k_medicines=req.top_k, otc_only=req.otc_only)
    latency_ms = (time.time() - t0) * 1000
    return _to_dto(decision, latency_ms)


# ───────────────── /chat — streaming conversational endpoint ─────────────────


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    text: str = Field(..., min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=20)


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Server-Sent Events stream of conversation events. Frontend reads with
    fetch+ReadableStream and splits on '\\n\\n'.

    Event kinds (one JSON payload per event):
      triage     — emitted first, contains label + red_flags + action
      medicines  — list of structured medicine cards (skipped on EMERGENCY)
      token      — text fragment from the LLM (skipped on EMERGENCY)
      done       — final event, indicates clean stream end
      error      — on failure
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


_INDEX_HTML = (Path(__file__).resolve().parent / "static" / "index.html").read_text(encoding="utf-8") \
    if (Path(__file__).resolve().parent / "static" / "index.html").exists() else ""


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    if _INDEX_HTML:
        return HTMLResponse(_INDEX_HTML)
    return HTMLResponse("<h1>Med Assist API</h1><p>POST to /advise. Demo UI not built.</p>")
