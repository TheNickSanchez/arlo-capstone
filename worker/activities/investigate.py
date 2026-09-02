"""Activity `investigate` — Retrieval Phase + Investigation (SAD §2 step 2).

Read-only. New `ClaudeSDKClient`-equivalent (`query()`) per invocation. Two
automatic pre-calls happen in plain Python *before* the first model turn so
their results can be injected into context (SAD: "Automatically ... Inject
both result sets into Claude prompt context"):
  (a) `learned_patterns` SELECT on `app_name` / `platform`.
  (b) `kb_search` with a ticket-derived query.
A blocking vendor **read** failure is a Diagnostic, not a fabricated fact —
this Activity must not invent device/ticket state (SAD §2 step 2).
"""

from __future__ import annotations

import json
import logging
import re

from sqlalchemy import or_, select
from temporalio import activity

from backend.app.config import settings
from backend.app.db.session import session_scope
from backend.app.domain.actions import McpSystem, Phase, read_tool_names
from backend.app.domain.status import InstanceStatus
from backend.app.domain.workflow_contracts import RemediationWorkflowInput
from backend.app.models.learned_pattern import LearnedPattern
from backend.app.schemas.evidence import EvidencePack
from backend.app.schemas.proposal import EvidenceGap, KbCitation, PatternCitation
from backend.app.services.artifacts import persist_artifact
from backend.app.services.audit import append_audit_event
from worker.activities.common import record_diagnostic, run_claude_query
from worker.agents import DISCOVERY_AGENT_ID, specialist_agents
from worker.mcp.claude_client import build_claude_options
from worker.mcp.kb_search_server import build_kb_search_server, kb_search_direct
from worker.mcp.raw_client import McpToolCallError, call_tool
from worker.mcp.registry import build_mcp_servers
from worker.pep import build_hooks

logger = logging.getLogger("arlo.worker.activities.investigate")

_INVESTIGATOR_SYSTEM_PROMPT = """You are `discovery_agent`, ARLO's read-only evidence gatherer \
(PRD FR-P0-02). Ground every claim in a tool result already shown to you or one you fetch now \
via your read-only MCP tools; never invent device, asset, or ticket state. If a system is \
unreachable or a fact is unavailable, record it as an entry in `evidence_gaps` instead of \
guessing. You may call `kb_search` again for follow-up queries if the initial results are \
insufficient. When you are done, return only the EvidencePack JSON — no prose outside the \
JSON payload."""

_BETA_PROD_INVESTIGATOR_ADDENDUM = """

This run is ARLO_JIRA_BETA_PROD (discovery and proposal lifecycle). In findings, explicitly:
1. Identify the platform: Apple/macOS → Jamf, Windows → Intune. Do not query the other MDM.
2. Report existing policies, smart groups, scripts, and Extension Attributes from the MDM catalog.
3. Name concrete asset gaps (example: "Ruby cannot be tracked via standard app versioning; \
custom Extension Attribute and new policy/script required").
4. Do not attempt any write. Endpoint mutation waits for human approval."""

_JAMF_PLATFORM_HINTS = ("mac", "macos", "osx", "ios", "ipad", "iphone", "apple", "jamf")
_INTUNE_PLATFORM_HINTS = ("win", "windows", "intune", "microsoft")
_ASSET_TAG_RE = re.compile(r"\b((?:MBP|WIN|LPT|MAC)-[A-Z0-9]+)\b", re.IGNORECASE)


def infer_platform(ticket: dict) -> str | None:
    explicit = ticket.get("platform")
    if explicit:
        return str(explicit)
    blob = " ".join(
        str(ticket.get(key) or "")
        for key in ("summary", "description", "issue_type", "labels")
    ).lower()
    if any(hint in blob for hint in _JAMF_PLATFORM_HINTS):
        return "macOS"
    if any(hint in blob for hint in _INTUNE_PLATFORM_HINTS):
        return "Windows"
    return None


def infer_asset_tag(ticket: dict, asset: dict | None) -> str | None:
    if asset and asset.get("asset_tag"):
        return str(asset["asset_tag"])
    blob = " ".join(
        str(ticket.get(key) or "")
        for key in ("summary", "description", "labels")
    )
    match = _ASSET_TAG_RE.search(blob)
    return match.group(1).upper() if match else None


