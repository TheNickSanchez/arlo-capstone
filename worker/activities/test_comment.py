"""Smoke-test Activity — build/demo pipeline verification only, **not** part of
the production remediation lifecycle (see `project-context/2.build/backend.md`
Assumptions for the operator-authorized exception this represents).

Posts one fixed diagnostic comment to the instance's own Jira ticket via
`worker.mcp.raw_client` — a direct, deterministic MCP call outside any
`ClaudeSDKClient` session, so it never goes through `allowed_tools` or the
`PreToolUse` PEP and is not gated by HITL approval. This intentionally
bypasses the "no write before HITL" guardrail (PRD §4.1) for exactly one
purpose: proving `API -> Temporal -> Worker -> MCP -> DB` wiring end-to-end
before any real remediation writes exist. It is disabled by setting
`ARLO_SMOKE_TEST_ENABLED=false`, and the Workflow only calls it when the API
told it to at start time (`RemediationWorkflowInput.smoke_test_enabled`).
"""

from __future__ import annotations

from temporalio import activity

from backend.app.db.session import session_scope
from backend.app.domain.actions import McpSystem
from backend.app.domain.status import InstanceStatus
from backend.app.domain.workflow_contracts import RemediationWorkflowInput
from backend.app.services.audit import append_audit_event
from worker.mcp.raw_client import McpToolCallError, call_tool

COMMENT_TEMPLATE = "[Arlo] Backend pipeline connected. Instance {arlo_id} initialized."


@activity.defn(name="post_smoke_test_comment")
async def post_smoke_test_comment(input: RemediationWorkflowInput) -> dict:
    activity.logger.info("smoke test comment start arlo_id=%s", input.arlo_id)
    body = COMMENT_TEMPLATE.format(arlo_id=input.arlo_id)

    if input.ticket_system != "jira":
        summary = f"smoke test skipped: ticket_system={input.ticket_system!r} (Jira MCP client only)"
        result: dict = {"ok": False, "reason": summary}
    else:
        try:
            call_result = await call_tool(
                McpSystem.JIRA, "jira_post_comment", {"ticket_key": input.ticket_key, "body": body}
            )
            summary = f"smoke test comment posted to {input.ticket_key}"
            result = {"ok": True, **call_result}
        except McpToolCallError as exc:
            summary = f"smoke test comment failed: {exc}"
            result = {"ok": False, "reason": str(exc)}

    async with session_scope() as session:
        await append_audit_event(
            session,
            arlo_id=input.arlo_id,
            phase=InstanceStatus.INVESTIGATING.value,
            kind="smoke_test",
            summary=summary,
            payload_json=result,
            mcp_system=McpSystem.JIRA.value,
            action="jira_post_comment",
            result="success" if result.get("ok") else "error",
        )

    return result
