"""Backward-compatible re-export of SAD §2 specialists.

Canonical definitions live in `worker/agents/`. Activities should import
`specialist_agents` from there; this module keeps the older
`coordinator_agents` name working.
"""

from __future__ import annotations

from claude_agent_sdk import AgentDefinition

from worker.agents import specialist_agents
from worker.agents.discovery import discovery_definition
from worker.agents.jamf_ops import jamf_ops_definition


def investigator_definition() -> AgentDefinition:
    return discovery_definition()


def executor_definition(*, allowed_write_tools: list[str]) -> AgentDefinition:
    return jamf_ops_definition(allowed_write_tools=allowed_write_tools)


def coordinator_agents(*, writes: list[str] | None = None) -> dict[str, AgentDefinition]:
    return specialist_agents(writes=writes)
