"""FastAPI auth dependency (SAD §4/§8: auth required except /health, /ready).

Accepts either the `Authorization: Bearer <token>` header or the
`arlo_session` cookie. No anonymous Approve (PRD §5 access control).
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Cookie, Header

from backend.app.domain.errors import UnauthenticatedError
from backend.app.security.tokens import InvalidTokenError, verify_token

SESSION_COOKIE_NAME = "arlo_session"


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    username: str


async def get_current_user(
    authorization: str | None = Header(default=None),
    arlo_session: str | None = Cookie(default=None),
) -> CurrentUser:
    token: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[len("bearer ") :].strip()
    elif arlo_session:
        token = arlo_session

    if not token:
        raise UnauthenticatedError("missing bearer token or session cookie")

    try:
        principal = verify_token(token)
    except InvalidTokenError as exc:
        raise UnauthenticatedError(f"invalid session: {exc}") from exc

    return CurrentUser(user_id=principal.user_id, username=principal.username)
