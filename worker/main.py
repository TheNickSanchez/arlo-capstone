"""Temporal Worker entrypoint (SAD §2, §4; adapter-claude-agent-sdk).

Registers `ArloRemediationWorkflow` and its Activities on task queue
`arlo-activities`. Must run with `AAMAD_TARGET_RUNTIME=claude-agent-sdk`
(compose/scripts pin this); `worker.sdk_env.claude_sdk_environ()` is what
threads that and the Anthropic credentials into each Activity's Claude Agent
SDK subprocess, not this entrypoint's own process env.
"""

from __future__ import annotations

import asyncio
import logging
import os

from temporalio.client import Client
from temporalio.worker import Worker

from backend.app.config import settings
from worker.activities.execute_approved import execute_approved
from worker.activities.generate_proposal import generate_proposal
from worker.activities.inspect_and_comment import inspect_and_comment
from worker.activities.investigate import investigate
from worker.activities.lifecycle import mark_failed
from worker.activities.post_proposal_comment import post_proposal_comment
from worker.activities.test_comment import post_smoke_test_comment
from worker.activities.validate_and_close import validate_and_close
from worker.mcp.jira_cloud import live_jira_configured
from worker.workflows.remediation import ArloRemediationWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("arlo.worker")

ACTIVITIES = (
    investigate,
    inspect_and_comment,
    generate_proposal,
    post_proposal_comment,
    execute_approved,
    validate_and_close,
    post_smoke_test_comment,
    mark_failed,
)


async def _run() -> None:
    if settings.aamad_target_runtime != "claude-agent-sdk":
        logger.warning(
            "AAMAD_TARGET_RUNTIME=%s (expected claude-agent-sdk for this worker build)",
            settings.aamad_target_runtime,
        )
    if live_jira_configured():
        os.environ["ATLASSIAN_SITE_NAME"] = settings.live_jira_site()
        os.environ["ATLASSIAN_EMAIL"] = settings.live_jira_email()
        os.environ["ATLASSIAN_API_TOKEN"] = settings.live_jira_api_token()
        logger.info("live Jira Cloud enabled site=%s", settings.live_jira_site())
    elif settings.arlo_jira_analysis_only or settings.arlo_jira_beta_prod:
        logger.warning(
            "Jira lifecycle mode is set but live Jira credentials are missing "
            "(ARLO_JIRA_ANALYSIS_ONLY=%s ARLO_JIRA_BETA_PROD=%s)",
            settings.arlo_jira_analysis_only,
            settings.arlo_jira_beta_prod,
        )

    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    worker = Worker(
        client,
        task_queue=settings.arlo_task_queue,
        workflows=[ArloRemediationWorkflow],
        activities=ACTIVITIES,
        max_concurrent_activities=settings.arlo_max_concurrent_runs,
    )
    logger.info(
        "ArloRemediationWorkflow worker starting task_queue=%s temporal=%s",
        settings.arlo_task_queue,
        settings.temporal_address,
    )
    await worker.run()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
