"""Canonical JSON hashing for proposal identity (SAD §2, §4; PRD FR-P0-05 AC4).

`proposal_hash` is the identity of a frozen proposal. Approve/Reject must supply
the same hash the API returned on the detail read, or the request is rejected
with 409 (stale proposal) and no Temporal Signal is sent (SAD §4).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_hash(payload: dict[str, Any]) -> str:
    """Sort keys, compact-encode, and sha256 a JSON-serializable payload.

    Deterministic across processes and Python versions: `json.dumps` with
    `sort_keys=True` and no whitespace, encoded as UTF-8, hashed with sha256.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def proposal_hash(proposal: dict[str, Any]) -> str:
    """Hash the proposal body only (excludes `proposal_hash` itself if present)."""
    body = {k: v for k, v in proposal.items() if k != "proposal_hash"}
    return canonical_json_hash(body)
