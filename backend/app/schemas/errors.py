"""Error envelope schema (SAD §4): `{ "error": { "code", "message", "arlo_id" } }`."""

from __future__ import annotations

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    arlo_id: str | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail
