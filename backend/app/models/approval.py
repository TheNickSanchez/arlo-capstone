"""approvals (SAD §4). Persisted before (or in the same request as) the Signal."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class Approval(Base):
    __tablename__ = "approvals"
    __table_args__ = (
        CheckConstraint("action IN ('approve', 'reject', 'cancel')", name="approvals_action_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    arlo_id: Mapped[str] = mapped_column(String, ForeignKey("instances.arlo_id"), nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    proposal_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    frozen_actions_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    rationale: Mapped[str | None] = mapped_column(String, nullable=True)
