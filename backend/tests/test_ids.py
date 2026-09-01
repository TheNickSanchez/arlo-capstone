"""Instance id / workflow id correspondence (SAD §1)."""

from __future__ import annotations

from backend.app.domain.ids import format_arlo_id, is_valid_arlo_id, parse_arlo_id, workflow_id_for


def test_format_and_parse() -> None:
    assert format_arlo_id(675) == "ARLO-675"
    assert parse_arlo_id("ARLO-675") == 675
    assert is_valid_arlo_id("ARLO-675")
    assert not is_valid_arlo_id("arlo-675")


def test_workflow_id_is_lowercase_display_id() -> None:
    assert workflow_id_for("ARLO-675") == "arlo-675"
