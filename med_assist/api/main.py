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

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from med_assist.api.ratelimit import chat_limiter, rate_limit, scan_limiter
from med_assist.conversation import ChatMessageIn, ConversationService
from med_assist.llm.client import GeminiClient
from med_assist.llm.vision import VisionClient
from med_assist.profile import UserProfile
from med_assist.service import RetrievalService

logger = logging.getLogger("medassist.api")

app = FastAPI(title="Med Assist API", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


class ScanExtraction(BaseModel):
    trade_name: Optional[str]
    expiration_date: Optional[str]
    dosage: Optional[str]
    form: Optional[str]
    confidence: float
    all_text: str = ""


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
    candidates: list[ScanMedicineMatch] = Field(default_factory=list)
    latency_ms: float


def _strip_data_url_prefix(b64: str) -> str:
    if b64.startswith("data:"):
        _, _, rest = b64.partition(",")
        return rest
    return b64


def _strip_pharma_suffixes(name: str) -> str:
    """Strip dose/form noise so a partial OCR like 'PARACETAMOL ZENTIVA 500MG' still matches."""
    import re
    s = re.sub(r"\b\d+([\.,]\d+)?\s*(mg/ml|mg|ml|mcg|μg|g|ui|iu)\b", " ", name, flags=re.I)
    s = re.sub(r"\b(comprimate|capsule|sirop|unguent|drajeuri|filmate|orala|suspensie|crema|sol\.?)\b", " ", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip()


# Romanian + English stopwords + pharma packaging boilerplate that adds noise to OCR-text matching.
_OCR_STOPWORDS = frozenset({
    "de", "la", "cu", "si", "in", "pe", "din", "sau", "pentru", "fara", "intre", "doar",
    "the", "and", "of", "for", "with", "to", "in",
    "lot", "exp", "expirare", "valabil", "pana", "fabricat", "import", "importator",
    "produs", "prospect", "rcp", "atc", "anmdm", "comprimate", "capsule", "filmate",
    "sirop", "unguent", "crema", "drajeuri", "orala", "soluție", "suspensie", "sol",
    "mg", "ml", "mcg", "ui", "iu", "ug", "tablete", "ambalaj", "buc", "buc.",
})


def _ocr_query_phrases(all_text: str) -> list[str]:
    """Extract candidate query strings from OCR dump: per-line phrases + 2-3-word substrings,
    filtered down to phrases that are mostly alphabetic and not entirely stopwords."""
    import re
    phrases: list[str] = []
    seen: set[str] = set()
    for line in all_text.splitlines():
        cleaned = re.sub(r"[^A-Za-zĂÂÎȘȚăâîșț0-9 \-]", " ", line)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            continue
        words = [w for w in cleaned.split() if len(w) >= 3 and not w.isdigit() and w.lower() not in _OCR_STOPWORDS]
        if not words:
            continue
        full = " ".join(words)
        if full not in seen:
            seen.add(full)
            phrases.append(full)
        # add 2- and 3-word windows as additional candidate queries
        for n in (3, 2):
            for i in range(len(words) - n + 1):
                window = " ".join(words[i:i + n])
                if window not in seen:
                    seen.add(window)
                    phrases.append(window)
    return phrases[:25]  # cap so a verbose OCR doesn't run hundreds of searches


def _hit_to_match_dto(svc: "RetrievalService", hit) -> Optional[ScanMedicineMatch]:
    med = svc._medicines_by_id.get(hit.chunk.medicine_id)
    if med is None:
        return None
    return ScanMedicineMatch(
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
        match_score=hit.score,
    )


@app.post("/scan", response_model=ScanResponse, dependencies=[Depends(rate_limit(scan_limiter, "scan"))])
def scan(req: ScanRequest) -> ScanResponse:
    """OCR a medicine box and match the trade name back to ANMDM."""
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
        all_text=extracted.get("all_text") or "",
    )

    # Two-stage match: (1) Gemini's chosen trade_name + dose-stripped variant.
    # (2) If still weak, sweep the full OCR dump as multi-word queries, merge.
    # The all_text fallback handles cases where Gemini misidentifies which
    # text on the box is the actual brand name.
    svc = get_service()
    best_by_id: dict = {}  # medicine_id -> best RetrievalHit so far

    def _record(hits):
        for h in hits:
            mid = h.chunk.medicine_id
            prev = best_by_id.get(mid)
            if prev is None or h.score > prev.score:
                best_by_id[mid] = h

    if extraction_dto.trade_name:
        _record(svc._dedup_by_medicine(svc.sparse.search(extraction_dto.trade_name, top_k=5)))
        stripped = _strip_pharma_suffixes(extraction_dto.trade_name)
        if stripped and stripped.upper() != extraction_dto.trade_name.upper():
            _record(svc._dedup_by_medicine(svc.sparse.search(stripped, top_k=5)))

    top_so_far = max((h.score for h in best_by_id.values()), default=0.0)
    if top_so_far < 0.05 and extraction_dto.all_text:
        for phrase in _ocr_query_phrases(extraction_dto.all_text):
            _record(svc._dedup_by_medicine(svc.sparse.search(phrase, top_k=3)))

    sorted_hits = sorted(best_by_id.values(), key=lambda h: -h.score)
    candidates: list[ScanMedicineMatch] = []
    for hit in sorted_hits[:3]:
        dto = _hit_to_match_dto(svc, hit)
        if dto is not None:
            candidates.append(dto)
    matched: Optional[ScanMedicineMatch] = candidates[0] if candidates else None

    return ScanResponse(
        extracted=extraction_dto,
        matched=matched,
        candidates=candidates,
        latency_ms=round((time.time() - t0) * 1000, 1),
    )
