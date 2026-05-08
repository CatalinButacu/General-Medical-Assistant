"""Test fixtures for the user-data endpoints.

Strategy:
- Build a minimal FastAPI app with just the /user/* router (so tests don't
  drag in the heavy retrieval/LLM stack from `med_assist.api.main`).
- Override `get_session` with an in-memory SQLite session.
- Override `current_user_sub` with a plain function so tests can switch
  identities without forging real Auth0 JWTs.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from med_assist.api.chats import router as chats_router
from med_assist.api.users import router as users_router
from med_assist.auth import current_user_sub
from med_assist.db import Base, get_session


@pytest.fixture
def db_engine():
    # StaticPool makes all sessions share one in-memory connection — otherwise
    # each new session would get a fresh, empty SQLite DB.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_factory(db_engine):
    return sessionmaker(bind=db_engine, autoflush=False, autocommit=False, expire_on_commit=False)


@pytest.fixture
def app(db_factory):
    """A test app exposing only /user/* — no retrieval/LLM imports."""
    test_app = FastAPI()
    test_app.include_router(users_router)
    test_app.include_router(chats_router)

    def override_get_session():
        session: Session = db_factory()
        try:
            yield session
        finally:
            session.close()

    test_app.dependency_overrides[get_session] = override_get_session
    return test_app


@pytest.fixture
def as_user(app):
    """Returns a callable that switches the JWT-derived user_sub the app sees."""
    def _set(sub: str) -> None:
        app.dependency_overrides[current_user_sub] = lambda: sub
    return _set


@pytest.fixture
def client(app, as_user):
    as_user("default-test-user")
    return TestClient(app)


@pytest.fixture
def anon_client(app):
    """Client where current_user_sub raises 401 (real auth path)."""
    return TestClient(app)