async def _read_asset(ticket_key: str) -> dict | None:
    try:
        return await call_tool(McpSystem.SERVICENOW, "snow_read_asset", {"ticket_key": ticket_key})
    except McpToolCallError as exc:
        logger.warning("snow_read_asset failed for %s: %s", ticket_key, exc)
        return None


async def _read_device_compliance(platform: str | None, asset_tag: str | None) -> tuple[dict | None, list[str]]:
    """Best-effort MDM lookup; the fixture's platform vocabulary decides Jamf vs. Intune.

    Underspecified in PRD §3.4 (no explicit asset-tag -> MDM-system crosswalk),
    so a platform we cannot route is a declared gap, not a guess.
    """
    if not asset_tag:
        return None, ["no asset tag available to look up device compliance"]

    platform_l = (platform or "").lower()
    if any(hint in platform_l for hint in _JAMF_PLATFORM_HINTS):
        try:
            compliance = await call_tool(McpSystem.JAMF, "jamf_read_compliance", {"asset_tag": asset_tag})
            logs = await call_tool(McpSystem.JAMF, "jamf_fetch_logs", {"asset_tag": asset_tag})
            compliance["logs"] = logs.get("logs", [])
            return compliance, []
        except McpToolCallError as exc:
            return None, [f"jamf lookup failed for {asset_tag}: {exc}"]
    if any(hint in platform_l for hint in _INTUNE_PLATFORM_HINTS):
        try:
            compliance = await call_tool(McpSystem.INTUNE, "intune_read_compliance", {"device_id": asset_tag})
            return compliance, []
        except McpToolCallError as exc:
            return None, [f"intune lookup failed for {asset_tag}: {exc}"]
    return None, [f"no known MDM routing for platform={platform!r}"]


