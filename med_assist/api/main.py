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
from med_assist.llm.vision import VisionClient
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
_vision: Optional[VisionClient] = None


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


def get_vision() -> VisionClient:
    global _vision
    if _vision is None:
        _vision = VisionClient()
    return _vision


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


# ───────────────── /scan — image -> medicine identification ─────────────────


class ScanRequest(BaseModel):
    # Frontend captures via canvas.toDataURL("image/jpeg") → "data:image/jpeg;base64,...".
    # We accept either the full data URL or the bare base64.
    image_base64: str = Field(..., min_length=100, max_length=8_000_000)
    mime_type: str = Field("image/jpeg", pattern="^image/(jpeg|png|webp)$")


class ScanExtraction(BaseModel):
    trade_name: Optional[str]
    expiration_date: Optional[str]
    dosage: Optional[str]
    form: Optional[str]
    confidence: float


class ScanMedicineMatch(BaseModel):
    trade_name: str
    dci: str
    form: str
    concentration: str
    atc_code: str
    rx_status: str
    category: str
    lay_symptoms: list[str]
    rcp_url: str
    prospect_url: str
    match_score: float


class ScanResponse(BaseModel):
    extracted: ScanExtraction
    matched: Optional[ScanMedicineMatch]
    latency_ms: float


def _strip_data_url_prefix(b64: str) -> str:
    if b64.startswith("data:"):
        _, _, rest = b64.partition(",")
        return rest
    return b64


@app.post("/scan", response_model=ScanResponse)
def scan(req: ScanRequest) -> ScanResponse:
    """
    Identify a medicine from a captured photo of its packaging.

    Runs Gemini Vision for OCR + structured extraction, then matches the
    extracted trade name against the ANMDM corpus via the existing sparse
    retriever (BM25 over title chunks). Returns both the raw extraction
    and the best authoritative medicine record so the Cabinet add-flow
    has clean DCI / ATC / Rx-status fields to pre-fill.
    """
    import base64
    import time

    t0 = time.time()
    try:
        image_bytes = base64.b64decode(_strip_data_url_prefix(req.image_base64))
    except Exception as exc:
        raise ValueError(f"invalid base64: {exc}") from exc

    extracted = get_vision().extract_medicine(image_bytes, mime_type=req.mime_type)
    extraction_dto = ScanExtraction(
        trade_name=extracted.get("trade_name"),
        expiration_date=extracted.get("expiration_date"),
        dosage=extracted.get("dosage"),
        form=extracted.get("form"),
        confidence=float(extracted.get("confidence") or 0.0),
    )

    # Match the extracted trade name against ANMDM via sparse retrieval.
    # Title chunks are short and brand-specific so BM25 nails this.
    matched: Optional[ScanMedicineMatch] = None
    if extraction_dto.trade_name:
        svc = get_service()
        sparse_hits = svc._dedup_by_medicine(
            svc.sparse.search(extraction_dto.trade_name, top_k=5)
        )
        if sparse_hits:
            best = sparse_hits[0]
            med = svc._medicines_by_id.get(best.chunk.medicine_id)
            if med is not None:
                matched = ScanMedicineMatch(
                    trade_name=med.trade_name,
                    dci=med.dci,
                    form=med.form,
                    concentration=med.concentration,
                    atc_code=med.atc_code,
                    rx_status=med.rx_status,
                    category=med.category,
                    lay_symptoms=list(med.lay_symptoms),
                    rcp_url=med.rcp_url,
                    prospect_url=med.prospect_url,
                    match_score=best.score,
                )

    return ScanResponse(
        extracted=extraction_dto,
        matched=matched,
        latency_ms=round((time.time() - t0) * 1000, 1),
    )
