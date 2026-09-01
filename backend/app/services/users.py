"""Application-user provisioning helpers (SAD §8). Used by seed scripts, not by spawn."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User
from backend.app.security.passwords import hash_password


async def upsert_local_user(session: AsyncSession, *, username: str, password: str) -> User:
    """Create or update a password-backed user. Capstone/local only — no self-signup API."""
    existing = (await session.execute(select(User).where(User.username == username))).scalar_one_or_none()
    digest = hash_password(password)
    if existing is None:
        user = User(username=username, password_hash=digest)
        session.add(user)
        await session.flush()
        return user
    existing.password_hash = digest
    await session.flush()
    return existing
