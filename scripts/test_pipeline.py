#!/usr/bin/env python3
"""End-to-end tests of the production backend pipeline.

Default (smoke): one test Activity posting a fixed Jira comment.

    python scripts/test_pipeline.py
    python scripts/test_pipeline.py --ticket-id JIRA-102

Jira-only analysis (live Cloud): inspect ticket, Claude analysis, comment, stop.

    python scripts/test_pipeline.py --analysis --ticket-id CPE-4297

Requires `ARLO_JIRA_ANALYSIS_ONLY=true`, live Atlassian credentials, API + worker restart.

Discovery + proposal (beta-prod): investigate MDM, post ADF proposal comment, wait at HITL.

    python scripts/test_pipeline.py --beta-prod --ticket-id CPE-4297

Requires `ARLO_JIRA_BETA_PROD=true`, API + worker restart. Instance stays Awaiting Approval.

Prerequisites (from repo root):

    docker compose up -d postgres temporal
    python scripts/seed_admin.py
    uvicorn backend.app.main:app --port 8000
    python -m worker.main
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from sqlalchemy import select

from backend.app.config import settings
from backend.app.db.migrate import run_upgrade_head
from backend.app.db.session import session_scope
from backend.app.models.audit_event import AuditEvent
from backend.app.models.instance import Instance
from backend.app.services.users import upsert_local_user
from worker.activities.test_comment import COMMENT_TEMPLATE

_DEFAULT_API = "http://localhost:8000"
_POLL_SECONDS = 60
_ANALYSIS_POLL_SECONDS = 180
_POLL_INTERVAL = 1.0


class PipelineError(RuntimeError):
    pass


def _api_base() -> str:
    return settings.next_public_api_base_url.rstrip("/") or _DEFAULT_API


async def _wait_ready(client: httpx.AsyncClient) -> None:
    deadline = time.monotonic() + 30
    last_error = "api not reachable"
    while time.monotonic() < deadline:
        try:
            health = await client.get("/health")
            if health.status_code != 200:
                last_error = f"/health {health.status_code}"
                await asyncio.sleep(_POLL_INTERVAL)
                continue
            ready = await client.get("/ready")
            if ready.status_code == 200:
                return
            last_error = f"/ready {ready.status_code} {ready.text}"
        except httpx.HTTPError as exc:
            last_error = str(exc)
        await asyncio.sleep(_POLL_INTERVAL)
    raise PipelineError(
        f"API not ready at {_api_base()} ({last_error}). "
        "Start postgres, temporal, the API, and the worker first."
    )


async def _login(client: httpx.AsyncClient) -> str:
    if not settings.arlo_admin_password:
        raise PipelineError(
            "ARLO_ADMIN_PASSWORD is empty. Set it in `.env` and run `python scripts/seed_admin.py`."
        )
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": settings.arlo_admin_username, "password": settings.arlo_admin_password},
    )
    if response.status_code != 200:
        raise PipelineError(
            f"login failed ({response.status_code}): {response.text}. "
            "Run `python scripts/seed_admin.py` after setting ARLO_ADMIN_PASSWORD."
        )
    token = response.json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return token


async def _spawn(client: httpx.AsyncClient, ticket_id: str) -> dict:
    response = await client.post(
        "/api/v1/instances",
        json={"ticket_system": "jira", "ticket_id": ticket_id},
    )
    if response.status_code == 409:
        raise PipelineError(
            f"active instance already mapped to jira:{ticket_id} ({response.text}). "
            "Cancel it or pass --ticket-id with a unique key."
        )
    if response.status_code != 201:
        raise PipelineError(f"POST /api/v1/instances failed ({response.status_code}): {response.text}")
    return response.json()


async def _poll_audit(arlo_id: str, kind: str, *, timeout: float = _POLL_SECONDS) -> AuditEvent:
    deadline = time.monotonic() + timeout
    last_kinds: list[str] = []
    last_status = None
    while time.monotonic() < deadline:
        async with session_scope() as session:
            instance = await session.get(Instance, arlo_id)
            if instance is None:
                raise PipelineError(f"instance {arlo_id} missing from PostgreSQL after spawn")
            last_status = instance.status
            rows = (
                await session.execute(
                    select(AuditEvent)
                    .where(AuditEvent.arlo_id == arlo_id)
                    .order_by(AuditEvent.at.asc())
                )
            ).scalars().all()
            last_kinds = [row.kind for row in rows]
            for row in rows:
                if row.kind == kind:
                    return row
        await asyncio.sleep(_POLL_INTERVAL)
    raise PipelineError(
        f"timed out waiting for {kind} audit event on {arlo_id} "
        f"(status={last_status} seen kinds={last_kinds}). Is `python -m worker.main` running?"
    )


async def _poll_smoke_audit(arlo_id: str) -> AuditEvent:
    return await _poll_audit(arlo_id, "smoke_test")


def _fixture_comment_bodies(ticket_id: str) -> list[str]:
    path = _ROOT / ".data" / "mcp_fixtures" / "jira.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return []
    ticket = data.get("tickets", {}).get(ticket_id, {})
    return [str(c.get("body", "")) for c in ticket.get("comments", [])]


async def run(ticket_id: str, *, analysis: bool, beta_prod: bool = False) -> None:
    print("==> running Alembic migrations")
    run_upgrade_head()

    if beta_prod:
        if not settings.arlo_jira_beta_prod:
            raise PipelineError(
                "ARLO_JIRA_BETA_PROD is false. Set it true in `.env` and restart the API + worker."
            )
        if settings.claude_model == "claude-sonnet-4-5":
            print(
                "==> warning: CLAUDE_MODEL=claude-sonnet-4-5 is often blocked by the hub; "
                "prefer claude-sonnet-4-5-20250929"
            )
    elif analysis:
        if not settings.arlo_jira_analysis_only:
            raise PipelineError(
                "ARLO_JIRA_ANALYSIS_ONLY is false. Set it true in `.env` and restart the API + worker."
            )
        if not settings.live_jira_configured():
            raise PipelineError(
                "live Jira credentials missing. Set ATLASSIAN_SITE_NAME, ATLASSIAN_EMAIL, "
                "and ATLASSIAN_API_TOKEN (names only; do not paste tokens into chat)."
            )
        if settings.claude_model == "claude-sonnet-4-5":
            print(
                "==> warning: CLAUDE_MODEL=claude-sonnet-4-5 is often blocked by the hub; "
                "prefer claude-sonnet-4-5-20250929"
            )

    if settings.arlo_admin_password:
        print("==> ensuring admin user exists")
        async with session_scope() as session:
            await upsert_local_user(
                session,
                username=settings.arlo_admin_username,
                password=settings.arlo_admin_password,
            )

    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as client:
        print(f"==> waiting for API {_api_base()}")
        await _wait_ready(client)
        await _login(client)
        print(f"==> POST /api/v1/instances ticket_id={ticket_id}")
        created = await _spawn(client, ticket_id)

    arlo_id = created["arlo_id"]
    status = created["status"]
    print(f"==> spawned {arlo_id} status={status}")
    if status != "Investigating":
        raise PipelineError(f"expected Investigating, got {status!r}")

    async with session_scope() as session:
        instance = await session.get(Instance, arlo_id)
        if instance is None:
            raise PipelineError(f"{arlo_id} was not persisted")
        if instance.ticket_system != "jira" or instance.ticket_key != ticket_id:
            raise PipelineError("instance ticket mapping mismatch")
        if not instance.workflow_id:
            raise PipelineError("workflow_id missing on instance row")

    if beta_prod:
        print("==> waiting for generate_proposal + post_proposal_comment (HITL pause)")
        await _poll_audit(arlo_id, "proposal_generated", timeout=_ANALYSIS_POLL_SECONDS)
        event = await _poll_audit(arlo_id, "jira_proposal_comment", timeout=_ANALYSIS_POLL_SECONDS)
        payload = event.payload_json or {}
        print(f"==> audit jira_proposal_comment result={event.result} summary={event.summary}")
        if event.result != "success":
            raise PipelineError(f"proposal comment did not post: {event.summary} payload={payload}")
        async with session_scope() as session:
            instance = await session.get(Instance, arlo_id)
            if instance is None or instance.status != "Awaiting Approval":
                raise PipelineError(
                    f"expected Awaiting Approval after beta-prod, "
                    f"got {instance.status if instance else None!r}"
                )
            if not instance.proposal_hash:
                raise PipelineError("proposal_hash missing after generate_proposal")
        print(
            f"OK beta-prod paused at HITL instance={arlo_id} ticket={ticket_id} "
            f"comment_id={payload.get('comment_id')} url={payload.get('url')}"
        )
        return

    if analysis:
        print("==> waiting for inspect_and_comment (Jira read + analysis comment)")
        event = await _poll_audit(arlo_id, "jira_analysis", timeout=_ANALYSIS_POLL_SECONDS)
        payload = event.payload_json or {}
        print(f"==> audit jira_analysis result={event.result} summary={event.summary}")
        if event.result != "success":
            raise PipelineError(f"analysis comment did not post: {event.summary} payload={payload}")
        async with session_scope() as session:
            instance = await session.get(Instance, arlo_id)
            if instance is None or instance.status != "Done":
                raise PipelineError(
                    f"expected Done after analysis, got {instance.status if instance else None!r}"
                )
            analysis_json = instance.proposal_json or {}
        if not analysis_json.get("comment_body") and not analysis_json.get("what_needs_to_get_done"):
            raise PipelineError("instance is missing analysis payload after inspect_and_comment")
        print(
            f"OK analysis posted instance={arlo_id} ticket={ticket_id} "
            f"comment_id={payload.get('comment_id')} url={payload.get('url')}"
        )
        return

    print("==> waiting for Temporal smoke-test Activity")
    event = await _poll_smoke_audit(arlo_id)
    expected_body = COMMENT_TEMPLATE.format(arlo_id=arlo_id)
    payload = event.payload_json or {}
    print(f"==> audit smoke_test result={event.result} summary={event.summary}")

    if event.result != "success" or not payload.get("ok"):
        raise PipelineError(
            f"smoke test did not post a Jira comment: {event.summary} payload={payload}"
        )

    bodies = _fixture_comment_bodies(ticket_id)
    if bodies and expected_body not in bodies:
        raise PipelineError(
            f"Jira fixture for {ticket_id} is missing expected comment {expected_body!r}"
        )
    if bodies:
        print(f"==> Jira stub comment confirmed on {ticket_id}")
    else:
        print("==> Jira comment confirmed via MCP/audit payload (no local fixture file)")

    print(f"OK pipeline connected instance={arlo_id} ticket={ticket_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ARLO backend pipeline smoke / analysis test")
    parser.add_argument(
        "--analysis",
        action="store_true",
        help="Jira-only inspect + analysis comment (live Cloud). Stops before HITL/execution.",
    )
    parser.add_argument(
        "--beta-prod",
        action="store_true",
        help="Discovery + proposal comment, then pause at Awaiting Approval.",
    )
    parser.add_argument(
        "--ticket-id",
        default=None,
        help="Jira key to map. Default JIRA-PIPE-<epoch> (smoke) or CPE-4297 (--analysis/--beta-prod).",
    )
    args = parser.parse_args()
    if args.analysis and args.beta_prod:
        print("FAIL use either --analysis or --beta-prod, not both", file=sys.stderr)
        sys.exit(2)
    ticket_id = args.ticket_id or (
        "CPE-4297" if (args.analysis or args.beta_prod) else f"JIRA-PIPE-{int(time.time())}"
    )
    try:
        asyncio.run(run(ticket_id, analysis=args.analysis, beta_prod=args.beta_prod))
    except PipelineError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
