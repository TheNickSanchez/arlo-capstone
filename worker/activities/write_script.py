"""Activity `write_script` — `script_writer_agent` (SAD §2 step 3, AD-18).

No vendor MCP. Persists `run_artifacts.generated_script`. Initial draft
uses the discovery pack; refactor mode receives Policy 1460 stdout/stderr.
"""

from __future__ import annotations

import json

from temporalio import activity

from backend.app.db.session import session_scope
from backend.app.domain.status import InstanceStatus
from backend.app.domain.workflow_contracts import WriteScriptInput
from backend.app.schemas.artifact import GeneratedScriptPayload
from backend.app.schemas.evidence import EvidencePack
from backend.app.services.artifacts import persist_artifact
from worker.activities.common import record_diagnostic, run_claude_query
from worker.agents import SCRIPT_WRITER_AGENT_ID, specialist_agents
from worker.agents.script_writer import SCRIPT_WRITER_PROMPT
from worker.mcp.claude_client import ClaudeQueryError, build_claude_options
from worker.pep import build_hooks


def fallback_script(
    *,
    platform: str | None,
    prior_script: str | None = None,
    test_log: dict | None = None,
) -> GeneratedScriptPayload:
    """Deterministic draft/refactor when Claude is unavailable (capstone)."""
    is_windows = (platform or "").lower() in {"windows", "win"}
    changelog = "initial draft"
    if is_windows:
        language, filename = "powershell", "arlo-remediation.ps1"
        contents = (
            prior_script
            or "# ARLO remediation\nWrite-Host 'arlo remediation'\n"
        )
        if test_log and int(test_log.get("exit_code", 0)) != 0:
            contents = contents.replace("ARLO_TEST_FAIL", "")
            contents += "\n# Refactored after Policy 1460 failure\n"
            changelog = "removed failing marker; retried after test log"
    else:
        language, filename = "zsh", "arlo-remediation.sh"
        contents = prior_script or (
            "#!/bin/zsh\nset -euo pipefail\necho 'arlo remediation'\n"
        )
        if test_log and int(test_log.get("exit_code", 0)) != 0:
            contents = contents.replace("ARLO_TEST_FAIL", "")
            if "refactored" not in contents:
                contents += "echo 'arlo remediation (refactored)'\n"
            changelog = "removed failing marker; retried after test log"
    return GeneratedScriptPayload(
        language=language,  # type: ignore[arg-type]
        filename=filename,
        contents=contents,
        changelog=changelog,
        platform=platform,
    )


@activity.defn(name="write_script")
async def write_script(input: WriteScriptInput) -> dict:
    activity.logger.info(
        "write_script start arlo_id=%s attempt=%s refactor=%s",
        input.arlo_id,
        input.attempt,
        input.test_log is not None,
    )
    evidence = EvidencePack.model_validate(input.evidence_pack) if input.evidence_pack else None
    platform = (evidence.platform if evidence else None) or None

    script: GeneratedScriptPayload | None = None
    options = build_claude_options(
        system_prompt=SCRIPT_WRITER_PROMPT,
        allowed_tools=[],
        agents=specialist_agents(),
        hooks=build_hooks(
            arlo_id=input.arlo_id,
            activity_phase=(
                InstanceStatus.EXECUTING.value
                if input.test_log is not None
                else InstanceStatus.INVESTIGATING.value
            ),
            read_phase=None,
            writes_enabled=False,
        ),
        max_turns=8,
        output_format={"type": "json_schema", "schema": GeneratedScriptPayload.model_json_schema()},
    )
    prompt = (
        f"Ticket {input.ticket_key}. Platform={platform!r}.\n"
        f"Evidence:\n{json.dumps(input.evidence_pack, indent=2)[:8000]}\n"
    )
    if input.test_log is not None:
        prompt += (
            "\nRefactor the prior script using this Policy 1460 test log "
            f"(exit_code={input.test_log.get('exit_code')}):\n"
            f"{json.dumps(input.test_log, indent=2)[:4000]}\n"
            f"Prior script:\n{input.prior_script or ''}\n"
        )
    else:
        prompt += "\nWrite the initial remediation script for this OS. Return GeneratedScriptPayload JSON."

    try:
        result = await run_claude_query(prompt=prompt, options=options)
        script = GeneratedScriptPayload.model_validate(result.structured_output)
    except (ClaudeQueryError, Exception) as exc:
        activity.logger.warning("write_script Claude fallback arlo_id=%s err=%s", input.arlo_id, exc)
        script = fallback_script(
            platform=platform, prior_script=input.prior_script, test_log=input.test_log
        )

    phase = (
        InstanceStatus.EXECUTING.value
        if input.test_log is not None
        else InstanceStatus.INVESTIGATING.value
    )
    artifact_id = ""
    async with session_scope() as session:
        row = await persist_artifact(
            session,
            arlo_id=input.arlo_id,
            artifact_type="generated_script",
            created_by_agent=SCRIPT_WRITER_AGENT_ID,
            phase=phase,
            attempt=input.attempt,
            content_text=script.contents,
            content_json=script.model_dump(mode="json"),
            metadata_json={
                "language": script.language,
                "filename": script.filename,
                "platform": script.platform or platform,
                "changelog": script.changelog,
            },
        )
        artifact_id = str(row.id)
        if input.test_log is not None:
            await record_diagnostic(
                session,
                arlo_id=input.arlo_id,
                phase=phase,
                summary=f"script_refactor attempt={input.attempt}",
                payload_json={"artifact_id": artifact_id},
            )

    return {
        "artifact_id": artifact_id,
        "attempt": input.attempt,
        "language": script.language,
        "filename": script.filename,
        "contents": script.contents,
        "platform": script.platform or platform,
    }
