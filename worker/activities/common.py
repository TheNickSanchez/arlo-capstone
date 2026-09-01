"""Shared plumbing for Activities (SAD §2). Not an Activity itself.

Keeps DB status transitions and audit writes here. ClaudeSDKClient sessions
are constructed in `worker.mcp.claude_client` so MCP + SDK lifecycle lives
in the MCP integration layer.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.exceptions import ApplicationError

from backend.app.domain.status import InstanceStatus, assert_transition_allowed
from backend.app.models.instance import Instance
from backend.app.services.audit import append_audit_event
from worker.mcp.claude_client import ClaudeQueryError, run_claude_session

logger = logging.getLogger("arlo.worker.activities")

# Re-export so existing Activity imports keep working.
run_claude_query = run_claude_session

__all__ = [
    "ClaudeQueryError",
    "non_retryable",
    "record_diagnostic",
    "run_claude_query",
    "run_claude_session",
    "transition_status",
]


async def transition_status(
    session: AsyncSession, instance: Instance, target: InstanceStatus
) -> None:
    """Assert the edge is legal (SAD §6 state machine) and persist it."""
    current = InstanceStatus(instance.status)
    assert_transition_allowed(current, target)
    instance.status = target.value
    await session.flush()


def non_retryable(message: str, *, arlo_id: str | None = None) -> ApplicationError:
    """An `ApplicationError` Temporal will not retry (SAD §2: "policy deny,
    unauthorized tool ... do not retry as success").
    """
    details = (arlo_id,) if arlo_id else ()
    return ApplicationError(message, *details, non_retryable=True)


async def record_diagnostic(
    session: AsyncSession,
    *,
    arlo_id: str,
    phase: str,
    summary: str,
    payload_json: dict | None = None,
) -> None:
    await append_audit_event(
        session,
        arlo_id=arlo_id,
        phase=phase,
        kind="diagnostic",
        summary=summary,
        payload_json=payload_json,
        result="error",
    )
