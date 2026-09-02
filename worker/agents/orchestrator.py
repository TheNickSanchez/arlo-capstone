"""`arlo_orchestrator` AgentDefinition (SAD §2 AD-16).

Main runtime agent in each Activity. Owns phase, budgets, and specialist
dispatch. Has no vendor MCP tools — writes stay on `jamf_ops_agent` (after
HITL) or on the orchestrator's Activity-level `allowed_tools` for Intune /
Jira / ServiceNow frozen writes.
"""

from __future__ import annotations

from claude_agent_sdk import AgentDefinition

ORCHESTRATOR_ID = "arlo_orchestrator"

ORCHESTRATOR_PROMPT = (
    "You are `arlo_orchestrator`, ARLO's Enterprise IT & Endpoint Remediation "
    "Specialist (PRD §3.1). You own this instance's lifecycle: phase, turn/token "
    "budgets, audit narrative, and specialist dispatch. "
    "Dispatch `discovery_agent` for evidence, `script_writer_agent` for script "
    "draft or refactor, and `jamf_ops_agent` only after an approval record exists. "
    "Never invent device, asset, or ticket state. Never bypass HITL. Never grant a "
    "specialist extra tools. Do not run Policy 1460 yourself."
)


def orchestrator_definition() -> AgentDefinition:
    return AgentDefinition(
        description="Coordinator: phase owner, specialist dispatcher, HITL guardian.",
        prompt=ORCHESTRATOR_PROMPT,
        tools=[],
        model="inherit",
    )
