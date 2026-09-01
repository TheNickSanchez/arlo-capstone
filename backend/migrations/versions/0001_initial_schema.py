"""Initial ARLO schema (SAD §4): users, instances, approvals, audit_events,
learned_patterns, kb_articles; `pgvector` extension; `arlo_instance_seq`.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # PRD example instance ids (ARLO-673..676) are seed/demo history only;
    # the sequence for real spawns starts where that narrative leaves off.
    op.execute("CREATE SEQUENCE IF NOT EXISTS arlo_instance_seq START WITH 675 INCREMENT BY 1")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("idp_subject", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "instances",
        sa.Column("arlo_id", sa.String(), primary_key=True),
        sa.Column("ticket_system", sa.String(), nullable=False),
        sa.Column("ticket_key", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("proposal_json", postgresql.JSONB(), nullable=True),
        sa.Column("proposal_hash", sa.String(), nullable=True),
        sa.Column("workflow_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.CheckConstraint("ticket_system IN ('jira', 'servicenow')", name="instances_ticket_system_check"),
    )
    op.create_index(
        "instances_active_ticket_uidx",
        "instances",
        ["ticket_system", "ticket_key"],
        unique=True,
        postgresql_where=sa.text("status NOT IN ('Done', 'Rejected', 'Failed', 'Cancelled')"),
    )

    op.create_table(
        "approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("arlo_id", sa.String(), sa.ForeignKey("instances.arlo_id"), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("proposal_hash", sa.String(), nullable=True),
        sa.Column("frozen_actions_json", postgresql.JSONB(), nullable=True),
        sa.Column("rationale", sa.String(), nullable=True),
        sa.CheckConstraint("action IN ('approve', 'reject', 'cancel')", name="approvals_action_check"),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("arlo_id", sa.String(), sa.ForeignKey("instances.arlo_id"), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("phase", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("mcp_system", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=True),
        sa.Column("result", sa.String(), nullable=True),
        sa.Column("policy_deny", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("audit_events_arlo_at_idx", "audit_events", ["arlo_id", "at"])

    op.create_table(
        "learned_patterns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("app_name", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("pattern_type", sa.String(), nullable=False),
        sa.Column("problem_description", sa.String(), nullable=False),
        sa.Column("problem_description_hash", sa.String(), nullable=False),
        sa.Column("solution_payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_by_arlo_id", sa.String(), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("learned_patterns_app_name_idx", "learned_patterns", ["app_name"])
    op.create_index("learned_patterns_platform_idx", "learned_patterns", ["platform"])
    op.create_index(
        "learned_patterns_natural_key_idx",
        "learned_patterns",
        ["app_name", "platform", "pattern_type"],
    )

    op.create_table(
        "kb_articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("kb_articles_category_idx", "kb_articles", ["category"])
    # ivfflat requires ANALYZE / a populated table to pick well-sized lists; safe on empty tables
    # in MVP because Build seeds a handful of fixture rows immediately after migration.
    op.execute(
        "CREATE INDEX IF NOT EXISTS kb_articles_embedding_ivfflat_idx "
        "ON kb_articles USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.drop_index("kb_articles_embedding_ivfflat_idx", table_name="kb_articles")
    op.drop_index("kb_articles_category_idx", table_name="kb_articles")
    op.drop_table("kb_articles")

    op.drop_index("learned_patterns_natural_key_idx", table_name="learned_patterns")
    op.drop_index("learned_patterns_platform_idx", table_name="learned_patterns")
    op.drop_index("learned_patterns_app_name_idx", table_name="learned_patterns")
    op.drop_table("learned_patterns")

    op.drop_index("audit_events_arlo_at_idx", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_table("approvals")

    op.drop_index("instances_active_ticket_uidx", table_name="instances")
    op.drop_table("instances")

    op.drop_table("users")

    op.execute("DROP SEQUENCE IF EXISTS arlo_instance_seq")
