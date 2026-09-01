"""Append-only audit event writer (SAD §4). Never UPDATE/DELETE `audit_events`."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_event import AuditEvent


async def append_audit_event(
    session: AsyncSession,
    *,
    arlo_id: str,
    phase: str,
    kind: str,
    summary: str,
    payload_json: dict[str, Any] | None = None,
    mcp_system: str | None = None,
    action: str | None = None,
    result: str | None = None,
    policy_deny: bool = False,
) -> AuditEvent:
    event = AuditEvent(
        arlo_id=arlo_id,
        phase=phase,
        kind=kind,
        summary=summary,
        payload_json=payload_json,
        mcp_system=mcp_system,
        action=action,
        result=result,
        policy_deny=policy_deny,
    )
    session.add(event)
    await session.flush()
    return event
