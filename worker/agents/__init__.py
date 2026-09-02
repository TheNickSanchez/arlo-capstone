"""Claude Agent SDK specialists (SAD §2 Subagent Specialist Topology).

Keys in `ClaudeAgentOptions.agents` must match the agent ids exported here.
"""

from __future__ import annotations

from claude_agent_sdk import AgentDefinition

from worker.agents.discovery import DISCOVERY_AGENT_ID, discovery_definition
from worker.agents.jamf_ops import JAMF_OPS_AGENT_ID, jamf_ops_definition
from worker.agents.orchestrator import ORCHESTRATOR_ID, orchestrator_definition
from worker.agents.script_writer import SCRIPT_WRITER_AGENT_ID, script_writer_definition


def specialist_agents(*, writes: list[str] | None = None) -> dict[str, AgentDefinition]:
    """Phase-appropriate `AgentDefinition` map for `ClaudeAgentOptions.agents`.

    `jamf_ops_agent` is included only when `writes` is a non-empty list so
    Investigation/Proposal sessions cannot even name the fleet executor.
    """
    agents: dict[str, AgentDefinition] = {
        ORCHESTRATOR_ID: orchestrator_definition(),
        DISCOVERY_AGENT_ID: discovery_definition(),
        SCRIPT_WRITER_AGENT_ID: script_writer_definition(),
    }
    if writes:
        agents[JAMF_OPS_AGENT_ID] = jamf_ops_definition(allowed_write_tools=writes)
    return agents


__all__ = [
    "DISCOVERY_AGENT_ID",
    "JAMF_OPS_AGENT_ID",
    "ORCHESTRATOR_ID",
    "SCRIPT_WRITER_AGENT_ID",
    "discovery_definition",
    "jamf_ops_definition",
    "orchestrator_definition",
    "script_writer_definition",
    "specialist_agents",
]
