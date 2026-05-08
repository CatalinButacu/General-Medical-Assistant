"""Request-scoped observability: per-request ID, access logs, log-record tagging."""

from __future__ import annotations

import contextvars
import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

access_log = logging.getLogger("medassist.access")

# Read by the LogRecordFactory below, so every record emitted during a request
# is tagged with the same id without callers having to thread it through.
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        token = request_id_var.set(rid)
        request.state.request_id = rid
        t0 = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            dur_ms = (time.perf_counter() - t0) * 1000
            access_log.exception("%s %s -> 500 (%.1f ms)", request.method, request.url.path, dur_ms)
            raise
        else:
            dur_ms = (time.perf_counter() - t0) * 1000
            response.headers["X-Request-ID"] = rid
            access_log.info(
                "%s %s -> %d (%.1f ms)",
                request.method, request.url.path, response.status_code, dur_ms,
            )
            return response
        finally:
            request_id_var.reset(token)


def install_request_id_log_factory() -> None:
    """Inject request_id onto every LogRecord so the formatter can show it."""
    base_factory = logging.getLogRecordFactory()

    def factory(*args, **kwargs):
        record = base_factory(*args, **kwargs)
        record.request_id = request_id_var.get()
        return record

    logging.setLogRecordFactory(factory)