@activity.defn(name="investigate")
async def investigate(input: RemediationWorkflowInput) -> dict:
    arlo_id, ticket_key = input.arlo_id, input.ticket_key
    activity.logger.info("investigate start arlo_id=%s ticket=%s", arlo_id, ticket_key)

    gaps: list[EvidenceGap] = []
    ticket: dict = {}

    if input.ticket_system == "jira":
        ticket = await call_tool(McpSystem.JIRA, "jira_get_ticket", {"ticket_key": ticket_key})
        if not ticket.get("found", True):
            gaps.append(EvidenceGap(system="jira", reason=f"ticket {ticket_key} not found"))
    else:
        # PRD §3.4 has no ticket-content read tool for ServiceNow (only CHG/asset
        # reads) — a real gap in the authorized-action catalog, not a bug here.
        gaps.append(
            EvidenceGap(
                system="servicenow",
                reason="no ticket-content read tool authorized for ServiceNow in PRD §3.4",
            )
        )

    app_name = ticket.get("app_name")
    platform = infer_platform(ticket)

    # (a) learned_patterns retrieval — automatic, before the first model turn.
    matched_patterns: list[PatternCitation] = []
    if app_name or platform:
        async with session_scope() as session:
            conditions = [c for c in (LearnedPattern.app_name == app_name if app_name else None,
                                       LearnedPattern.platform == platform if platform else None) if c is not None]
            rows = (
                await session.execute(select(LearnedPattern).where(or_(*conditions)))
            ).scalars().all()
        matched_patterns = [
            PatternCitation(
                id=str(row.id), app_name=row.app_name, platform=row.platform, success_count=row.success_count
            )
            for row in rows
        ]
    else:
        gaps.append(EvidenceGap(system="learned_patterns", reason="ticket has no app_name/platform to match on"))

    # (b) kb_search automatic pre-call — direct Python call, not a model tool use.
    kb_query = " ".join(part for part in (ticket.get("summary"), ticket.get("description")) if part) or ticket_key
    kb_result = await kb_search_direct(query=kb_query, top_k=5)
    kb_hits = [
        KbCitation(id=hit["id"], title=hit["title"], category=hit.get("category"), score=hit.get("score"))
        for hit in kb_result.get("hits", [])
    ]
    if kb_result.get("gap"):
        gaps.append(EvidenceGap(system="kb", reason=str(kb_result["gap"])))

    asset = await _read_asset(ticket_key)
    assets = [asset] if asset and asset.get("found") else []
    if asset is None or not asset.get("found", False):
        gaps.append(EvidenceGap(system="servicenow", reason=f"no asset record for {ticket_key}"))

    asset_tag = infer_asset_tag(ticket, asset)
    device, device_gaps = await _read_device_compliance(platform, asset_tag)
    devices = [device] if device and device.get("found") else []
    gaps.extend(EvidenceGap(system="mdm", reason=g) for g in device_gaps)

    prefetched = EvidencePack(
        ticket_key=ticket_key,
        app_name=app_name,
        platform=platform,
        ticket_summary=str(ticket.get("summary", "")),
        ticket_description=str(ticket.get("description", "")),
        assets=assets,
        devices=devices,
        matched_patterns=matched_patterns,
        kb_hits=kb_hits,
        evidence_gaps=gaps,
    )

    system_prompt = _INVESTIGATOR_SYSTEM_PROMPT
    if input.jira_beta_prod:
        system_prompt = _INVESTIGATOR_SYSTEM_PROMPT + _BETA_PROD_INVESTIGATOR_ADDENDUM

    options = build_claude_options(
        system_prompt=system_prompt,
        allowed_tools=read_tool_names(Phase.INVESTIGATION),
        agents=specialist_agents(),
        mcp_servers={
            **build_mcp_servers([McpSystem.JIRA, McpSystem.SERVICENOW, McpSystem.JAMF, McpSystem.INTUNE]),
            "kb": build_kb_search_server(),
        },
        hooks=build_hooks(
            arlo_id=arlo_id,
            activity_phase=InstanceStatus.INVESTIGATING.value,
            read_phase=Phase.INVESTIGATION,
            writes_enabled=False,
        ),
        max_turns=settings.investigation_max_turns,
        output_format={"type": "json_schema", "schema": EvidencePack.model_json_schema()},
    )
    prompt = (
        "Pre-fetched evidence (already retrieved for you; do not re-fetch unless verifying "
        f"a specific detail):\n{json.dumps(prefetched.model_dump(mode='json'), indent=2)}\n\n"
        "Investigate ticket "
        f"{ticket_key} using this evidence and any additional read-only tool calls you judge "
        "necessary. Add concrete `findings` (short bullet strings) and merge in any additional "
        "`evidence_gaps` you discover. Return the complete EvidencePack JSON."
    )
    if input.jira_beta_prod:
        prompt += (
            " Beta-prod: identify Jamf vs Intune from the ticket, inspect the MDM catalog "
            "for prior policies/groups/scripts/EAs, and record every missing control as a gap."
        )

    try:
        result = await run_claude_query(prompt=prompt, options=options)
        evidence = EvidencePack.model_validate(result.structured_output)
    except Exception as exc:
        async with session_scope() as session:
            await record_diagnostic(
                session,
                arlo_id=arlo_id,
                phase=InstanceStatus.INVESTIGATING.value,
                summary=f"investigate failed: {exc}",
            )
        raise

    pack = evidence.model_dump(mode="json")
    async with session_scope() as session:
        await persist_artifact(
            session,
            arlo_id=arlo_id,
            artifact_type="discovery_pack",
            created_by_agent=DISCOVERY_AGENT_ID,
            phase=InstanceStatus.INVESTIGATING.value,
            attempt=0,
            content_json=pack,
            metadata_json={"ticket_key": ticket_key, "platform": evidence.platform},
        )
        await append_audit_event(
            session,
            arlo_id=arlo_id,
            phase=InstanceStatus.INVESTIGATING.value,
            kind="investigation_complete",
            summary=(
                f"evidence gathered: {len(evidence.findings)} findings, "
                f"{len(evidence.matched_patterns)} matched patterns, {len(evidence.kb_hits)} KB hits, "
                f"{len(evidence.evidence_gaps)} gaps"
            ),
        )

    return pack
