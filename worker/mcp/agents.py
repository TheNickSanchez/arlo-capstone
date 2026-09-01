"""Claude Agent SDK `AgentDefinition` entries (SAD §2 Multi-Agent System).

The Activity's main runtime agent is the coordinator (`arlo`). Specialists are
declared here so the Agent tool can invoke them with a stricter or equal tool
policy. Delegation must not bypass HITL — write tools stay off investigator
definitions and on executor definitions only after the frozen list is applied.
"""

from __future__ import annotations

from claude_agent_sdk import AgentDefinition

from backend.app.domain.actions import Phase, read_tool_names


def investigator_definition() -> AgentDefinition:
    return AgentDefinition(
        description="Read-only evidence gatherer for ticket, asset, MDM, and SOP context.",
        prompt=(
            "You are `arlo-investigator`. Assemble ticket, asset, device compliance/log, "
            "and official runbook context without mutating anything. Ground every claim in "
            "a tool result. Never invent device, asset, or ticket state."
        ),
        tools=read_tool_names(Phase.INVESTIGATION),
        model="inherit",
    )


def executor_definition(*, allowed_write_tools: list[str]) -> AgentDefinition:
    return AgentDefinition(
        description="Approved-plan executor. Apply the frozen action list exactly.",
        prompt=(
            "You are `arlo-executor`. Apply exactly the enumerated write_actions from the "
            "approved proposal using your available write tools. Stop on the first failed "
            "or denied mutation. Do not invent extra writes."
        ),
        tools=list(allowed_write_tools),
        model="inherit",
    )


def coordinator_agents(*, writes: list[str] | None = None) -> dict[str, AgentDefinition]:
    agents: dict[str, AgentDefinition] = {"arlo-investigator": investigator_definition()}
    if writes:
        agents["arlo-executor"] = executor_definition(allowed_write_tools=writes)
    return agents
