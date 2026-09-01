"""Activity `mark_failed` — Workflow-triggered terminal-failure bookkeeping.

Workflow code cannot touch PostgreSQL directly (SAD §2: "no LLM, MCP, or DB
drivers"), so when `ArloRemediationWorkflow` catches an unrecoverable
`ActivityError` from `investigate` / `generate_proposal` / `execute_approved`
/ `validate_and_close`, it schedules this tiny Activity to persist the
`Failed` transition and a Diagnostic audit entry before returning.
"""

from __future__ import annotations

from temporalio import activity

from backend.app.db.session import session_scope
from backend.app.domain.status import InstanceStatus, is_terminal
from backend.app.domain.workflow_contracts import MarkFailedInput
from backend.app.models.instance import Instance
from backend.app.services.audit import append_audit_event
from worker.activities.common import transition_status


@activity.defn(name="mark_failed")
async def mark_failed(input: MarkFailedInput) -> None:
    activity.logger.warning("mark_failed arlo_id=%s phase=%s reason=%s", input.arlo_id, input.phase, input.reason)
    async with session_scope() as session:
        instance = await session.get(Instance, input.arlo_id)
        if instance is None:
            return
        if not is_terminal(InstanceStatus(instance.status)):
            await transition_status(session, instance, InstanceStatus.FAILED)
        await append_audit_event(
            session,
            arlo_id=input.arlo_id,
            phase=InstanceStatus.FAILED.value,
            kind="diagnostic",
            summary=f"workflow halted in {input.phase}: {input.reason}",
            result="error",
        )
