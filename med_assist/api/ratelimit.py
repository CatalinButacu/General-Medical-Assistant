"""Per-IP token bucket. In-memory; correct for single-replica HF Space."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from math import ceil

from fastapi import HTTPException, Request, status

log = logging.getLogger("medassist.ratelimit")


@dataclass
class _Bucket:
    tokens: float
    updated_at: float


class TokenBucketLimiter:
    """`rate_per_minute` tokens added per minute, capped at `burst`."""

    def __init__(self, rate_per_minute: float, burst: int):
        self.rate = rate_per_minute / 60.0
        self.burst = float(burst)
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def consume(self, key: str) -> tuple[bool, float]:
        """Try to take 1 token. Returns (allowed, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            b = self._buckets.get(key)
            if b is None:
                b = _Bucket(tokens=self.burst, updated_at=now)
                self._buckets[key] = b
            else:
                elapsed = now - b.updated_at
                b.tokens = min(self.burst, b.tokens + elapsed * self.rate)
                b.updated_at = now
            if b.tokens >= 1.0:
                b.tokens -= 1.0
                return True, 0.0
            wait = (1.0 - b.tokens) / self.rate if self.rate > 0 else 60.0
            return False, wait


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(limiter: TokenBucketLimiter, label: str):
    """FastAPI dependency factory. `label` is included in 429 logs for grep."""

    def _dep(request: Request) -> None:
        key = _client_ip(request)
        allowed, wait = limiter.consume(key)
        if not allowed:
            retry_after = max(1, ceil(wait))
            log.warning("rate limit hit: %s key=%s retry_after=%ds", label, key, retry_after)
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {label}. Retry in {retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )

    return _dep


# Defaults sized for HF Space free-tier traffic:
# - chat is streaming + LLM-heavy: 30/min with burst 10
# - scan calls Gemini Vision (~$0.0001/image): 10/min with burst 3
chat_limiter = TokenBucketLimiter(rate_per_minute=30, burst=10)
scan_limiter = TokenBucketLimiter(rate_per_minute=10, burst=3)
