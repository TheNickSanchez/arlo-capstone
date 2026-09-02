"""run_artifacts — instance-scoped dashboard artifacts (SAD §4 AD-17).

Append-only. A script refactor inserts a new row with a higher `attempt`;
prior versions stay visible on the Script tab.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base

ARTIFACT_TYPES = ("discovery_pack", "generated_script", "test_execution_log")


class RunArtifact(Base):
    __tablename__ = "run_artifacts"
    __table_args__ = (
        Index("run_artifacts_arlo_type_created_idx", "arlo_id", "artifact_type", "created_at"),
        Index("run_artifacts_arlo_type_attempt_idx", "arlo_id", "artifact_type", "attempt"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    arlo_id: Mapped[str] = mapped_column(
        String, ForeignKey("instances.arlo_id"), nullable=False
    )
    artifact_type: Mapped[str] = mapped_column(String, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by_agent: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
