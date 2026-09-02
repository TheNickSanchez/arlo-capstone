"""Instances API (SAD §4).

POST   /api/v1/instances
GET    /api/v1/instances
GET    /api/v1/instances/{arlo_id}
GET    /api/v1/instances/{arlo_id}/artifacts
GET    /api/v1/instances/{arlo_id}/artifacts/{artifact_id}
GET    /api/v1/instances/{arlo_id}/audit
POST   /api/v1/instances/{arlo_id}/approve
POST   /api/v1/instances/{arlo_id}/reject
POST   /api/v1/instances/{arlo_id}/cancel
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_session
from backend.app.schemas.artifact import ArtifactListResponse, ArtifactOut
from backend.app.schemas.instance import (
    ApproveRequest,
    AuditEventOut,
    AuditListResponse,
    CancelRequest,
    DecisionResponse,
    InstanceCreateRequest,
    InstanceCreateResponse,
    InstanceDetail,
    InstanceListResponse,
    RejectRequest,
)
from backend.app.security.dependencies import CurrentUser, get_current_user
from backend.app.services import artifacts as artifacts_service
from backend.app.services import instances as instances_service

router = APIRouter(tags=["instances"])


@router.post("/instances", response_model=InstanceCreateResponse, status_code=201)
async def create_instance(
    body: InstanceCreateRequest,
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> InstanceCreateResponse:
    instance = await instances_service.create_instance(
        session,
        ticket_system=body.ticket_system,
        ticket_key=body.ticket_id,
        created_by=uuid.UUID(user.user_id),
    )
    return InstanceCreateResponse(arlo_id=instance.arlo_id, status=instance.status)


@router.get("/instances", response_model=InstanceListResponse)
async def list_instances(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> InstanceListResponse:
    items, total = await instances_service.list_instances(
        session, status=status, limit=limit, offset=offset
    )
    return InstanceListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/instances/{arlo_id}", response_model=InstanceDetail)
async def get_instance(
    arlo_id: str,
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> InstanceDetail:
    return await instances_service.get_instance_detail(session, arlo_id)


@router.get("/instances/{arlo_id}/artifacts", response_model=ArtifactListResponse)
async def list_artifacts(
    arlo_id: str,
    type: str | None = Query(default=None, alias="type"),
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ArtifactListResponse:
    await instances_service.get_instance_or_404(session, arlo_id)
    rows = await artifacts_service.list_artifacts(session, arlo_id, artifact_type=type)
    items = [artifacts_service.artifact_out(row) for row in rows]
    return ArtifactListResponse(items=items, total=len(items))


@router.get("/instances/{arlo_id}/artifacts/{artifact_id}", response_model=ArtifactOut)
async def get_artifact(
    arlo_id: str,
    artifact_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ArtifactOut:
    await instances_service.get_instance_or_404(session, arlo_id)
    row = await artifacts_service.get_artifact(session, arlo_id, artifact_id)
    return artifacts_service.artifact_out(row)


@router.get("/instances/{arlo_id}/audit", response_model=AuditListResponse)
async def get_audit(
    arlo_id: str,
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> AuditListResponse:
    events = await instances_service.list_audit_events(session, arlo_id)
    return AuditListResponse(
        items=[
            AuditEventOut(
                at=event.at,
                arlo_id=event.arlo_id,
                phase=event.phase,
                kind=event.kind,
                summary=event.summary,
                mcp_system=event.mcp_system,
                action=event.action,
                result=event.result,
                policy_deny=event.policy_deny,
            )
            for event in events
        ]
    )


@router.post("/instances/{arlo_id}/approve", response_model=DecisionResponse)
async def approve(
    arlo_id: str,
    body: ApproveRequest,
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> DecisionResponse:
    instance = await instances_service.approve_instance(
        session,
        arlo_id=arlo_id,
        actor_id=uuid.UUID(user.user_id),
        proposal_hash=body.proposal_hash,
        rationale=body.rationale,
    )
    return DecisionResponse(arlo_id=instance.arlo_id, status=instance.status)


@router.post("/instances/{arlo_id}/reject", response_model=DecisionResponse)
async def reject(
    arlo_id: str,
    body: RejectRequest,
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> DecisionResponse:
    instance = await instances_service.reject_instance(
        session,
        arlo_id=arlo_id,
        actor_id=uuid.UUID(user.user_id),
        proposal_hash=body.proposal_hash,
        reason=body.reason,
    )
    return DecisionResponse(arlo_id=instance.arlo_id, status=instance.status)


@router.post("/instances/{arlo_id}/cancel", response_model=DecisionResponse)
async def cancel(
    arlo_id: str,
    body: CancelRequest,
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> DecisionResponse:
    instance = await instances_service.cancel_instance(
        session, arlo_id=arlo_id, actor_id=uuid.UUID(user.user_id), reason=body.reason
    )
    return DecisionResponse(arlo_id=instance.arlo_id, status=instance.status)
