"""Validation Activity structured-output contract (SAD §2 step 8; PRD Open Q6).

`passed=False` (or omitted) means "do not close" — the PRD default is no
close/transition on partial success, so a mismatched or missing `passed`
must fail closed, not open.
"""

from __future__ import annotations

from pydantic import BaseModel


class ValidationResult(BaseModel):
    passed: bool
    notes: str = ""
    closed_ticket: bool = False
