"""File-backed fixture store shared by the local stdio stub MCP servers.

Not a database: a small JSON document per vendor system under
`ARLO_MCP_FIXTURES_DIR` (default `<repo>/.data/mcp_fixtures`). Good enough to
let a capstone demo or `scripts/test_pipeline.py` observe the effect of a
"write" tool call (e.g. a posted Jira comment) across separate stdio
subprocess invocations, without pretending to be a real vendor system.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _fixtures_dir() -> Path:
    configured = os.environ.get("ARLO_MCP_FIXTURES_DIR")
    path = Path(configured) if configured else _REPO_ROOT / ".data" / "mcp_fixtures"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load(system: str, seed: dict[str, Any]) -> dict[str, Any]:
    path = _fixtures_dir() / f"{system}.json"
    if not path.exists():
        save(system, seed)
        return json.loads(json.dumps(seed))  # deep copy
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        save(system, seed)
        return json.loads(json.dumps(seed))


def save(system: str, data: dict[str, Any]) -> None:
    path = _fixtures_dir() / f"{system}.json"
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(data, indent=2, default=str))
    tmp_path.replace(path)
