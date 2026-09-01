"""Auth payloads (SAD §8: authenticated users; approver identity attributable)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    user_id: str
    username: str
    token: str
    """Bearer token, also set as an httpOnly session cookie on the response."""
