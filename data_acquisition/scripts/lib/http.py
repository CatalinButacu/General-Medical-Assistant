"""
Polite HTTP fetcher with rate limiting, retry, and on-disk caching.

ANMDM is a public regulatory site funded by Romanian taxpayers. We pull
slowly (default 0.5 req/s), identify ourselves clearly, and cache hard so
re-runs don't hammer the server.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

import requests

USER_AGENT = "MedAssistResearch/0.1 (educational; contact butacu.catalin@yahoo.com)"

log = logging.getLogger(__name__)


class PoliteFetcher:
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        min_interval_s: float = 2.0,
        max_retries: int = 3,
        timeout_s: int = 30,
    ):
        self.cache_dir = cache_dir
        self.min_interval_s = min_interval_s
        self.max_retries = max_retries
        self.timeout_s = timeout_s
        self._last_request_at = 0.0
        self._session = requests.Session()
        self._session.headers["User-Agent"] = USER_AGENT
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval_s:
            time.sleep(self.min_interval_s - elapsed)
        self._last_request_at = time.monotonic()

    def get_bytes(self, url: str, cache_key: Optional[str] = None) -> bytes:
        """Fetch bytes; cache to disk if cache_key provided."""
        if cache_key is not None and self.cache_dir is not None:
            cached = self.cache_dir / cache_key
            if cached.exists():
                return cached.read_bytes()

        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            self._wait()
            try:
                resp = self._session.get(url, timeout=self.timeout_s)
                resp.raise_for_status()
                if cache_key is not None and self.cache_dir is not None:
                    cached_path = self.cache_dir / cache_key
                    cached_path.parent.mkdir(parents=True, exist_ok=True)
                    cached_path.write_bytes(resp.content)
                return resp.content
            except requests.RequestException as exc:
                last_exc = exc
                backoff = 2 ** attempt
                log.warning(
                    "fetch failed (attempt %d/%d) %s: %s — backing off %ds",
                    attempt + 1, self.max_retries, url, exc, backoff,
                )
                time.sleep(backoff)
        raise RuntimeError(f"failed to fetch {url} after {self.max_retries} attempts") from last_exc

    def get_text(self, url: str, cache_key: Optional[str] = None, encoding: str = "utf-8") -> str:
        return self.get_bytes(url, cache_key).decode(encoding, errors="replace")
