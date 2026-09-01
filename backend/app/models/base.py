"""Declarative base for all ORM models (SAD §4 application control plane)."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared metadata object; Alembic autogenerate targets `Base.metadata`."""
