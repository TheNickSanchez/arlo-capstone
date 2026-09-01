"""`PreToolUse` Policy Enforcement Point (SAD AD-9; PRD FR-P0-10).

Deny any state-changing **vendor** tool call unless this Activity was built
with `writes_enabled=True` *and* the tool is on that instance's frozen
approved-action list. The Activity fixes `read_phase` / `writes_enabled` /
`allowed_write_tools` in Python **before** the `ClaudeSDKClient` session ever
starts (SAD: "outside the model") — nothing here trusts the model's stated
phase or reasoning.

Read tools are gated independently of writes by `read_phase` (the catalog's
`Phase`, e.g. Investigation vs. Validation) because `validate_and_close` needs
Validation-phase reads *and* Execution-phase writes (closing the ticket) in
the same Activity/session (SAD §2 step 8).

`PostToolUse` mirrors every tool call (success or deny) into `audit_events`
(SAD §2: "PostToolUse = audit append (redact secrets)"). The `activity_phase`
passed here is the `instances.status` vocabulary (e.g. "Investigating"), for
consistency with the rest of the audit log (`backend.app.services.instances`
uses the same convention) — it is distinct from the catalog's lowercase
`Phase` enum used for tool-gating.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable

from claude_agent_sdk.types import (
    HookContext,
    HookMatcher,
    PostToolUseHookInput,
    PreToolUseHookInput,
    PreToolUseHookSpecificOutput,
    SyncHookJSONOutput,
)

from backend.app.db.session import session_scope
from backend.app.domain.actions import ActionKind, Phase, lookup_by_qualified_tool
from backend.app.services.audit import append_audit_event

logger = logging.getLogger("arlo.worker.pep")

_REDACT_KEYS = {"token", "secret", "password", "api_key", "authorization"}


def _redact(payload: dict) -> dict:
    def _clean(value):
        if isinstance(value, dict):
            return {
                k: ("***redacted***" if k.lower() in _REDACT_KEYS else _clean(v))
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [_clean(v) for v in value]
        return value

    return _clean(payload)


async def _audit(
    *,
    arlo_id: str,
    activity_phase: str,
    kind: str,
    summary: str,
    payload_json: dict,
    mcp_system: str | None,
    action: str,
    result: str,
    policy_deny: bool,
) -> None:
    try:
        async with session_scope() as session:
            await append_audit_event(
                session,
                arlo_id=arlo_id,
                phase=activity_phase,
                kind=kind,
                summary=summary,
                payload_json=_redact(payload_json),
                mcp_system=mcp_system,
                action=action,
                result=result,
                policy_deny=policy_deny,
            )
    except Exception:
        logger.exception("failed to audit %s for %s (%s)", kind, arlo_id, action)


def build_pretooluse_hook(
    *,
    arlo_id: str,
    activity_phase: str,
    read_phase: Phase | None,
    writes_enabled: bool = False,
    allowed_write_tools: frozenset[str] = frozenset(),
    is_halted: Callable[[], bool] | None = None,
) -> Callable[[PreToolUseHookInput, str | None, HookContext], Awaitable[SyncHookJSONOutput]]:
    """Build a `PreToolUse` callback closed over this Activity's fixed policy.

    `is_halted` (optional) lets `execute_approved` stop *all further writes*
    once one has failed (SAD §2 step 7: "Default halt remaining writes on
    first failure") without needing a second hook type.
    """

    async def _hook(
        input_data: PreToolUseHookInput, _tool_use_id: str | None, _context: HookContext
    ) -> SyncHookJSONOutput:
        tool_name = input_data["tool_name"]
        spec = lookup_by_qualified_tool(tool_name)

        if spec is None:
            decision, reason = "deny", f"{tool_name} is not an authorized MCP action (PRD §3.4)"
        elif spec.kind is ActionKind.READ:
            if read_phase is not None and read_phase in spec.phases:
                decision, reason = "allow", None
            else:
                decision, reason = "deny", f"{tool_name} is not a read action permitted here"
        else:  # WRITE
            if not writes_enabled:
                decision, reason = "deny", f"{tool_name}: writes are not enabled for this Activity"
            elif is_halted is not None and is_halted():
                decision, reason = "deny", "execution halted after an earlier write failure"
            elif tool_name not in allowed_write_tools:
                decision, reason = "deny", f"{tool_name} is not on the frozen approved-action list"
            else:
                decision, reason = "allow", None

        if decision == "deny":
            logger.warning("PEP deny arlo_id=%s tool=%s reason=%s", arlo_id, tool_name, reason)
            await _audit(
                arlo_id=arlo_id,
                activity_phase=activity_phase,
                kind="policy_deny",
                summary=f"blocked {tool_name}: {reason}",
                payload_json={"tool_input": input_data.get("tool_input", {})},
                mcp_system=(spec.system.value if spec else None),
                action=tool_name,
                result="deny",
                policy_deny=True,
            )

        output: SyncHookJSONOutput = {
            "hookSpecificOutput": PreToolUseHookSpecificOutput(
                hookEventName="PreToolUse",
                permissionDecision=decision,  # type: ignore[typeddict-item]
                permissionDecisionReason=reason or "authorized by policy",
            )
        }
        return output

    return _hook


def build_posttooluse_hook(
    *, arlo_id: str, activity_phase: str, on_result: Callable[[str, dict], None] | None = None
) -> Callable[[PostToolUseHookInput, str | None, HookContext], Awaitable[SyncHookJSONOutput]]:
    """Audit-append every tool call that actually ran (SAD §2 PostToolUse).

    `on_result` (optional) is invoked synchronously with `(tool_name, tool_response)`
    so a caller (e.g. `execute_approved`) can track failures without a second
    round-trip through the audit log.
    """

    async def _hook(
        input_data: PostToolUseHookInput, _tool_use_id: str | None, _context: HookContext
    ) -> SyncHookJSONOutput:
        tool_name = input_data["tool_name"]
        spec = lookup_by_qualified_tool(tool_name)
        response = input_data.get("tool_response")

        if on_result is not None:
            try:
                on_result(tool_name, response if isinstance(response, dict) else {"raw": response})
            except Exception:
                logger.exception("on_result callback failed for %s", tool_name)

        try:
            response_summary = json.dumps(_redact(response), default=str)[:2000]
        except (TypeError, ValueError):
            response_summary = str(response)[:2000]

        await _audit(
            arlo_id=arlo_id,
            activity_phase=activity_phase,
            kind="mcp_call",
            summary=f"{tool_name} completed",
            payload_json={"tool_input": input_data.get("tool_input", {}), "result": response_summary},
            mcp_system=(spec.system.value if spec else None),
            action=tool_name,
            result="success",
            policy_deny=False,
        )
        return {}

    return _hook


def build_hooks(
    *,
    arlo_id: str,
    activity_phase: str,
    read_phase: Phase | None,
    writes_enabled: bool = False,
    allowed_write_tools: frozenset[str] = frozenset(),
    is_halted: Callable[[], bool] | None = None,
    on_result: Callable[[str, dict], None] | None = None,
) -> dict:
    """Convenience: full `hooks=` dict for `ClaudeAgentOptions` (SAD §2 runtime notes)."""
    return {
        "PreToolUse": [
            HookMatcher(
                hooks=[
                    build_pretooluse_hook(
                        arlo_id=arlo_id,
                        activity_phase=activity_phase,
                        read_phase=read_phase,
                        writes_enabled=writes_enabled,
                        allowed_write_tools=allowed_write_tools,
                        is_halted=is_halted,
                    )
                ]
            )
        ],
        "PostToolUse": [
            HookMatcher(
                hooks=[
                    build_posttooluse_hook(
                        arlo_id=arlo_id, activity_phase=activity_phase, on_result=on_result
                    )
                ]
            )
        ],
    }
