"""Smoke-test comment contract (operator verification path)."""

from __future__ import annotations

from worker.activities.test_comment import COMMENT_TEMPLATE


def test_comment_template_matches_operator_contract() -> None:
    body = COMMENT_TEMPLATE.format(arlo_id="ARLO-675")
    assert body == "[Arlo] Backend pipeline connected. Instance ARLO-675 initialized."
