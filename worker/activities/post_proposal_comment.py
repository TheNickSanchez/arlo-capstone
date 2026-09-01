"""Activity `post_proposal_comment` — Jira discovery/proposal comment.

Operator-authorized HITL exception for `ARLO_JIRA_BETA_PROD`: publish the
executive proposal as a ticket comment, then the Workflow sleeps at
`Awaiting Approval`. Markdown is converted to ADF inside live
`jira_post_comment`. No Jamf/Intune/ServiceNow writes.
"""

from __future__ import annotations

from temporalio import activity

from backend.app.db.session import session_scope
from backend.app.domain.actions import McpSystem
from backend.app.domain.status import InstanceStatus
from backend.app.domain.workflow_contracts import PostProposalCommentInput
from backend.app.schemas.proposal import ProposalPayload
from backend.app.services.audit import append_audit_event
from worker.activities.comment_format import executive_comment_from_proposal
from worker.activities.common import non_retryable, record_diagnostic
from worker.mcp.raw_client import McpToolCallError, call_tool


@activity.defn(name="post_proposal_comment")
async def post_proposal_comment(input: PostProposalCommentInput) -> dict:
    activity.logger.info(
        "post_proposal_comment start arlo_id=%s ticket=%s", input.arlo_id, input.ticket_key
    )
    if input.ticket_system != "jira":
        raise non_retryable("post_proposal_comment is Jira-only", arlo_id=input.arlo_id)

    proposal = ProposalPayload.model_validate(input.proposal)
    posted = executive_comment_from_proposal(proposal)

    try:
        call_result = await call_tool(
            McpSystem.JIRA,
            "jira_post_comment",
            {"ticket_key": input.ticket_key, "body": posted},
        )
    except McpToolCallError as exc:
        async with session_scope() as session:
            await record_diagnostic(
                session,
                arlo_id=input.arlo_id,
                phase=InstanceStatus.AWAITING_APPROVAL.value,
                summary=f"jira_post_comment failed: {exc}",
            )
        raise

    async with session_scope() as session:
        await append_audit_event(
            session,
            arlo_id=input.arlo_id,
            phase=InstanceStatus.AWAITING_APPROVAL.value,
            kind="jira_proposal_comment",
            summary=f"proposal comment posted to {input.ticket_key}",
            payload_json={
                "comment_id": call_result.get("comment_id"),
                "url": call_result.get("url"),
            },
            mcp_system=McpSystem.JIRA.value,
            action="jira_post_comment",
            result="success",
        )

    return {"ok": True, "jira": call_result}
