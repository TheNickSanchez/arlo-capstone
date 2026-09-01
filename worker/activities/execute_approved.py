"""Activity `execute_approved` (SAD §2 step 7). Reachable only after a Signal
+ matching `approvals` row (the Workflow only schedules this Activity when
`decision.action == "approve"` and `proposal_hash` matches).

New Claude session; `allowed_tools` = the frozen approved write list. The
`PreToolUse` PEP (`worker.pep`) is the actual enforcement point — this
Activity's job is to construct that policy correctly, not to trust the model.
Default: halt remaining writes on first failure (tracked via `PostToolUse`).
"""

from __future__ import annotations

import json

from temporalio import activity

from backend.app.config import settings
from backend.app.db.session import session_scope
from backend.app.domain.actions import McpSystem, write_tool_names_for_frozen_actions
from backend.app.domain.status import InstanceStatus
from backend.app.domain.workflow_contracts import ExecuteApprovedInput
from backend.app.schemas.proposal import ProposalPayload
from backend.app.services.audit import append_audit_event
from worker.activities.common import run_claude_query
from worker.mcp.agents import coordinator_agents
from worker.mcp.claude_client import build_claude_options
from worker.mcp.registry import build_mcp_servers
from worker.pep import build_hooks

_EXECUTOR_SYSTEM_PROMPT = """You are `arlo-executor`, ARLO's approved-plan executor (PRD \
FR-P0-06). Apply exactly the enumerated `write_actions` from the approved proposal below using \
your available write tools — nothing more, nothing that was not explicitly authorized. If a \
write tool call fails or is denied, stop attempting further writes and report what happened; do \
not retry around a denial. When you have applied every write you can, summarize what was \
attempted and the outcome of each."""


@activity.defn(name="execute_approved")
async def execute_approved(input: ExecuteApprovedInput) -> dict:
    activity.logger.info("execute_approved start arlo_id=%s", input.arlo_id)
    proposal = ProposalPayload.model_validate(input.proposal)
    frozen_actions = [action.model_dump() for action in proposal.write_actions]
    allowed_write_tools = write_tool_names_for_frozen_actions(frozen_actions)

    if not allowed_write_tools:
        async with session_scope() as session:
            await append_audit_event(
                session,
                arlo_id=input.arlo_id,
                phase=InstanceStatus.EXECUTING.value,
                kind="execution",
                summary="approved proposal enumerated no writes; nothing to execute",
            )
        return {"attempted": [], "halted": False, "summary": "no writes enumerated"}

    systems = sorted({McpSystem(action.system) for action in proposal.write_actions}, key=lambda s: s.value)
    execution_log: list[dict] = []
    state = {"halted": False}

    def _on_result(tool_name: str, response: dict) -> None:
        execution_log.append({"tool": tool_name, "response": response})
        if isinstance(response, dict) and response.get("ok") is False:
            state["halted"] = True

    options = build_claude_options(
        system_prompt=_EXECUTOR_SYSTEM_PROMPT,
        allowed_tools=sorted(allowed_write_tools),
        agents=coordinator_agents(writes=sorted(allowed_write_tools)),
        mcp_servers=build_mcp_servers(systems),
        hooks=build_hooks(
            arlo_id=input.arlo_id,
            activity_phase=InstanceStatus.EXECUTING.value,
            read_phase=None,
            writes_enabled=True,
            allowed_write_tools=frozenset(allowed_write_tools),
            is_halted=lambda: state["halted"],
            on_result=_on_result,
        ),
        max_turns=settings.execution_max_turns,
    )
    prompt = (
        f"Approved write_actions for ticket {input.ticket_key}:\n"
        f"{json.dumps([a.model_dump() for a in proposal.write_actions], indent=2)}\n\n"
        f"Findings/context from the proposal: {json.dumps(proposal.findings)}\n"
        "Apply these writes now using your available tools."
    )

    result = await run_claude_query(prompt=prompt, options=options)

    async with session_scope() as session:
        await append_audit_event(
            session,
            arlo_id=input.arlo_id,
            phase=InstanceStatus.EXECUTING.value,
            kind="execution",
            summary=f"execution complete; {len(execution_log)} write tool call(s); halted={state['halted']}",
            payload_json={"attempted": execution_log},
        )

    return {"attempted": execution_log, "halted": state["halted"], "summary": result.result}
