"""Temporal Workflow input/signal payload shapes (SAD §2, §4, AD-7).

Shared by `backend.app.temporal_client` (typed `start_workflow` / `signal`
calls from the API process) and `worker.workflows.remediation` (the
Workflow definition itself). Keeping these dataclasses here — rather than
duplicating them per process — is what makes `client.start_workflow(Workflow.run,
...)` type-check and stay wire-compatible across API and worker deploys.

Temporal serializes dataclasses with its default (JSON) data converter, so
these must remain plain, JSON-serializable dataclasses: no ORM objects, no
`datetime` timezone edge cases beyond ISO 8601 strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ApprovalAction = Literal["approve", "reject", "cancel"]


JAMF_TEST_ACTION_TYPES = frozenset({"upload_script", "policy_set_script", "execute_test_policy"})


def proposal_has_jamf_test_actions(proposal: dict) -> bool:
    """Pure check for the Workflow test-loop (SAD AD-18). No I/O."""
    return any(
        str(action.get("system", "")) == "jamf"
        and str(action.get("action_type", "")) in JAMF_TEST_ACTION_TYPES
        for action in proposal.get("write_actions", []) or []
    )


def resolve_lifecycle_flags(
    *, smoke_enabled: bool, analysis_only: bool, beta_prod: bool
) -> tuple[bool, bool, bool]:
    """Return `(smoke_test_enabled, jira_analysis_only, jira_beta_prod)`.

    `ARLO_JIRA_BETA_PROD` wins over analysis-only. Either lifecycle mode
    disables the smoke-test comment.
    """
    jira_beta_prod = beta_prod
    jira_analysis_only = analysis_only and not jira_beta_prod
    smoke_test_enabled = smoke_enabled and not jira_analysis_only and not jira_beta_prod
    return smoke_test_enabled, jira_analysis_only, jira_beta_prod


@dataclass
class RemediationWorkflowInput:
    arlo_id: str
    ticket_system: str
    ticket_key: str
    smoke_test_enabled: bool = False
    """Decided by the API at `start_workflow` time (SAD AD-1 determinism: the
    Workflow must not read env vars itself), not by the Workflow reading env."""
    jira_analysis_only: bool = False
    """Operator-authorized Jira-only slice: inspect ticket, post analysis
    comment, stop. No other MCP systems, no HITL wait, no execution."""
    jira_beta_prod: bool = False
    """Operator-authorized discovery + proposal lifecycle: identify platform,
    read Jamf/Intune, post an ADF proposal comment, then wait at
    Awaiting Approval. No endpoint writes until a human Signal."""
    investigation_timeout_seconds: int = 900
    execution_timeout_seconds: int = 900
    """`start_to_close_timeout` budgets for the matching Activities, threaded
    through from `backend.app.config` at start time for the same determinism
    reason — the Workflow module must not import Settings itself."""
    jamf_test_policy_id: int = 1460
    jamf_test_event: str = "arlo_test"
    script_test_max_attempts: int = 3


@dataclass
class ApprovalDecision:
    action: ApprovalAction
    actor_id: str
    at: str
    proposal_hash: str | None = None
    rationale: str | None = None


@dataclass
class ProposalWriteActionPayload:
    system: str
    action_type: str
    target_ids: list[str] = field(default_factory=list)


@dataclass
class GenerateProposalInput:
    arlo_id: str
    ticket_system: str
    ticket_key: str
    evidence_pack: dict = field(default_factory=dict)
    jira_beta_prod: bool = False


@dataclass
class PostProposalCommentInput:
    arlo_id: str
    ticket_system: str
    ticket_key: str
    proposal: dict = field(default_factory=dict)


@dataclass
class WriteScriptInput:
    arlo_id: str
    ticket_key: str
    evidence_pack: dict = field(default_factory=dict)
    test_log: dict | None = None
    """When set, `script_writer_agent` refactors from Policy 1460 stdout/stderr."""
    attempt: int = 0
    prior_script: str | None = None


@dataclass
class ExecuteJamfTestInput:
    arlo_id: str
    ticket_key: str
    proposal: dict = field(default_factory=dict)
    attempt: int = 0
    policy_id: int = 1460
    event: str = "arlo_test"
    script_contents: str | None = None
    script_filename: str = "arlo-remediation.sh"
    script_os: str = "macOS"


@dataclass
class ExecuteApprovedInput:
    arlo_id: str
    ticket_system: str
    ticket_key: str
    proposal: dict = field(default_factory=dict)


@dataclass
class ValidateAndCloseInput:
    arlo_id: str
    ticket_system: str
    ticket_key: str
    proposal: dict = field(default_factory=dict)
    execution_summary: dict = field(default_factory=dict)
    evidence_pack: dict = field(default_factory=dict)
    """Threaded through from `investigate` for `app_name` / `platform` on
    `learned_patterns` persist (SAD §2 step 8); not re-fetched from MCP."""


@dataclass
class MarkFailedInput:
    arlo_id: str
    phase: str
    reason: str
