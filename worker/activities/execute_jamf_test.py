"""Activity `execute_jamf_test` — `jamf_ops_agent` Policy 1460 loop (SAD AD-18).

Deterministic MCP sequence (upload → bind Policy 1460 → execute event
`arlo_test`). The `jamf_ops_agent` tool list is the authorization surface;
this Activity calls those same tools via `raw_client` so the test-loop is
replay-safe and does not depend on model tool-selection. Claude filesystem
/ shell stay disabled.
"""

from __future__ import annotations

from temporalio import activity

from backend.app.config import settings
from backend.app.db.session import session_scope
from backend.app.domain.actions import McpSystem, jamf_ops_tool_names, write_tool_names_for_frozen_actions
from backend.app.domain.status import InstanceStatus
from backend.app.domain.workflow_contracts import ExecuteJamfTestInput
from backend.app.services.artifacts import latest_artifacts, persist_artifact
from worker.agents import JAMF_OPS_AGENT_ID
from worker.mcp.raw_client import McpToolCallError, call_tool


def _script_from_proposal_or_input(input: ExecuteJamfTestInput, latest_script: dict | None) -> tuple[str, str, str]:
    if input.script_contents:
        return input.script_contents, input.script_filename, input.script_os
    if latest_script:
        meta = latest_script.get("metadata_json") or {}
        contents = latest_script.get("content_text") or ""
        filename = str(meta.get("filename") or input.script_filename)
        os_name = str(meta.get("platform") or input.script_os)
        return contents, filename, os_name
    return "", input.script_filename, input.script_os


@activity.defn(name="execute_jamf_test")
async def execute_jamf_test(input: ExecuteJamfTestInput) -> dict:
    activity.logger.info(
        "execute_jamf_test start arlo_id=%s attempt=%s policy=%s event=%s",
        input.arlo_id,
        input.attempt,
        input.policy_id,
        input.event,
    )
    frozen = list(input.proposal.get("write_actions") or [])
    allowed = write_tool_names_for_frozen_actions(frozen)
    required = set(jamf_ops_tool_names(include_apply_profile=False))
    if not required.issubset(allowed):
        # Proposal must enumerate the three Jamf test verbs (SAD AD-18 HITL).
        missing = sorted(required - allowed)
        return {
            "ok": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": f"jamf test tools not on frozen list: {missing}",
            "attempt": input.attempt,
            "halted": True,
        }

    async with session_scope() as session:
        latest = await latest_artifacts(session, input.arlo_id)
    latest_script = (
        latest.generated_script.model_dump(mode="json") if latest.generated_script is not None else None
    )
    contents, filename, os_name = _script_from_proposal_or_input(input, latest_script)
    script_artifact_id = (
        str(latest.generated_script.id) if latest.generated_script is not None else None
    )

    policy_id = input.policy_id or settings.jamf_test_policy_id
    event = input.event or settings.jamf_test_event

    try:
        uploaded = await call_tool(
            McpSystem.JAMF,
            "jamf_upload_script",
            {"name": filename, "contents": contents, "os": os_name},
        )
        script_id = str(uploaded.get("script_id") or "")
        await call_tool(
            McpSystem.JAMF,
            "jamf_policy_set_script",
            {"policy_id": policy_id, "script_id": script_id},
        )
        result = await call_tool(
            McpSystem.JAMF,
            "jamf_execute_test_policy",
            {"policy_id": policy_id, "event": event},
        )
    except McpToolCallError as exc:
        result = {
            "ok": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": str(exc),
            "policy_id": policy_id,
            "event": event,
            "command": f"sudo jamf policy -event {event}",
        }

    exit_code = int(result.get("exit_code", 1))
    stdout = str(result.get("stdout") or "")
    stderr = str(result.get("stderr") or "")
    payload = {
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "policy_id": result.get("policy_id", policy_id),
        "event": result.get("event", event),
        "command": result.get("command", f"sudo jamf policy -event {event}"),
        "script_id": result.get("script_id"),
        "ok": exit_code == 0,
        "script_artifact_id": script_artifact_id,
        "attempt": input.attempt,
    }

    artifact_id = ""
    async with session_scope() as session:
        row = await persist_artifact(
            session,
            arlo_id=input.arlo_id,
            artifact_type="test_execution_log",
            created_by_agent=JAMF_OPS_AGENT_ID,
            phase=InstanceStatus.EXECUTING.value,
            attempt=input.attempt,
            content_text=f"stdout:\n{stdout}\n\nstderr:\n{stderr}",
            content_json=payload,
            metadata_json={
                "exit_code": exit_code,
                "policy_id": payload["policy_id"],
                "event": payload["event"],
                "script_artifact_id": script_artifact_id,
            },
        )
        artifact_id = str(row.id)

    return {**payload, "artifact_id": artifact_id, "jamf_ops_tools": sorted(required)}
