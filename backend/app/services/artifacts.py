"""Append-only run artifact persistence (SAD §4 AD-17)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.errors import NotFoundError, ValidationError
from backend.app.models.run_artifact import ARTIFACT_TYPES, RunArtifact
from backend.app.schemas.artifact import ArtifactOut, LatestArtifacts
from backend.app.services.audit import append_audit_event


def _to_out(row: RunArtifact) -> ArtifactOut:
    return ArtifactOut(
        id=row.id,
        arlo_id=row.arlo_id,
        artifact_type=row.artifact_type,  # type: ignore[arg-type]
        attempt=row.attempt,
        content_text=row.content_text,
        content_json=row.content_json,
        metadata_json=row.metadata_json,
        created_by_agent=row.created_by_agent,
        created_at=row.created_at,
    )


async def persist_artifact(
    session: AsyncSession,
    *,
    arlo_id: str,
    artifact_type: str,
    created_by_agent: str,
    phase: str,
    attempt: int = 0,
    content_text: str | None = None,
    content_json: dict[str, Any] | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> RunArtifact:
    if artifact_type not in ARTIFACT_TYPES:
        raise ValidationError(f"unknown artifact_type: {artifact_type}")
    row = RunArtifact(
        arlo_id=arlo_id,
        artifact_type=artifact_type,
        attempt=attempt,
        content_text=content_text,
        content_json=content_json,
        metadata_json=metadata_json,
        created_by_agent=created_by_agent,
    )
    session.add(row)
    await session.flush()
    await append_audit_event(
        session,
        arlo_id=arlo_id,
        phase=phase,
        kind="artifact_persist",
        summary=f"persisted {artifact_type} attempt={attempt} by {created_by_agent}",
        payload_json={"artifact_id": str(row.id), "artifact_type": artifact_type, "attempt": attempt},
    )
    return row


async def list_artifacts(
    session: AsyncSession,
    arlo_id: str,
    *,
    artifact_type: str | None = None,
) -> list[RunArtifact]:
    query = select(RunArtifact).where(RunArtifact.arlo_id == arlo_id)
    if artifact_type is not None:
        if artifact_type not in ARTIFACT_TYPES:
            raise ValidationError(f"unknown artifact_type: {artifact_type}")
        query = query.where(RunArtifact.artifact_type == artifact_type)
    rows = (
        await session.execute(query.order_by(RunArtifact.created_at.desc(), RunArtifact.attempt.desc()))
    ).scalars().all()
    return list(rows)


async def get_artifact(session: AsyncSession, arlo_id: str, artifact_id: uuid.UUID) -> RunArtifact:
    row = await session.get(RunArtifact, artifact_id)
    if row is None or row.arlo_id != arlo_id:
        raise NotFoundError(f"unknown artifact {artifact_id}", arlo_id=arlo_id)
    return row


async def latest_artifacts(session: AsyncSession, arlo_id: str) -> LatestArtifacts:
    latest: dict[str, RunArtifact] = {}
    for row in await list_artifacts(session, arlo_id):
        latest.setdefault(row.artifact_type, row)
    return LatestArtifacts(
        discovery_pack=_to_out(latest["discovery_pack"]) if "discovery_pack" in latest else None,
        generated_script=_to_out(latest["generated_script"]) if "generated_script" in latest else None,
        test_execution_log=(
            _to_out(latest["test_execution_log"]) if "test_execution_log" in latest else None
        ),
    )


def artifact_out(row: RunArtifact) -> ArtifactOut:
    return _to_out(row)
