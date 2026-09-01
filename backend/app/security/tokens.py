"""Signed session tokens (SAD §8: "session cookie or signed token").

A compact HMAC-SHA256 signed token, functionally equivalent to a JWS HS256
token but implemented with stdlib only. Used both as the `Authorization:
Bearer` value and as the `arlo_session` cookie payload so the frontend may use
either transport (SAD §3 API client boundary; integration.md Open Question).

`ARLO_SESSION_SECRET` must be set in any environment where tokens must survive
a process restart. If unset, an ephemeral per-process secret is generated so
local `*develop-be` work is not blocked — sessions simply do not survive a
worker/API restart in that mode (logged once at import time).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass

from backend.app.config import settings

logger = logging.getLogger("arlo.security.tokens")

_DEFAULT_TTL_SECONDS = 12 * 60 * 60  # 12h session lifetime


def _resolve_secret() -> bytes:
    if settings.arlo_session_secret:
        return settings.arlo_session_secret.encode("utf-8")
    logger.warning(
        "ARLO_SESSION_SECRET is unset; using an ephemeral per-process secret. "
        "Sessions will not survive a restart. Set ARLO_SESSION_SECRET for any "
        "persistent environment (SAD §4 secrets)."
    )
    return os.urandom(32)


_SECRET = _resolve_secret()


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


@dataclass(frozen=True)
class SessionPrincipal:
    user_id: str
    username: str
    issued_at: float
    expires_at: float


class InvalidTokenError(Exception):
    """Signature mismatch, malformed token, or expired session."""


def issue_token(user_id: uuid.UUID | str, username: str, *, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> str:
    now = time.time()
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(_SECRET, body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64url_encode(signature)}"


def verify_token(token: str) -> SessionPrincipal:
    try:
        body, signature_b64 = token.split(".", 1)
    except ValueError as exc:
        raise InvalidTokenError("malformed token") from exc

    expected_signature = hmac.new(_SECRET, body.encode("ascii"), hashlib.sha256).digest()
    try:
        provided_signature = _b64url_decode(signature_b64)
    except Exception as exc:
        raise InvalidTokenError("malformed signature") from exc

    if not hmac.compare_digest(expected_signature, provided_signature):
        raise InvalidTokenError("signature mismatch")

    try:
        payload = json.loads(_b64url_decode(body))
    except Exception as exc:
        raise InvalidTokenError("malformed payload") from exc

    if payload.get("exp", 0) < time.time():
        raise InvalidTokenError("token expired")

    return SessionPrincipal(
        user_id=payload["sub"],
        username=payload["username"],
        issued_at=payload["iat"],
        expires_at=payload["exp"],
    )
