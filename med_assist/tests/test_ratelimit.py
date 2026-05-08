"""Token bucket math + FastAPI dependency integration."""

from __future__ import annotations

import time

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from med_assist.api.ratelimit import TokenBucketLimiter, rate_limit


def test_burst_allows_n_then_blocks():
    lim = TokenBucketLimiter(rate_per_minute=60, burst=3)
    assert lim.consume("a")[0] is True
    assert lim.consume("a")[0] is True
    assert lim.consume("a")[0] is True
    allowed, wait = lim.consume("a")
    assert allowed is False
    assert wait > 0


def test_keys_are_isolated():
    lim = TokenBucketLimiter(rate_per_minute=60, burst=1)
    assert lim.consume("a")[0] is True
    assert lim.consume("a")[0] is False
    # different key still has its own bucket
    assert lim.consume("b")[0] is True


def test_refills_over_time():
    lim = TokenBucketLimiter(rate_per_minute=600, burst=1)  # 10/sec
    assert lim.consume("a")[0] is True
    assert lim.consume("a")[0] is False
    time.sleep(0.15)  # gives ~1.5 tokens back
    assert lim.consume("a")[0] is True


def test_dependency_returns_429_with_retry_after():
    lim = TokenBucketLimiter(rate_per_minute=60, burst=1)
    app = FastAPI()

    @app.get("/x", dependencies=[Depends(rate_limit(lim, "x"))])
    def handler():
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/x").status_code == 200
    r = client.get("/x")
    assert r.status_code == 429
    assert "Retry-After" in r.headers
    assert int(r.headers["Retry-After"]) >= 1


def test_dependency_keys_by_forwarded_for():
    lim = TokenBucketLimiter(rate_per_minute=60, burst=1)
    app = FastAPI()

    @app.get("/x", dependencies=[Depends(rate_limit(lim, "x"))])
    def handler():
        return {"ok": True}

    client = TestClient(app)
    # Same forwarded IP exhausts after 1 hit.
    assert client.get("/x", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
    assert client.get("/x", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 429
    # Different forwarded IP gets its own bucket.
    assert client.get("/x", headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 200
