"""Proposal hash stability (SAD §4; PRD FR-P0-05 AC4)."""

from __future__ import annotations

from backend.app.domain.hashing import canonical_json_hash, proposal_hash


def test_canonical_hash_is_key_order_independent() -> None:
    a = canonical_json_hash({"b": 1, "a": 2})
    b = canonical_json_hash({"a": 2, "b": 1})
    assert a == b
    assert len(a) == 64


def test_proposal_hash_excludes_self() -> None:
    body = {"ticket_key": "JIRA-102", "write_actions": []}
    hashed = proposal_hash({**body, "proposal_hash": "should-be-ignored"})
    assert hashed == proposal_hash(body)
    assert hashed != canonical_json_hash({**body, "proposal_hash": "should-be-ignored"})
