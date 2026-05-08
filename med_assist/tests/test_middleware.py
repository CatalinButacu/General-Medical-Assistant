"""Verify RequestIDMiddleware tags responses and honors inbound X-Request-ID."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from med_assist.api.middleware import RequestIDMiddleware


def _app():
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/ping")
    def ping(request: Request):
        return {"rid": request.state.request_id}

    return app


def test_generates_request_id_when_none_provided():
    client = TestClient(_app())
    r = client.get("/ping")
    assert r.status_code == 200
    rid_hdr = r.headers.get("X-Request-ID")
    rid_body = r.json()["rid"]
    assert rid_hdr and rid_hdr == rid_body
    assert len(rid_hdr) == 12  # hex shortened to 12 chars


def test_honors_inbound_request_id():
    client = TestClient(_app())
    r = client.get("/ping", headers={"X-Request-ID": "trace-abc-123"})
    assert r.headers["X-Request-ID"] == "trace-abc-123"
    assert r.json()["rid"] == "trace-abc-123"


def test_distinct_ids_across_requests():
    client = TestClient(_app())
    r1 = client.get("/ping")
    r2 = client.get("/ping")
    assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]
