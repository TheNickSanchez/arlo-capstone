"""Authorized-action catalog (PRD §3.4)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.domain.actions import (
    ActionKind,
    Phase,
    has_jamf_test_actions,
    jamf_ops_tool_names,
    lookup,
    qualified_tool_name,
    read_tool_names,
    write_tool_names_for_frozen_actions,
)
from backend.app.schemas.instance import InstanceCreateRequest


def test_kb_search_is_read_only_investigation() -> None:
    spec = lookup("kb", "kb_search")
    assert spec is not None
    assert spec.kind is ActionKind.READ
    assert Phase.INVESTIGATION in spec.phases
    assert Phase.EXECUTION not in spec.phases


def test_write_tools_absent_from_investigation_allowed_list() -> None:
    names = read_tool_names(Phase.INVESTIGATION)
    assert all("post_comment" not in n and "apply_" not in n for n in names)
    assert any(n.endswith("kb_search") for n in names)


def test_frozen_list_maps_to_qualified_mcp_tools() -> None:
    tools = write_tool_names_for_frozen_actions(
        [{"system": "jira", "action_type": "post_summary", "target_ids": ["JIRA-102"]}]
    )
    spec = lookup("jira", "post_summary")
    assert spec is not None
    assert qualified_tool_name(spec) in tools


def test_jamf_test_tools_are_execution_writes_not_investigation_reads() -> None:
    for action_type in ("upload_script", "policy_set_script", "execute_test_policy"):
        spec = lookup("jamf", action_type)
        assert spec is not None
        assert spec.kind is ActionKind.WRITE
        assert Phase.EXECUTION in spec.phases
        assert Phase.INVESTIGATION not in spec.phases
        assert qualified_tool_name(spec) not in read_tool_names(Phase.INVESTIGATION)


def test_jamf_ops_tool_names_are_segregated() -> None:
    names = jamf_ops_tool_names()
    assert all(n.startswith("mcp__jamf__") for n in names)
    assert "mcp__jamf__jamf_upload_script" in names
    assert "mcp__jamf__jamf_policy_set_script" in names
    assert "mcp__jamf__jamf_execute_test_policy" in names
    assert all("jira" not in n and "intune" not in n for n in names)


def test_has_jamf_test_actions() -> None:
    assert has_jamf_test_actions(
        [{"system": "jamf", "action_type": "upload_script", "target_ids": ["1460"]}]
    )
    assert not has_jamf_test_actions(
        [{"system": "jira", "action_type": "post_summary", "target_ids": ["CPE-1"]}]
    )


def test_spawn_rejects_blank_ticket_id() -> None:
    with pytest.raises(ValidationError):
        InstanceCreateRequest(ticket_system="jira", ticket_id="   ")
