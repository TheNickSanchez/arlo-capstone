"""run_artifacts table (SAD §4 AD-17).

Revision ID: 0002_run_artifacts
Revises: 0001_initial_schema
Create Date: 2026-09-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_run_artifacts"
down_revision: str | None = "0001_initial_schema"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "run_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("arlo_id", sa.String(), sa.ForeignKey("instances.arlo_id"), nullable=False),
        sa.Column("artifact_type", sa.String(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("content_json", postgresql.JSONB(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_by_agent", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "artifact_type IN ('discovery_pack', 'generated_script', 'test_execution_log')",
            name="run_artifacts_type_check",
        ),
    )
    op.create_index(
        "run_artifacts_arlo_type_created_idx",
        "run_artifacts",
        ["arlo_id", "artifact_type", "created_at"],
    )
    op.create_index(
        "run_artifacts_arlo_type_attempt_idx",
        "run_artifacts",
        ["arlo_id", "artifact_type", "attempt"],
    )


def downgrade() -> None:
    op.drop_index("run_artifacts_arlo_type_attempt_idx", table_name="run_artifacts")
    op.drop_index("run_artifacts_arlo_type_created_idx", table_name="run_artifacts")
    op.drop_table("run_artifacts")
