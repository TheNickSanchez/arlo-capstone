"""Activity `generate_proposal` (SAD §2 step 3; PRD FR-P0-03).

No vendor MCP writes — `kb_search` remains available for follow-up grounding
only. Persists the proposal + `proposal_hash` and transitions the instance to
`Awaiting Approval` on success (SAD §2: "Status -> Awaiting Approval").
"""

from __future__ import annotations

import json

from temporalio import activity

from backend.app.config import settings
from backend.app.db.session import session_scope
from backend.app.domain.actions import Phase, read_tool_names
from backend.app.domain.hashing import proposal_hash as compute_proposal_hash
from backend.app.domain.status import InstanceStatus
from backend.app.domain.workflow_contracts import GenerateProposalInput
from backend.app.models.instance import Instance
from backend.app.schemas.evidence import EvidencePack
from backend.app.schemas.proposal import ProposalPayload
from backend.app.services.audit import append_audit_event
from worker.activities.common import record_diagnostic, run_claude_query, transition_status
from worker.mcp.agents import coordinator_agents
from worker.mcp.claude_client import build_claude_options
from worker.mcp.kb_search_server import build_kb_search_server
from worker.pep import build_hooks

_PROPOSAL_SYSTEM_PROMPT = """You are ARLO's proposal specialist (PRD FR-P0-03). Given an \
EvidencePack, produce a human-reviewable remediation proposal: concrete findings, an exact \
enumerated list of the writes you want authorized (`write_actions`, each with `system`, \
`action_type` matching PRD §3.4, and `target_ids`), validation checks that must pass before \
closing the ticket, residual risk, and citations of any `learned_patterns` / `kb_articles` you \
relied on. You have NO write tools and must not attempt any mutation. If this fix is a reusable, \
non-ticket-specific pattern (a `script_fix`, `version_endpoint`, or `vendor_gotcha`), set \
`pattern_type` and a concise `solution_summary`; otherwise leave both empty. Return only the \
ProposalPayload JSON."""


@activity.defn(name="generate_proposal")
async def generate_proposal(input: GenerateProposalInput) -> dict:
    activity.logger.info("generate_proposal start arlo_id=%s", input.arlo_id)
    evidence = EvidencePack.model_validate(input.evidence_pack)

    options = build_claude_options(
        system_prompt=_PROPOSAL_SYSTEM_PROMPT,
        allowed_tools=read_tool_names(Phase.PROPOSAL),
        agents=coordinator_agents(),
        mcp_servers={"kb": build_kb_search_server()},
        hooks=build_hooks(
            arlo_id=input.arlo_id,
            activity_phase=InstanceStatus.INVESTIGATING.value,
            read_phase=Phase.PROPOSAL,
            writes_enabled=False,
        ),
        max_turns=settings.investigation_max_turns,
        output_format={"type": "json_schema", "schema": ProposalPayload.model_json_schema()},
    )
    prompt = (
        f"EvidencePack for ticket {input.ticket_key}:\n"
        f"{json.dumps(evidence.model_dump(mode='json'), indent=2)}\n\n"
        "Produce the ProposalPayload JSON now."
    )

    try:
        result = await run_claude_query(prompt=prompt, options=options)
        proposal = ProposalPayload.model_validate(result.structured_output)
    except Exception as exc:
        async with session_scope() as session:
            await record_diagnostic(
                session,
                arlo_id=input.arlo_id,
                phase=InstanceStatus.INVESTIGATING.value,
                summary=f"generate_proposal failed: {exc}",
            )
        raise

    body = proposal.model_dump(mode="json", exclude={"proposal_hash"})
    proposal.proposal_hash = compute_proposal_hash(body)

    async with session_scope() as session:
        instance = await session.get(Instance, input.arlo_id)
        if instance is None:
            raise RuntimeError(f"instance {input.arlo_id} missing during generate_proposal")
        instance.proposal_json = proposal.model_dump(mode="json")
        instance.proposal_hash = proposal.proposal_hash
        await transition_status(session, instance, InstanceStatus.AWAITING_APPROVAL)
        await append_audit_event(
            session,
            arlo_id=input.arlo_id,
            phase=InstanceStatus.AWAITING_APPROVAL.value,
            kind="proposal_generated",
            summary=(
                f"proposal generated with {len(proposal.write_actions)} enumerated write(s); "
                f"hash={proposal.proposal_hash[:12]}"
            ),
            payload_json={"proposal_hash": proposal.proposal_hash},
        )

    return proposal.model_dump(mode="json")
