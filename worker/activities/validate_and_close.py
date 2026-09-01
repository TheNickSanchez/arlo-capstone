"""Activity `validate_and_close` — Validation + Persist Phase (SAD §2 step 8).

Validation reads (`Phase.VALIDATION`); ticket close/transition only if that
write was on the approved plan **and** validation criteria passed (PRD
default: no close on partial — a halted/failed `execute_approved` disables
writes here entirely, it does not just skip the close). On successful
validation of a new-or-reused fix, appends/increments a `learned_patterns`
row (Activity SQL, not an MCP vendor write) so later instances inherit it
immediately (SAD §2 step 8, `ARLO-680` example).
"""

from __future__ import annotations

import json

from sqlalchemy import select
from temporalio import activity

from backend.app.config import settings
from backend.app.db.session import session_scope
from backend.app.domain.actions import (
    McpSystem,
    Phase,
    read_tool_names,
    write_tool_names_for_frozen_actions,
)
from backend.app.domain.hashing import canonical_json_hash
from backend.app.domain.status import InstanceStatus
from backend.app.domain.workflow_contracts import ValidateAndCloseInput
from backend.app.models.instance import Instance
from backend.app.models.learned_pattern import LearnedPattern
from backend.app.schemas.evidence import EvidencePack
from backend.app.schemas.proposal import ProposalPayload
from backend.app.schemas.validation import ValidationResult
from backend.app.services.audit import append_audit_event
from worker.activities.common import run_claude_query, transition_status
from worker.mcp.claude_client import build_claude_options
from worker.mcp.registry import build_mcp_servers
from worker.pep import build_hooks

_VALIDATOR_SYSTEM_PROMPT = """You are ARLO's Validation specialist (PRD Open Question 6). \
Re-read the current compliance/asset/ticket state with your read-only tools and judge whether \
every `validation_checks` item from the approved proposal now passes. If (and only if) they all \
pass AND a ticket close/transition write is on your approved write list, use it to close or \
transition the ticket. Never close on a partial result — if execution was halted or any check \
fails, set `passed` to false and do not attempt the close/transition tool even if it is \
available. Return only the ValidationResult JSON: {passed, notes, closed_ticket}."""


def _natural_key_hash(problem_description: str) -> str:
    return canonical_json_hash({"problem_description": problem_description})


async def _persist_learned_pattern(
    session,
    *,
    arlo_id: str,
    app_name: str | None,
    platform: str | None,
    pattern_type: str | None,
    solution_summary: str,
    findings: list[str],
) -> None:
    if not pattern_type or not app_name or not platform:
        return

    problem_description = "; ".join(findings) or f"{app_name} remediation on {platform}"
    problem_hash = _natural_key_hash(problem_description)

    existing = (
        await session.execute(
            select(LearnedPattern).where(
                LearnedPattern.app_name == app_name,
                LearnedPattern.platform == platform,
                LearnedPattern.pattern_type == pattern_type,
                LearnedPattern.problem_description_hash == problem_hash,
            )
        )
    ).scalar_one_or_none()

    if existing is not None:
        existing.success_count += 1
        from datetime import UTC, datetime

        existing.last_verified_at = datetime.now(UTC)
    else:
        session.add(
            LearnedPattern(
                app_name=app_name,
                platform=platform,
                pattern_type=pattern_type,
                problem_description=problem_description,
                problem_description_hash=problem_hash,
                solution_payload={"summary": solution_summary},
                created_by_arlo_id=arlo_id,
            )
        )
    await session.flush()


@activity.defn(name="validate_and_close")
async def validate_and_close(input: ValidateAndCloseInput) -> dict:
    activity.logger.info("validate_and_close start arlo_id=%s", input.arlo_id)
    proposal = ProposalPayload.model_validate(input.proposal)
    evidence = EvidencePack.model_validate(input.evidence_pack) if input.evidence_pack else None
    execution_halted = bool(input.execution_summary.get("halted", False))

    frozen_actions = [action.model_dump() for action in proposal.write_actions]
    allowed_write_tools = write_tool_names_for_frozen_actions(frozen_actions) if not execution_halted else frozenset()

    state = {"halted": execution_halted}

    def _on_result(tool_name: str, response: dict) -> None:
        if isinstance(response, dict) and response.get("ok") is False:
            state["halted"] = True

    options = build_claude_options(
        system_prompt=_VALIDATOR_SYSTEM_PROMPT,
        allowed_tools=[*read_tool_names(Phase.VALIDATION), *sorted(allowed_write_tools)],
        mcp_servers=build_mcp_servers([McpSystem.JIRA, McpSystem.SERVICENOW, McpSystem.JAMF, McpSystem.INTUNE]),
        hooks=build_hooks(
            arlo_id=input.arlo_id,
            activity_phase=InstanceStatus.EXECUTING.value,
            read_phase=Phase.VALIDATION,
            writes_enabled=not execution_halted,
            allowed_write_tools=frozenset(allowed_write_tools),
            is_halted=lambda: state["halted"],
            on_result=_on_result,
        ),
        max_turns=settings.execution_max_turns,
        output_format={"type": "json_schema", "schema": ValidationResult.model_json_schema()},
    )
    prompt = (
        f"Approved proposal for ticket {input.ticket_key}:\n"
        f"{json.dumps(proposal.model_dump(mode='json'), indent=2)}\n\n"
        f"Execution summary: {json.dumps(input.execution_summary)}\n"
        f"Execution halted (no-close-on-partial applies): {execution_halted}\n\n"
        "Re-check the validation_checks now and decide whether to close/transition the ticket."
    )

    result = await run_claude_query(prompt=prompt, options=options)
    validation = ValidationResult.model_validate(result.structured_output)
    passed = validation.passed and not execution_halted

    async with session_scope() as session:
        instance = await session.get(Instance, input.arlo_id)
        if instance is None:
            raise RuntimeError(f"instance {input.arlo_id} missing during validate_and_close")
        target = InstanceStatus.DONE if passed else InstanceStatus.FAILED
        await transition_status(session, instance, target)

        if passed:
            await _persist_learned_pattern(
                session,
                arlo_id=input.arlo_id,
                app_name=evidence.app_name if evidence else None,
                platform=evidence.platform if evidence else None,
                pattern_type=proposal.pattern_type,
                solution_summary=proposal.solution_summary,
                findings=proposal.findings,
            )

        await append_audit_event(
            session,
            arlo_id=input.arlo_id,
            phase=target.value,
            kind="validation_complete",
            summary=f"validation {'passed' if passed else 'failed'}: {validation.notes}",
            payload_json={"closed_ticket": validation.closed_ticket, "execution_halted": execution_halted},
        )

    return {"passed": passed, "notes": validation.notes, "closed_ticket": validation.closed_ticket}
