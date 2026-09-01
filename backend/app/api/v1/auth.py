"""Auth router (SAD §8: authenticated users; approver identity attributable).

Every other `/api/v1` endpoint depends on `get_current_user`, and
`approvals.actor_id` must resolve to a real `users.id`. Users are provisioned
via `scripts/seed_admin.py`; this router authenticates existing rows only.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_session
from backend.app.domain.errors import UnauthenticatedError
from backend.app.models.user import User
from backend.app.schemas.auth import LoginRequest, LoginResponse
from backend.app.security.dependencies import SESSION_COOKIE_NAME
from backend.app.security.passwords import verify_password
from backend.app.security.tokens import issue_token

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> LoginResponse:
    result = await session.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if user is None or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise UnauthenticatedError("invalid username or password")

    token = issue_token(user.id, user.username)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=12 * 60 * 60,
    )
    return LoginResponse(user_id=str(user.id), username=user.username, token=token)


@router.post("/auth/logout")
async def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"ok": True}
