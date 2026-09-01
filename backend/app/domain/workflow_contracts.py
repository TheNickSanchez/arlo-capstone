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
    investigation_timeout_seconds: int = 900
    execution_timeout_seconds: int = 900
    """`start_to_close_timeout` budgets for the matching Activities, threaded
    through from `backend.app.config` at start time for the same determinism
    reason — the Workflow module must not import Settings itself."""


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
