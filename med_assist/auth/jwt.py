"""Auth0 JWT verification (RS256 vs JWKS, iss/aud/exp checked)."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Optional

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.algorithms import RSAAlgorithm

log = logging.getLogger(__name__)

_bearer_required = HTTPBearer(auto_error=True)
_bearer_optional = HTTPBearer(auto_error=False)


def _domain() -> str:
    d = os.getenv("AUTH0_DOMAIN")
    if not d:
        raise RuntimeError("AUTH0_DOMAIN not set.")
    return d.rstrip("/").replace("https://", "")


def _audience() -> str:
    a = os.getenv("AUTH0_AUDIENCE")
    if not a:
        raise RuntimeError("AUTH0_AUDIENCE not set.")
    return a


@lru_cache(maxsize=1)
def _jwks() -> dict:
    url = f"https://{_domain()}/.well-known/jwks.json"
    resp = httpx.get(url, timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def _public_key_for_kid(kid: str):
    for key in _jwks().get("keys", []):
        if key.get("kid") == kid:
            return RSAAlgorithm.from_jwk(key)
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown token signing key.")


def _verify_token(token: str) -> dict:
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Malformed token: {exc}") from exc
    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token missing kid header.")
    key = _public_key_for_kid(kid)
    try:
        return jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=_audience(),
            issuer=f"https://{_domain()}/",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired.")
    except jwt.InvalidAudienceError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token audience invalid.")
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Token rejected: {exc}") from exc


def current_user_sub(creds: HTTPAuthorizationCredentials = Depends(_bearer_required)) -> str:
    payload = _verify_token(creds.credentials)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token missing sub claim.")
    return str(sub)


def optional_user_sub(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_optional),
) -> Optional[str]:
    if creds is None:
        return None
    payload = _verify_token(creds.credentials)
    sub = payload.get("sub")
    return str(sub) if sub else None
