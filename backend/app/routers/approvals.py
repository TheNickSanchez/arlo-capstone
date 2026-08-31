"""Approvals helpers (SAD §4). HTTP paths live under /instances/{arlo_id}/approve|reject.

Persist approvals row before Temporal Signal. Stale proposal_hash → 409, no Signal.
Implement in @backend.eng.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["approvals"])
