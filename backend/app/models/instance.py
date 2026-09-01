"""instances (SAD §4 logical tables; PRD §4.1 lifecycle).

`arlo_id` is the correspondence key: UI row = API path = `instances.arlo_id`
= (lowercased) Temporal Workflow Id.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class Instance(Base):
    __tablename__ = "instances"
    __table_args__ = (
        CheckConstraint(
            "ticket_system IN ('jira', 'servicenow')", name="instances_ticket_system_check"
        ),
        Index(
            "instances_active_ticket_uidx",
            "ticket_system",
            "ticket_key",
            unique=True,
            postgresql_where=text("status NOT IN ('Done', 'Rejected', 'Failed', 'Cancelled')"),
        ),
    )

    arlo_id: Mapped[str] = mapped_column(String, primary_key=True)
    ticket_system: Mapped[str] = mapped_column(String, nullable=False)
    ticket_key: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    proposal_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    proposal_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    workflow_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
