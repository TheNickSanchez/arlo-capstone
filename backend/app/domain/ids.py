"""Instance id / Workflow id correspondence (SAD §1 correspondence rule).

`ARLO-<n>` = Temporal Workflow Id (lowercase `arlo-<n>`) = `instances.arlo_id`
= UI row key. Keep the numeric parse/format pair here so no other module
reimplements it differently.
"""

from __future__ import annotations

import re

_ARLO_ID_RE = re.compile(r"^ARLO-(\d+)$")


def format_arlo_id(n: int) -> str:
    return f"ARLO-{n}"


def workflow_id_for(arlo_id: str) -> str:
    """Workflow id is the lowercase form of the display id (SAD §1)."""
    return arlo_id.lower()


def parse_arlo_id(arlo_id: str) -> int | None:
    match = _ARLO_ID_RE.match(arlo_id)
    return int(match.group(1)) if match else None


def is_valid_arlo_id(arlo_id: str) -> bool:
    return _ARLO_ID_RE.match(arlo_id) is not None
