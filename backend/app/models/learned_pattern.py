"""learned_patterns — Shared Operational Memory (SAD §4 AD-13).

Cross-instance, structured fixes. Retrieved (SELECT) during Investigation;
inserted or incremented only by the Validation Activity after a successful
Validation. Never persisted on Reject / Failed / Cancelled.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class LearnedPattern(Base):
    __tablename__ = "learned_patterns"
    __table_args__ = (
        Index("learned_patterns_app_name_idx", "app_name"),
        Index("learned_patterns_platform_idx", "platform"),
        Index(
            "learned_patterns_natural_key_idx",
            "app_name",
            "platform",
            "pattern_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    app_name: Mapped[str] = mapped_column(String, nullable=False)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    pattern_type: Mapped[str] = mapped_column(String, nullable=False)
    problem_description: Mapped[str] = mapped_column(String, nullable=False)
    problem_description_hash: Mapped[str] = mapped_column(String, nullable=False)
    solution_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_by_arlo_id: Mapped[str] = mapped_column(String, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
