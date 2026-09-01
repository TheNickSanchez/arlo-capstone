"""ArloRemediationWorkflow — Temporal Workflow (SAD §2, §6).

Deterministic control flow only. No LLM, MCP, or DB drivers — Activities
are referenced by registered string name only. Lifecycle:

    if `jira_analysis_only`: inspect_and_comment → Done (no HITL, no other MCP)
    elif `jira_beta_prod`: investigate → generate_proposal → post_proposal_comment
    → wait_condition(Signal `approval_decision`) — no endpoint writes until Signal
    else: smoke-test (optional) → investigate → generate_proposal
    → wait_condition(Signal `approval_decision`)
    → execute_approved (approve + hash match only) → validate_and_close

No auto-approve timers (PRD: no auto-approve). Wake paths are the
`approval_decision` Signal only (approve / reject / cancel).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from backend.app.domain.workflow_contracts import (
        ApprovalDecision,
        ExecuteApprovedInput,
        GenerateProposalInput,
        MarkFailedInput,
        PostProposalCommentInput,
        RemediationWorkflowInput,
        ValidateAndCloseInput,
    )

_TRANSIENT_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=5),
    maximum_attempts=3,
)


@dataclass
class _StageResult:
    ok: bool
    value: object = None
    reason: str = ""


@workflow.defn(name="ArloRemediationWorkflow")
class ArloRemediationWorkflow:
    def __init__(self) -> None:
        self._decision: ApprovalDecision | None = None

    @workflow.signal
    def approval_decision(self, decision: ApprovalDecision) -> None:
        """Wake signal (SAD AD-7). The API writes the `approvals` row before
        or in the same request as this Signal. The Workflow re-validates
        `proposal_hash` defensively before scheduling Execution."""
        self._decision = decision

    async def _run_stage(
        self, arlo_id: str, phase: str, activity_name: str, arg: object, timeout: timedelta
    ) -> _StageResult:
        try:
            value = await workflow.execute_activity(
                activity_name,
                arg,
                start_to_close_timeout=timeout,
                retry_policy=_TRANSIENT_RETRY_POLICY,
            )
        except ActivityError as exc:
            reason = str(exc.cause) if exc.cause else str(exc)
            await workflow.execute_activity(
                "mark_failed",
                MarkFailedInput(arlo_id=arlo_id, phase=phase, reason=reason),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            return _StageResult(ok=False, reason=reason)
        return _StageResult(ok=True, value=value)

    @workflow.run
    async def run(self, input: RemediationWorkflowInput) -> str:
        investigation_timeout = timedelta(seconds=input.investigation_timeout_seconds)
        execution_timeout = timedelta(seconds=input.execution_timeout_seconds)

        if input.jira_analysis_only:
            analysis_stage = await self._run_stage(
                input.arlo_id,
                "Investigating",
                "inspect_and_comment",
                input,
                investigation_timeout,
            )
            return "Done" if analysis_stage.ok else "Failed"

        if input.smoke_test_enabled:
            # Build/demo verification only — see worker.activities.test_comment.
            # Best-effort: failure here must not block the real lifecycle.
            try:
                await workflow.execute_activity(
                    "post_smoke_test_comment",
                    input,
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=RetryPolicy(maximum_attempts=2),
                )
            except ActivityError:
                pass

        investigate_stage = await self._run_stage(
            input.arlo_id, "Investigating", "investigate", input, investigation_timeout
        )
        if not investigate_stage.ok:
            return "Failed"
        evidence_pack = investigate_stage.value

        proposal_stage = await self._run_stage(
            input.arlo_id,
            "Investigating",
            "generate_proposal",
            GenerateProposalInput(
                arlo_id=input.arlo_id,
                ticket_system=input.ticket_system,
                ticket_key=input.ticket_key,
                evidence_pack=evidence_pack,
                jira_beta_prod=input.jira_beta_prod,
            ),
            investigation_timeout,
        )
        if not proposal_stage.ok:
            return "Failed"
        proposal = proposal_stage.value

        if input.jira_beta_prod:
            comment_stage = await self._run_stage(
                input.arlo_id,
                "Awaiting Approval",
                "post_proposal_comment",
                PostProposalCommentInput(
                    arlo_id=input.arlo_id,
                    ticket_system=input.ticket_system,
                    ticket_key=input.ticket_key,
                    proposal=proposal if isinstance(proposal, dict) else {},
                ),
                investigation_timeout,
            )
            if not comment_stage.ok:
                return "Failed"

        # HITL sleep. Beta-prod and full path both stop here until Signal.
        # No Jamf/Intune/ServiceNow writes are scheduled before this wait.
        await workflow.wait_condition(lambda: self._decision is not None)
        decision = self._decision
        assert decision is not None

        if decision.action != "approve":
            return decision.action

        if decision.proposal_hash != proposal.get("proposal_hash"):
            await workflow.execute_activity(
                "mark_failed",
                MarkFailedInput(
                    arlo_id=input.arlo_id,
                    phase="Awaiting Approval",
                    reason="proposal_hash mismatch on approval Signal",
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            return "Failed"

        execute_stage = await self._run_stage(
            input.arlo_id,
            "Executing",
            "execute_approved",
            ExecuteApprovedInput(
                arlo_id=input.arlo_id,
                ticket_system=input.ticket_system,
                ticket_key=input.ticket_key,
                proposal=proposal,
            ),
            execution_timeout,
        )
        if not execute_stage.ok:
            return "Failed"
        execution_summary = execute_stage.value

        validate_stage = await self._run_stage(
            input.arlo_id,
            "Executing",
            "validate_and_close",
            ValidateAndCloseInput(
                arlo_id=input.arlo_id,
                ticket_system=input.ticket_system,
                ticket_key=input.ticket_key,
                proposal=proposal,
                execution_summary=execution_summary,
                evidence_pack=evidence_pack,
            ),
            execution_timeout,
        )
        if not validate_stage.ok:
            return "Failed"

        return "Done"
