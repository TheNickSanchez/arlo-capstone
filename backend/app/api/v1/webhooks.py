"""Webhook ingress (SAD §4, §6). HMAC verify; map to Signal only.

POST /api/v1/webhooks/jira
POST /api/v1/webhooks/servicenow

P1 auto-spawn from ticket-created events is out of MVP.
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.db.session import get_session
from backend.app.domain.errors import UnauthenticatedError, ValidationError
from backend.app.services import instances as instances_service
from backend.app.services.audit import append_audit_event

router = APIRouter(tags=["webhooks"])


def _verify_hmac(secret: str, body: bytes, signature_header: str | None) -> None:
    if not secret:
        raise UnauthenticatedError("webhook secret not configured; refusing unsigned ingress")
    if not signature_header:
        raise UnauthenticatedError("missing webhook signature header")
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    if not hmac.compare_digest(expected, provided):
        raise UnauthenticatedError("webhook signature mismatch")


def _extract_approval_payload(body: dict[str, Any]) -> dict[str, Any] | None:
    """Recognize only an explicit `arlo_decision` block; ignore other webhook noise."""
    decision = body.get("arlo_decision")
    if not isinstance(decision, dict):
        return None
    required = {"arlo_id", "action", "actor_id", "proposal_hash"}
    if not required.issubset(decision.keys()):
        return None
    if decision["action"] not in ("approve", "reject"):
        return None
    return decision


async def _handle_webhook(
    request: Request,
    session: AsyncSession,
    *,
    system: str,
    secret: str,
    signature_header: str | None,
) -> dict[str, Any]:
    raw_body = await request.body()
    _verify_hmac(secret, raw_body, signature_header)

    try:
        body = await request.json()
    except Exception as exc:
        raise ValidationError(f"invalid JSON webhook body: {exc}") from exc

    decision = _extract_approval_payload(body)
    if decision is None:
        return {"ok": True, "action": "ignored"}

    arlo_id = str(decision["arlo_id"])
    actor_id = uuid.UUID(str(decision["actor_id"]))
    proposal_hash = str(decision["proposal_hash"])

    await append_audit_event(
        session,
        arlo_id=arlo_id,
        phase="webhook",
        kind="webhook_received",
        summary=f"{system} webhook delivered an {decision['action']} decision",
        mcp_system=system,
    )

    if decision["action"] == "approve":
        instance = await instances_service.approve_instance(
            session,
            arlo_id=arlo_id,
            actor_id=actor_id,
            proposal_hash=proposal_hash,
            rationale=f"approved via {system} webhook",
        )
    else:
        instance = await instances_service.reject_instance(
            session,
            arlo_id=arlo_id,
            actor_id=actor_id,
            proposal_hash=proposal_hash,
            reason=f"rejected via {system} webhook",
        )

    return {"ok": True, "arlo_id": instance.arlo_id, "status": instance.status}


@router.post("/webhooks/jira")
async def jira_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await _handle_webhook(
        request,
        session,
        system="jira",
        secret=settings.jira_webhook_secret,
        signature_header=x_hub_signature_256,
    )


@router.post("/webhooks/servicenow")
async def servicenow_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await _handle_webhook(
        request,
        session,
        system="servicenow",
        secret=settings.snow_webhook_secret,
        signature_header=x_hub_signature_256,
    )
