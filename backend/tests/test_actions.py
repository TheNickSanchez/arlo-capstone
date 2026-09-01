"""Authorized-action catalog (PRD §3.4)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.domain.actions import (
    ActionKind,
    Phase,
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


def test_spawn_rejects_blank_ticket_id() -> None:
    with pytest.raises(ValidationError):
        InstanceCreateRequest(ticket_system="jira", ticket_id="   ")
