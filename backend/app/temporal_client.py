"""Temporal client boundary for the FastAPI process (SAD §4 Runtime Integration Layer).

The API is the only component that starts Workflows and sends Signals
(SAD §1 Logical Architecture element catalog). It never imports the Claude
Agent SDK or MCP clients — only the Workflow *type* (for `start_workflow`
type-checking) and the shared dataclass contracts.

A single lazily-connected client is cached per process; `Client.connect` is
cheap to call repeatedly but the connection itself is reused across requests.
"""

from __future__ import annotations

import asyncio
import logging

from temporalio.client import (
    Client,
    WorkflowExecutionStatus,
    WorkflowFailureError,
    WorkflowHandle,
)
from temporalio.service import RPCError

from backend.app.config import settings
from backend.app.domain.errors import UpstreamUnavailableError
from backend.app.domain.ids import workflow_id_for
from backend.app.domain.workflow_contracts import (
    ApprovalDecision,
    RemediationWorkflowInput,
    resolve_lifecycle_flags,
)

logger = logging.getLogger("arlo.temporal_client")

_client: Client | None = None
_client_lock = asyncio.Lock()


async def get_temporal_client() -> Client:
    global _client
    if _client is not None:
        return _client
    async with _client_lock:
        if _client is None:
            try:
                _client = await Client.connect(
                    settings.temporal_address, namespace=settings.temporal_namespace
                )
            except Exception as exc:  # connection refused, DNS failure, etc.
                raise UpstreamUnavailableError(f"Temporal unavailable: {exc}") from exc
    return _client


async def check_temporal_ready() -> bool:
    try:
        client = await get_temporal_client()
        # A lightweight RPC that requires a live frontend connection.
        await client.service_client.check_health()
        return True
    except Exception:
        return False


def _workflow_run_ref():
    # Imported lazily so importing `backend.app` never pulls in `worker` (and
    # therefore never pulls in `claude_agent_sdk`) unless a workflow is
    # actually started/signalled.
    from worker.workflows.remediation import ArloRemediationWorkflow

    return ArloRemediationWorkflow.run, ArloRemediationWorkflow.approval_decision


async def start_remediation_workflow(
    *, arlo_id: str, ticket_system: str, ticket_key: str
) -> str:
    """Start `ArloRemediationWorkflow`; returns the Temporal workflow id."""
    run_method, _ = _workflow_run_ref()
    client = await get_temporal_client()
    workflow_id = workflow_id_for(arlo_id)
    smoke, analysis_only, beta_prod = resolve_lifecycle_flags(
        smoke_enabled=settings.arlo_smoke_test_enabled,
        analysis_only=settings.arlo_jira_analysis_only,
        beta_prod=settings.arlo_jira_beta_prod,
    )
    try:
        await client.start_workflow(
            run_method,
            RemediationWorkflowInput(
                arlo_id=arlo_id,
                ticket_system=ticket_system,
                ticket_key=ticket_key,
                smoke_test_enabled=smoke,
                jira_analysis_only=analysis_only,
                jira_beta_prod=beta_prod,
                investigation_timeout_seconds=settings.investigation_timeout_seconds,
                execution_timeout_seconds=settings.execution_timeout_seconds,
                jamf_test_policy_id=settings.jamf_test_policy_id,
                jamf_test_event=settings.jamf_test_event,
                script_test_max_attempts=settings.arlo_script_test_max_attempts,
            ),
            id=workflow_id,
            task_queue=settings.arlo_task_queue,
        )
    except Exception as exc:
        raise UpstreamUnavailableError(f"failed to start workflow {workflow_id}: {exc}") from exc
    return workflow_id


async def signal_approval_decision(*, arlo_id: str, decision: ApprovalDecision) -> None:
    _, signal_method = _workflow_run_ref()
    client = await get_temporal_client()
    handle: WorkflowHandle = client.get_workflow_handle(workflow_id_for(arlo_id))
    try:
        await handle.signal(signal_method, decision)
    except RPCError as exc:
        raise UpstreamUnavailableError(f"failed to signal {arlo_id}: {exc}") from exc


async def workflow_status(arlo_id: str) -> WorkflowExecutionStatus | None:
    """Best-effort Temporal-reported status, used only for `/ready`-style diagnostics.

    PostgreSQL `instances.status` remains the UI/API source of truth (SAD §4);
    this helper is not on the request path for list/detail.
    """
    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id_for(arlo_id))
    try:
        description = await handle.describe()
        return description.status
    except (RPCError, WorkflowFailureError):
        return None
