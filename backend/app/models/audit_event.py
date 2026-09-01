"""audit_events (SAD §4). Append-only mirrored log for the dashboard.

No silent updates of past events (SAD §4). Application code must only INSERT
into this table — never UPDATE or DELETE a row.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("audit_events_arlo_at_idx", "arlo_id", "at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    arlo_id: Mapped[str] = mapped_column(String, ForeignKey("instances.arlo_id"), nullable=False)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    phase: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(String, nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    mcp_system: Mapped[str | None] = mapped_column(String, nullable=True)
    action: Mapped[str | None] = mapped_column(String, nullable=True)
    result: Mapped[str | None] = mapped_column(String, nullable=True)
    policy_deny: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
