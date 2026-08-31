"""Webhook ingress (SAD §4). Implement signature verify + Signal in @backend.eng.

POST /api/v1/webhooks/jira
POST /api/v1/webhooks/servicenow

P1 auto-spawn is out of MVP. Webhook-to-Signal is the wake mechanism when enabled.
Never Signal without HMAC verification.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])
