"""FastAPI service: /health /manifest /chat /scan /user/*."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env.local")
load_dotenv(_ROOT / ".env")

from med_assist.api.middleware import RequestIDMiddleware, install_request_id_log_factory

# install_request_id_log_factory must run before basicConfig so the %(request_id)s
# field is populated on every record from the very first log line.
install_request_id_log_factory()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] req=%(request_id)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
for noisy in ("httpx", "httpcore", "urllib3", "google.api_core", "google.auth"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from med_assist.api.ratelimit import chat_limiter, rate_limit, scan_limiter
from med_assist.conversation import ChatMessageIn, ConversationService
from med_assist.llm.client import GeminiClient
from med_assist.llm.vision import VisionClient, VisionExtraction
from med_assist.profile import UserProfile
from med_assist.service import RetrievalService

logger = logging.getLogger("medassist.api")

app = FastAPI(title="Med Assist API", version="0.3.0")

# Pin to the GitHub Pages origin in production via CORS_ORIGINS env var
# (comma-separated). Default to local-dev origins so a fresh clone works.
_default_cors = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", _default_cors).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
# Added LAST so it wraps everything else and tags the full request lifecycle.
app.add_middleware(RequestIDMiddleware)

if os.getenv("DATABASE_URL") and os.getenv("AUTH0_AUDIENCE"):
    from med_assist.api.chats import router as chats_router
    from med_assist.api.users import router as users_router
    app.include_router(users_router)
    app.include_router(chats_router)


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
    profile: Optional[UserProfile] = None


@app.post("/chat", dependencies=[Depends(rate_limit(chat_limiter, "chat"))])
async def chat(req: ChatRequest):
    """SSE stream of intent / triage / medicines / token / done / error events."""
    convo = get_conversation()
    history = [ChatMessageIn(role=m.role, text=m.text) for m in req.messages]

    async def sse_stream():
        try:
            async for event in convo.stream_turn(history, profile=req.profile):
                yield f"event: {event.kind}\ndata: {json.dumps(event.payload, ensure_ascii=False)}\n\n"
        except Exception:
            logger.exception("Unhandled error while streaming /chat SSE response")
            payload = {"message": "An internal error has occurred."}
            yield f"event: error\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        sse_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class ScanRequest(BaseModel):
    image_base64: str = Field(..., min_length=100, max_length=8_000_000)
    mime_type: str = Field("image/jpeg", pattern="^image/(jpeg|png|webp)$")


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
    extracted: VisionExtraction
    matched: Optional[ScanMedicineMatch]
    candidates: list[ScanMedicineMatch] = Field(default_factory=list)
    latency_ms: float


def _strip_data_url_prefix(b64: str) -> str:
    if b64.startswith("data:"):
        _, _, rest = b64.partition(",")
        return rest
    return b64


@app.post("/scan", response_model=ScanResponse, dependencies=[Depends(rate_limit(scan_limiter, "scan"))])
def scan(req: ScanRequest) -> ScanResponse:
    """OCR a medicine box and match the trade name back to ANMDM."""
    import base64
    import time

    t0 = time.time()
    try:
        image_bytes = base64.b64decode(_strip_data_url_prefix(req.image_base64))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid base64: {exc}") from exc

    extracted = get_vision().extract_medicine(image_bytes, mime_type=req.mime_type)

    hits = get_service().match_by_name(extracted.trade_name, extracted.all_text)
    candidates: list[ScanMedicineMatch] = [
        ScanMedicineMatch(
            trade_name=h.medicine.trade_name,
            dci=h.medicine.dci,
            form=h.medicine.form,
            concentration=h.medicine.concentration,
            atc_code=h.medicine.atc_code,
            rx_status=h.medicine.rx_status,
            category=h.medicine.category,
            lay_symptoms=list(h.medicine.lay_symptoms),
            rcp_url=h.medicine.rcp_url,
            prospect_url=h.medicine.prospect_url,
            match_score=h.score,
        )
        for h in hits
    ]
    matched: Optional[ScanMedicineMatch] = candidates[0] if candidates else None

    return ScanResponse(
        extracted=extracted,
        matched=matched,
        candidates=candidates,
        latency_ms=round((time.time() - t0) * 1000, 1),
    )
