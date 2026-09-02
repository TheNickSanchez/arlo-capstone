"""`jamf_ops_agent` AgentDefinition (SAD §2 AD-16).

Fleet executor for the Apple / Jamf path. Tool bindings are the granular
PRD §3.4 “apply approved scripts” writes: upload, attach to Policy 1460,
and execute event `arlo_test`. Optional `jamf_apply_profile` only when that
action is on the frozen approval list.
"""

from __future__ import annotations

from claude_agent_sdk import AgentDefinition

from backend.app.domain.actions import jamf_ops_tool_names

JAMF_OPS_AGENT_ID = "jamf_ops_agent"

JAMF_OPS_PROMPT = (
    "You are `jamf_ops_agent`, ARLO's Jamf Fleet Executor (PRD `arlo-executor` on "
    "the Apple path). Apply exactly the frozen Jamf writes. Upload the persisted "
    "script with `jamf_upload_script`, attach it to Policy 1460 with "
    "`jamf_policy_set_script`, and run `jamf_execute_test_policy` (event "
    "`arlo_test`). Stop on the first failed or denied mutation. Do not call sudo "
    "or any shell — the MCP tool is the only execution path. Do not invent extra "
    "writes, devices, or policy ids."
)


def jamf_ops_definition(*, allowed_write_tools: list[str] | None = None) -> AgentDefinition:
    """Bind only the Jamf write tools this Activity is allowed to run.

    When `allowed_write_tools` is provided (Execution after HITL), the
    definition is the intersection with the specialist's catalog set so a
    frozen list cannot accidentally grant Jira/Intune tools to this agent.
    """
    catalog = set(jamf_ops_tool_names(include_apply_profile=True))
    if allowed_write_tools is None:
        tools = jamf_ops_tool_names(include_apply_profile=False)
    else:
        tools = sorted(catalog.intersection(allowed_write_tools))
    return AgentDefinition(
        description=(
            "Jamf fleet executor for approved script upload, Policy 1460 bind, "
            "and arlo_test."
        ),
        prompt=JAMF_OPS_PROMPT,
        tools=tools,
        model="inherit",
    )
