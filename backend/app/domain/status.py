"""Instance status machine (PRD §4.1, SAD §6 state machine).

UI/API/Workflow/DB vocabulary must match exactly (SAD correspondence rule).
Illegal transitions are product bugs and must raise, not silently clamp.
"""

from __future__ import annotations

from enum import StrEnum


class InstanceStatus(StrEnum):
    """Exact PRD §4.1 / UI-P0-03 vocabulary. Do not rename."""

    INVESTIGATING = "Investigating"
    AWAITING_APPROVAL = "Awaiting Approval"
    EXECUTING = "Executing"
    DONE = "Done"
    REJECTED = "Rejected"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


TERMINAL_STATUSES: frozenset[InstanceStatus] = frozenset(
    {
        InstanceStatus.DONE,
        InstanceStatus.REJECTED,
        InstanceStatus.FAILED,
        InstanceStatus.CANCELLED,
    }
)

# Legal forward edges only (SAD §6 state machine). No edge re-enters a terminal
# status. No edge skips Awaiting Approval into Executing without going through
# the approval gate (that check is enforced by the approval record, not here).
# Investigating → Done is only for the Jira-analysis-only slice (inspect +
# comment, no HITL/execution). Full remediation still cannot skip HITL into
# Executing.
_ALLOWED_TRANSITIONS: dict[InstanceStatus, frozenset[InstanceStatus]] = {
    InstanceStatus.INVESTIGATING: frozenset(
        {
            InstanceStatus.AWAITING_APPROVAL,
            InstanceStatus.DONE,
            InstanceStatus.FAILED,
            InstanceStatus.CANCELLED,
        }
    ),
    InstanceStatus.AWAITING_APPROVAL: frozenset(
        {
            InstanceStatus.EXECUTING,
            InstanceStatus.REJECTED,
            InstanceStatus.CANCELLED,
            InstanceStatus.FAILED,
        }
    ),
    InstanceStatus.EXECUTING: frozenset(
        {InstanceStatus.DONE, InstanceStatus.FAILED, InstanceStatus.CANCELLED}
    ),
    InstanceStatus.DONE: frozenset(),
    InstanceStatus.REJECTED: frozenset(),
    InstanceStatus.FAILED: frozenset(),
    InstanceStatus.CANCELLED: frozenset(),
}


class IllegalTransitionError(ValueError):
    """Raised when code attempts to move an instance across a forbidden edge."""

    def __init__(self, current: InstanceStatus, target: InstanceStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(f"illegal transition: {current.value} -> {target.value}")


def is_terminal(status: InstanceStatus) -> bool:
    return status in TERMINAL_STATUSES


def assert_transition_allowed(current: InstanceStatus, target: InstanceStatus) -> None:
    """Raise IllegalTransitionError unless `current -> target` is a legal edge."""
    if target not in _ALLOWED_TRANSITIONS.get(current, frozenset()):
        raise IllegalTransitionError(current, target)
