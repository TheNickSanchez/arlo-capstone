"""Instance lifecycle service (SAD §4 API Architecture; PRD §4.1).

Routers stay thin controllers; all persistence + Temporal orchestration logic
lives here so it is independently testable and reusable from
`scripts/test_pipeline.py` style tooling.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import temporal_client
from backend.app.db.sequences import next_arlo_id
from backend.app.domain.errors import ConflictError, NotFoundError, ValidationError
from backend.app.domain.ids import workflow_id_for
from backend.app.domain.status import InstanceStatus, assert_transition_allowed, is_terminal
from backend.app.domain.workflow_contracts import ApprovalDecision as WorkflowApprovalDecision
from backend.app.models.approval import Approval
from backend.app.models.audit_event import AuditEvent
from backend.app.models.instance import Instance
from backend.app.schemas.instance import ApprovalSummary, InstanceDetail, InstanceSummary
from backend.app.schemas.proposal import ProposalPayload
from backend.app.services.artifacts import latest_artifacts
from backend.app.services.audit import append_audit_event

_TERMINAL_STATUS_VALUES = [s.value for s in InstanceStatus if is_terminal(s)]


async def create_instance(
    session: AsyncSession,
    *,
    ticket_system: str,
    ticket_key: str,
    created_by: uuid.UUID | None,
) -> Instance:
    """Spawn a new instance (PRD FR-P0-01). Duplicate active mapping → 409 (SAD §4)."""
    existing = await session.execute(
        select(Instance).where(
            Instance.ticket_system == ticket_system,
            Instance.ticket_key == ticket_key,
            Instance.status.not_in(_TERMINAL_STATUS_VALUES),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError(
            f"an active instance is already mapped to {ticket_system}:{ticket_key}"
        )

    arlo_id = await next_arlo_id(session)
    workflow_id = workflow_id_for(arlo_id)

    instance = Instance(
        arlo_id=arlo_id,
        ticket_system=ticket_system,
        ticket_key=ticket_key,
        status=InstanceStatus.INVESTIGATING.value,
        workflow_id=workflow_id,
        created_by=created_by,
    )
    session.add(instance)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise ConflictError(
            f"an active instance is already mapped to {ticket_system}:{ticket_key}"
        ) from exc

    await append_audit_event(
        session,
        arlo_id=arlo_id,
        phase=InstanceStatus.INVESTIGATING.value,
        kind="spawn",
        summary=f"ARLO instance mapped to {ticket_system}:{ticket_key}",
    )

    try:
        await temporal_client.start_remediation_workflow(
            arlo_id=arlo_id, ticket_system=ticket_system, ticket_key=ticket_key
        )
    except Exception:
        # Roll the whole spawn back: no orphaned "Investigating" row without a
        # backing Workflow (SAD §4: Workflow is authority for execution state).
        await session.rollback()
        raise

    return instance


async def get_instance_or_404(session: AsyncSession, arlo_id: str) -> Instance:
    instance = await session.get(Instance, arlo_id)
    if instance is None:
        raise NotFoundError(f"unknown instance {arlo_id}", arlo_id=arlo_id)
    return instance


async def list_instances(
    session: AsyncSession,
    *,
    status: str | None,
    limit: int,
    offset: int,
) -> tuple[list[InstanceSummary], int]:
    if limit < 1 or limit > 200:
        raise ValidationError("limit must be between 1 and 200")
    if offset < 0:
        raise ValidationError("offset must be >= 0")
    if status is not None and status not in [s.value for s in InstanceStatus]:
        raise ValidationError(f"unknown status filter: {status}")

    base_query = select(Instance)
    count_query = select(func.count()).select_from(Instance)
    if status is not None:
        base_query = base_query.where(Instance.status == status)
        count_query = count_query.where(Instance.status == status)

    total = (await session.execute(count_query)).scalar_one()
    rows = (
        await session.execute(
            base_query.order_by(Instance.created_at.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()

    items = [
        InstanceSummary(
            arlo_id=row.arlo_id,
            ticket_system=row.ticket_system,
            ticket_key=row.ticket_key,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]
    return items, total


async def get_instance_detail(session: AsyncSession, arlo_id: str) -> InstanceDetail:
    instance = await get_instance_or_404(session, arlo_id)

    latest_approval_row = (
        await session.execute(
            select(Approval)
            .where(Approval.arlo_id == arlo_id)
            .order_by(Approval.at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    latest_approval = None
    if latest_approval_row is not None:
        latest_approval = ApprovalSummary(
            action=latest_approval_row.action,
            actor_id=str(latest_approval_row.actor_id),
            at=latest_approval_row.at,
            rationale=latest_approval_row.rationale,
        )

    proposal = ProposalPayload(**instance.proposal_json) if instance.proposal_json else None
    artifacts = await latest_artifacts(session, arlo_id)

    return InstanceDetail(
        arlo_id=instance.arlo_id,
        ticket_system=instance.ticket_system,
        ticket_key=instance.ticket_key,
        status=instance.status,
        created_at=instance.created_at,
        updated_at=instance.updated_at,
        proposal=proposal,
        proposal_hash=instance.proposal_hash,
        latest_approval=latest_approval,
        latest_artifacts=artifacts,
    )


async def list_audit_events(session: AsyncSession, arlo_id: str) -> list[AuditEvent]:
    await get_instance_or_404(session, arlo_id)
    rows = (
        await session.execute(
            select(AuditEvent).where(AuditEvent.arlo_id == arlo_id).order_by(AuditEvent.at.asc())
        )
    ).scalars().all()
    return list(rows)


async def _record_decision(
    session: AsyncSession,
    *,
    arlo_id: str,
    action: str,
    actor_id: uuid.UUID,
    new_status: InstanceStatus,
    proposal_hash: str | None,
    rationale: str | None,
    require_hash_match: bool,
) -> Instance:
    instance = await get_instance_or_404(session, arlo_id)
    current_status = InstanceStatus(instance.status)

    if is_terminal(current_status):
        raise ConflictError(
            f"instance {arlo_id} is already terminal ({current_status.value})", arlo_id=arlo_id
        )

    if require_hash_match:
        if current_status is not InstanceStatus.AWAITING_APPROVAL:
            raise ConflictError(
                f"instance {arlo_id} is not Awaiting Approval (status={current_status.value})",
                arlo_id=arlo_id,
            )
        if not instance.proposal_hash or instance.proposal_hash != proposal_hash:
            raise ConflictError(
                f"stale proposal_hash for {arlo_id}; re-fetch the instance detail",
                arlo_id=arlo_id,
            )

    assert_transition_allowed(current_status, new_status)

    frozen_actions = None
    if action == "approve":
        frozen_actions = (instance.proposal_json or {}).get("write_actions", [])

    approval = Approval(
        arlo_id=arlo_id,
        action=action,
        actor_id=actor_id,
        proposal_hash=proposal_hash,
        frozen_actions_json=frozen_actions,
        rationale=rationale,
    )
    session.add(approval)

    instance.status = new_status.value
    await session.flush()

    await append_audit_event(
        session,
        arlo_id=arlo_id,
        phase=new_status.value,
        kind="hitl_decision",
        summary=f"{action} recorded by actor {actor_id}",
        payload_json={"action": action, "rationale": rationale},
    )

    try:
        await temporal_client.signal_approval_decision(
            arlo_id=arlo_id,
            decision=WorkflowApprovalDecision(
                action=action,  # type: ignore[arg-type]
                actor_id=str(actor_id),
                at=datetime.now(UTC).isoformat(),
                proposal_hash=proposal_hash,
                rationale=rationale,
            ),
        )
    except Exception:
        await session.rollback()
        raise

    return instance


async def approve_instance(
    session: AsyncSession, *, arlo_id: str, actor_id: uuid.UUID, proposal_hash: str, rationale: str | None
) -> Instance:
    return await _record_decision(
        session,
        arlo_id=arlo_id,
        action="approve",
        actor_id=actor_id,
        new_status=InstanceStatus.EXECUTING,
        proposal_hash=proposal_hash,
        rationale=rationale,
        require_hash_match=True,
    )


async def reject_instance(
    session: AsyncSession, *, arlo_id: str, actor_id: uuid.UUID, proposal_hash: str, reason: str | None
) -> Instance:
    return await _record_decision(
        session,
        arlo_id=arlo_id,
        action="reject",
        actor_id=actor_id,
        new_status=InstanceStatus.REJECTED,
        proposal_hash=proposal_hash,
        rationale=reason,
        require_hash_match=True,
    )


async def cancel_instance(
    session: AsyncSession, *, arlo_id: str, actor_id: uuid.UUID, reason: str | None
) -> Instance:
    instance = await get_instance_or_404(session, arlo_id)
    current_status = InstanceStatus(instance.status)
    if is_terminal(current_status):
        raise ConflictError(
            f"instance {arlo_id} is already terminal ({current_status.value})", arlo_id=arlo_id
        )
    return await _record_decision(
        session,
        arlo_id=arlo_id,
        action="cancel",
        actor_id=actor_id,
        new_status=InstanceStatus.CANCELLED,
        proposal_hash=instance.proposal_hash,
        rationale=reason,
        require_hash_match=False,
    )
