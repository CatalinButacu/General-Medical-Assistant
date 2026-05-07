"""SQLAlchemy engine + session factory. Lazy: no DATABASE_URL required for chat/scan endpoints."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def _normalize_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL not set. User-data endpoints disabled. "
            "Expected postgresql://user:pass@host:5432/dbname."
        )
    return create_engine(_normalize_url(url), pool_pre_ping=True, pool_size=5, max_overflow=5)


@lru_cache(maxsize=1)
def _session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    session = _session_factory()()
    try:
        yield session
    finally:
        session.close()
