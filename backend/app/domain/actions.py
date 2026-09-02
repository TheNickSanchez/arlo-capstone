"""Authorized MCP action catalog (PRD §3.4; SAD §4, §6, §8).

Single source of truth binding a PRD-authorized logical action (`system` +
`action_type`) to: an MCP tool name, its read/write classification, and the
lifecycle phases where it may legally run. Both the API (proposal validation)
and the worker (`allowed_tools` construction, PEP enforcement) import this
module so the catalog cannot drift between the two processes.

Anything not listed here is out of scope (PRD §3.4 "Global MCP rules": deny by
default). `kb_search` is Investigation-only and is never a write.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ActionKind(StrEnum):
    READ = "read"
    WRITE = "write"


class Phase(StrEnum):
    INVESTIGATION = "investigation"
    PROPOSAL = "proposal"
    EXECUTION = "execution"
    VALIDATION = "validation"


class McpSystem(StrEnum):
    JIRA = "jira"
    SERVICENOW = "servicenow"
    JAMF = "jamf"
    INTUNE = "intune"
    KB = "kb"


@dataclass(frozen=True)
class ActionSpec:
    system: McpSystem
    action_type: str
    tool_name: str
    kind: ActionKind
    phases: frozenset[Phase]
    description: str


# PRD §3.4 tables, one row per authorized action. `tool_name` is the Build-time
# MCP tool binding (SAD: "PRD authorizes actions, not vendor SDK sprawl").
_CATALOG: tuple[ActionSpec, ...] = (
    ActionSpec(
        McpSystem.JIRA,
        "read_ticket",
        "jira_get_ticket",
        ActionKind.READ,
        frozenset({Phase.INVESTIGATION, Phase.VALIDATION}),
        "Title, description, comments, status, assignee, linked identifiers",
    ),
    ActionSpec(
        McpSystem.JIRA,
        "post_summary",
        "jira_post_comment",
        ActionKind.WRITE,
        frozenset({Phase.EXECUTION}),
        "Publish investigation/proposal summary onto the ticket",
    ),
    ActionSpec(
        McpSystem.JIRA,
        "transition_ticket",
        "jira_transition_ticket",
        ActionKind.WRITE,
        frozenset({Phase.EXECUTION}),
        "Move the ticket along the agreed workflow",
    ),
    ActionSpec(
        McpSystem.JIRA,
        "close_ticket",
        "jira_close_ticket",
        ActionKind.WRITE,
        frozenset({Phase.EXECUTION}),
        "Close when validation criteria in the approved plan are met",
    ),
    ActionSpec(
        McpSystem.SERVICENOW,
        "check_chg",
        "snow_check_chg",
        ActionKind.READ,
        frozenset({Phase.INVESTIGATION}),
        "Check for existing change requests",
    ),
    ActionSpec(
        McpSystem.SERVICENOW,
        "read_asset",
        "snow_read_asset",
        ActionKind.READ,
        frozenset({Phase.INVESTIGATION, Phase.VALIDATION}),
        "Read asset/CI data",
    ),
    ActionSpec(
        McpSystem.SERVICENOW,
        "create_chg",
        "snow_create_chg",
        ActionKind.WRITE,
        frozenset({Phase.EXECUTION}),
        "Create new change request for tracking",
    ),
    ActionSpec(
        McpSystem.JAMF,
        "read_compliance",
        "jamf_read_compliance",
        ActionKind.READ,
        frozenset({Phase.INVESTIGATION, Phase.VALIDATION}),
        "Read device compliance state",
    ),
    ActionSpec(
        McpSystem.JAMF,
        "fetch_logs",
        "jamf_fetch_logs",
        ActionKind.READ,
        frozenset({Phase.INVESTIGATION}),
        "Fetch device logs",
    ),
    ActionSpec(
        McpSystem.JAMF,
        "apply_profile_or_script",
        "jamf_apply_profile",
        ActionKind.WRITE,
        frozenset({Phase.EXECUTION}),
        "Apply approved configuration profile or script",
    ),
    ActionSpec(
        McpSystem.JAMF,
        "upload_script",
        "jamf_upload_script",
        ActionKind.WRITE,
        frozenset({Phase.EXECUTION}),
        "Upload approved script content to Jamf (PRD apply approved scripts)",
    ),
    ActionSpec(
        McpSystem.JAMF,
        "policy_set_script",
        "jamf_policy_set_script",
        ActionKind.WRITE,
        frozenset({Phase.EXECUTION}),
        "Attach an uploaded script to the isolated test policy (default 1460)",
    ),
    ActionSpec(
        McpSystem.JAMF,
        "execute_test_policy",
        "jamf_execute_test_policy",
        ActionKind.WRITE,
        frozenset({Phase.EXECUTION}),
        "Execute isolated test policy via event arlo_test (MCP wrap; no shell)",
    ),
    ActionSpec(
        McpSystem.INTUNE,
        "read_compliance",
        "intune_read_compliance",
        ActionKind.READ,
        frozenset({Phase.INVESTIGATION, Phase.VALIDATION}),
        "Read device compliance state",
    ),
    ActionSpec(
        McpSystem.INTUNE,
        "sync_device_status",
        "intune_sync_device",
        ActionKind.READ,
        frozenset({Phase.INVESTIGATION, Phase.VALIDATION}),
        "Read-side refresh (SAD AD-12); not a remediation",
    ),
    ActionSpec(
        McpSystem.INTUNE,
        "apply_policy_or_remediation",
        "intune_apply_policy",
        ActionKind.WRITE,
        frozenset({Phase.EXECUTION}),
        "Apply approved policy or remediation",
    ),
    ActionSpec(
        McpSystem.KB,
        "kb_search",
        "kb_search",
        ActionKind.READ,
        frozenset({Phase.INVESTIGATION, Phase.PROPOSAL}),
        "Vector similarity search over kb_articles for SOP grounding",
    ),
)

CATALOG_BY_KEY: dict[tuple[str, str], ActionSpec] = {
    (spec.system.value, spec.action_type): spec for spec in _CATALOG
}
CATALOG_BY_TOOL: dict[str, ActionSpec] = {spec.tool_name: spec for spec in _CATALOG}

WRITE_ACTIONS: tuple[ActionSpec, ...] = tuple(s for s in _CATALOG if s.kind is ActionKind.WRITE)
READ_ACTIONS: tuple[ActionSpec, ...] = tuple(s for s in _CATALOG if s.kind is ActionKind.READ)

# Granular bindings of PRD §3.4 Jamf “apply approved … scripts” used by
# `jamf_ops_agent` and the Policy 1460 test-loop (SAD AD-16, AD-18).
JAMF_TEST_ACTION_TYPES: frozenset[str] = frozenset(
    {"upload_script", "policy_set_script", "execute_test_policy"}
)


def qualified_tool_name(spec: ActionSpec) -> str:
    """Claude Agent SDK fully-qualified MCP tool name: `mcp__{server_name}__{tool}`.

    `server_name` is `McpSystem.value` — the same key `build_mcp_servers` (and
    `build_kb_search_server`) uses for `ClaudeAgentOptions.mcp_servers`, so this
    stays in sync with the registry without either module importing the other.
    """
    return f"mcp__{spec.system.value}__{spec.tool_name}"


CATALOG_BY_QUALIFIED_TOOL: dict[str, ActionSpec] = {
    qualified_tool_name(spec): spec for spec in _CATALOG
}


def lookup(system: str, action_type: str) -> ActionSpec | None:
    return CATALOG_BY_KEY.get((system, action_type))


def lookup_by_qualified_tool(qualified_name: str) -> ActionSpec | None:
    """Resolve a hook's `tool_name` (e.g. `mcp__jira__jira_get_ticket`) back to its spec."""
    return CATALOG_BY_QUALIFIED_TOOL.get(qualified_name)


