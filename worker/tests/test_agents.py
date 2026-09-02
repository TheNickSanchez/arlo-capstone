"""Subagent specialist tool segregation (SAD §2 AD-16)."""

from __future__ import annotations

from backend.app.domain.actions import ActionKind, lookup_by_qualified_tool
from worker.agents import (
    DISCOVERY_AGENT_ID,
    JAMF_OPS_AGENT_ID,
    SCRIPT_WRITER_AGENT_ID,
    specialist_agents,
)
from worker.agents.discovery import discovery_definition
from worker.agents.jamf_ops import jamf_ops_definition
from worker.agents.script_writer import script_writer_definition


def test_discovery_agent_tools_are_reads_only() -> None:
    definition = discovery_definition()
    assert definition.tools
    for name in definition.tools:
        spec = lookup_by_qualified_tool(name)
        assert spec is not None
        assert spec.kind is ActionKind.READ
        assert "upload" not in name
        assert "execute_test" not in name
        assert "post_comment" not in name


def test_script_writer_has_no_mcp_tools() -> None:
    assert script_writer_definition().tools == []


def test_jamf_ops_tools_are_jamf_writes_only() -> None:
    writes = [
        "mcp__jamf__jamf_upload_script",
        "mcp__jamf__jamf_policy_set_script",
        "mcp__jamf__jamf_execute_test_policy",
        "mcp__jira__jira_post_comment",
    ]
    definition = jamf_ops_definition(allowed_write_tools=writes)
    assert set(definition.tools) == {
        "mcp__jamf__jamf_upload_script",
        "mcp__jamf__jamf_policy_set_script",
        "mcp__jamf__jamf_execute_test_policy",
    }


def test_specialist_map_omits_jamf_ops_until_writes() -> None:
    investigating = specialist_agents()
    assert DISCOVERY_AGENT_ID in investigating
    assert SCRIPT_WRITER_AGENT_ID in investigating
    assert JAMF_OPS_AGENT_ID not in investigating
    executing = specialist_agents(writes=["mcp__jamf__jamf_upload_script"])
    assert JAMF_OPS_AGENT_ID in executing
