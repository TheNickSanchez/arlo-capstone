"""`discovery_agent` AgentDefinition (SAD §2 AD-16).

Read-only investigator. Bindings are Jira, ServiceNow, Jamf, Intune, and
`kb_search` — never a write tool.
"""

from __future__ import annotations

from claude_agent_sdk import AgentDefinition

from backend.app.domain.actions import Phase, read_tool_names

DISCOVERY_AGENT_ID = "discovery_agent"

DISCOVERY_PROMPT = (
    "You are `discovery_agent`, ARLO's Read-Only Investigator (PRD `arlo-investigator`). "
    "Assemble ticket, asset, device compliance/log, and official runbook context "
    "without mutating anything. Ground every claim in a tool result. Never invent "
    "device, asset, or ticket state. If a system is unreachable, record an evidence "
    "gap instead of guessing."
)


def discovery_tool_names() -> list[str]:
    """Qualified read-only MCP tools for Investigation (SAD §2 segregation)."""
    return read_tool_names(Phase.INVESTIGATION)


def discovery_definition() -> AgentDefinition:
    return AgentDefinition(
        description="Read-only investigator for ticket, asset, MDM, and SOP context.",
        prompt=DISCOVERY_PROMPT,
        tools=discovery_tool_names(),
        model="inherit",
    )
