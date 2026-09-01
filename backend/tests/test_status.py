"""Unit tests for instance status machine (SAD §6; PRD §4.1)."""

from __future__ import annotations

import pytest

from backend.app.domain.status import (
    IllegalTransitionError,
    InstanceStatus,
    assert_transition_allowed,
    is_terminal,
)


def test_prd_status_vocabulary() -> None:
    assert [s.value for s in InstanceStatus] == [
        "Investigating",
        "Awaiting Approval",
        "Executing",
        "Done",
        "Rejected",
        "Failed",
        "Cancelled",
    ]


def test_happy_path_edges() -> None:
    assert_transition_allowed(InstanceStatus.INVESTIGATING, InstanceStatus.AWAITING_APPROVAL)
    assert_transition_allowed(InstanceStatus.AWAITING_APPROVAL, InstanceStatus.EXECUTING)
    assert_transition_allowed(InstanceStatus.EXECUTING, InstanceStatus.DONE)


def test_analysis_only_may_complete_from_investigating() -> None:
    assert_transition_allowed(InstanceStatus.INVESTIGATING, InstanceStatus.DONE)


def test_cannot_skip_hitl() -> None:
    with pytest.raises(IllegalTransitionError):
        assert_transition_allowed(InstanceStatus.INVESTIGATING, InstanceStatus.EXECUTING)


def test_terminal_has_no_exits() -> None:
    for status in (InstanceStatus.DONE, InstanceStatus.REJECTED, InstanceStatus.FAILED, InstanceStatus.CANCELLED):
        assert is_terminal(status)
        with pytest.raises(IllegalTransitionError):
            assert_transition_allowed(status, InstanceStatus.INVESTIGATING)
