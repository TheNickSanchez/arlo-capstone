"""Activity `inspect_and_comment` — Jira-only analysis slice.

Operator-authorized test path: read the mapped Jira ticket, evaluate what
needs to get done, post that analysis as a comment, then stop. No other MCP
systems. No HITL execution. No ticket transition/close.
"""

from __future__ import annotations

import json

from temporalio import activity

from backend.app.config import settings
from backend.app.db.session import session_scope
from backend.app.domain.actions import McpSystem
from backend.app.domain.status import InstanceStatus
from backend.app.domain.workflow_contracts import RemediationWorkflowInput
from backend.app.models.instance import Instance
from backend.app.schemas.analysis import TicketAnalysis
from backend.app.services.audit import append_audit_event
from worker.activities.common import (
    non_retryable,
    record_diagnostic,
    run_claude_query,
    transition_status,
)
from worker.mcp.claude_client import build_claude_options
from worker.mcp.jira_cloud import live_jira_configured
from worker.mcp.raw_client import McpToolCallError, call_tool

_SYSTEM_PROMPT = """You are ARLO performing a Jira-only inspection. You are given ticket \
JSON already fetched from Jira. Do not invent facts that are not in the ticket. Identify \
what needs to get done and what is still unknown. Write `comment_body` as a concise ticket \
comment a human can act on: short summary, numbered next steps, and open questions. Do not \
recommend wiping devices, changing identity, or any action outside the ticket's stated work. \
Return only TicketAnalysis JSON."""


async def _diagnose(arlo_id: str, summary: str) -> None:
    async with session_scope() as session:
        await record_diagnostic(
            session,
            arlo_id=arlo_id,
            phase=InstanceStatus.INVESTIGATING.value,
            summary=summary,
        )


@activity.defn(name="inspect_and_comment")
async def inspect_and_comment(input: RemediationWorkflowInput) -> dict:
    activity.logger.info("inspect_and_comment start arlo_id=%s ticket=%s", input.arlo_id, input.ticket_key)

    if input.ticket_system != "jira":
        raise non_retryable("inspect_and_comment is Jira-only", arlo_id=input.arlo_id)
    if not live_jira_configured():
        await _diagnose(
            input.arlo_id,
            "live Jira credentials missing (ATLASSIAN_SITE_NAME / ATLASSIAN_EMAIL / ATLASSIAN_API_TOKEN)",
        )
        raise non_retryable("live Jira is not configured", arlo_id=input.arlo_id)

    async with session_scope() as session:
        instance = await session.get(Instance, input.arlo_id)
        if instance is None:
            raise non_retryable(f"instance {input.arlo_id} missing", arlo_id=input.arlo_id)
        if instance.status == InstanceStatus.DONE.value and instance.proposal_json:
            return {"ok": True, "analysis": instance.proposal_json, "idempotent": True}

    try:
        ticket = await call_tool(McpSystem.JIRA, "jira_get_ticket", {"ticket_key": input.ticket_key})
    except McpToolCallError as exc:
        await _diagnose(input.arlo_id, f"jira_get_ticket failed: {exc}")
        raise

    if not ticket.get("found"):
        await _diagnose(input.arlo_id, f"Jira ticket {input.ticket_key} not found")
        raise non_retryable(f"Jira ticket {input.ticket_key} not found", arlo_id=input.arlo_id)

    async with session_scope() as session:
        await append_audit_event(
            session,
            arlo_id=input.arlo_id,
            phase=InstanceStatus.INVESTIGATING.value,
            kind="jira_read",
            summary=f"read {input.ticket_key}: {ticket.get('summary') or '(no summary)'}",
            mcp_system=McpSystem.JIRA.value,
            action="jira_get_ticket",
            result="success",
        )

    options = build_claude_options(
        system_prompt=_SYSTEM_PROMPT,
        allowed_tools=[],
        max_turns=8,
        output_format={"type": "json_schema", "schema": TicketAnalysis.model_json_schema()},
    )
    prompt = (
        f"ARLO instance {input.arlo_id} is inspecting this Jira ticket. "
        "Evaluate what needs to get done. Do not call tools.\n\n"
        f"{json.dumps(ticket, indent=2, default=str)}"
    )

    try:
        result = await run_claude_query(prompt=prompt, options=options)
        analysis = TicketAnalysis.model_validate(result.structured_output)
    except Exception as exc:
        await _diagnose(input.arlo_id, f"analysis failed: {exc}")
        raise

    header = (
        f"[Arlo] Analysis for {input.arlo_id} "
        "(inspect only — no endpoint or ticket mutation beyond this comment)"
    )
    comment_body = analysis.comment_body.strip() or analysis.summary
    posted = f"{header}\n\n{comment_body}"

    try:
        call_result = await call_tool(
            McpSystem.JIRA,
            "jira_post_comment",
            {"ticket_key": input.ticket_key, "body": posted},
        )
    except McpToolCallError as exc:
        await _diagnose(input.arlo_id, f"jira_post_comment failed: {exc}")
        raise

    payload = analysis.model_dump(mode="json")
    async with session_scope() as session:
        instance = await session.get(Instance, input.arlo_id)
        if instance is None:
            raise non_retryable(
                f"instance {input.arlo_id} missing during inspect_and_comment",
                arlo_id=input.arlo_id,
            )
        instance.proposal_json = payload
        await transition_status(session, instance, InstanceStatus.DONE)
        await append_audit_event(
            session,
            arlo_id=input.arlo_id,
            phase=InstanceStatus.DONE.value,
            kind="jira_analysis",
            summary=f"analysis comment posted to {input.ticket_key}",
            payload_json={"comment_id": call_result.get("comment_id"), "url": call_result.get("url")},
            mcp_system=McpSystem.JIRA.value,
            action="jira_post_comment",
            result="success",
        )

    return {"ok": True, "analysis": payload, "jira": call_result, "model": settings.claude_model}