def is_authorized_write(system: str, action_type: str) -> bool:
    spec = lookup(system, action_type)
    return spec is not None and spec.kind is ActionKind.WRITE


def read_tool_names(phase: Phase) -> list[str]:
    """Qualified (`mcp__...`) read-tool names allowed in `phase`, for `allowed_tools`."""
    return sorted({qualified_tool_name(s) for s in READ_ACTIONS if phase in s.phases})


def jamf_ops_tool_names(*, include_apply_profile: bool = False) -> list[str]:
    """Qualified Jamf write tools bound to `jamf_ops_agent` (SAD §2 segregation)."""
    action_types = ["upload_script", "policy_set_script", "execute_test_policy"]
    if include_apply_profile:
        action_types.append("apply_profile_or_script")
    names: list[str] = []
    for action_type in action_types:
        spec = lookup("jamf", action_type)
        if spec is not None:
            names.append(qualified_tool_name(spec))
    return sorted(names)


def has_jamf_test_actions(frozen_actions: list[dict[str, object]]) -> bool:
    """True when the frozen list includes Policy 1460 test-loop verbs."""
    return any(
        str(action.get("system", "")) == McpSystem.JAMF.value
        and str(action.get("action_type", "")) in JAMF_TEST_ACTION_TYPES
        for action in frozen_actions
    )


def write_tool_names_for_frozen_actions(frozen_actions: list[dict[str, object]]) -> set[str]:
    """Map a frozen approval action list to the qualified MCP tool names it authorizes.

    Unknown (system, action_type) pairs are ignored here (not authorized) —
    the caller (API) should already have rejected unknown actions at proposal
    time; the worker PEP treats "unknown" the same as "not on the list": deny.
    """
    tools: set[str] = set()
    for action in frozen_actions:
        system = str(action.get("system", ""))
        action_type = str(action.get("action_type", ""))
        spec = lookup(system, action_type)
        if spec is not None and spec.kind is ActionKind.WRITE:
            tools.add(qualified_tool_name(spec))
    return tools
