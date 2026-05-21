"""Optional Langfuse tracing.

Decorating the orchestrator's hot path with `@observe` gives a per-turn trace
tree in Langfuse: red-flag scan → intent classify → retrieve → LLM stream.
This is the "stay put on orchestration, add tracing" path from the agent-design
review — zero behavioural change, full replay on demand.

When `langfuse` is not installed, `observe` is a no-op identity decorator so
tests, CI, and any deployment without tracing pay zero cost. When the package
is present but the env vars (`LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`,
`LANGFUSE_SECRET_KEY`) are unset, Langfuse itself becomes a no-op — the SDK
handles that, we don't need to gate it here.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, TypeVar

log = logging.getLogger("medassist.tracing")

F = TypeVar("F", bound=Callable[..., Any])


try:
    from langfuse import observe as _langfuse_observe  # type: ignore[import-not-found]
    _LANGFUSE_AVAILABLE = True
    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        log.info("langfuse tracing active (host=%s)", os.getenv("LANGFUSE_HOST") or "cloud")
except ImportError:
    _LANGFUSE_AVAILABLE = False
    _langfuse_observe = None  # type: ignore[assignment]


def observe(name: str | None = None, **kwargs: Any) -> Callable[[F], F]:
    """A drop-in @observe that becomes a no-op when langfuse isn't installed."""
    if _LANGFUSE_AVAILABLE and _langfuse_observe is not None:
        return _langfuse_observe(name=name, **kwargs)  # type: ignore[no-any-return]

    def _noop(fn: F) -> F:
        return fn

    return _noop
