"""Resolve `convert_markdown_to_adf` for outbound Jira comments.

Prefers the shared Atlassian MCP converter when that file exists on this
machine (operator path). Falls back to the vendored copy so CI, Compose,
and other hosts stay reproducible.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import Any

_EXTERNAL = Path("/Users/nick.sanchez/mcp-servers/atlassian_mcp/shared/adf_converter.py")


def _load_convert_markdown_to_adf() -> Callable[[str], dict[str, Any]]:
    if _EXTERNAL.is_file():
        spec = importlib.util.spec_from_file_location("atlassian_mcp_adf_converter", _EXTERNAL)
        if spec is not None and spec.loader is not None:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module.convert_markdown_to_adf
    from worker.mcp.adf_converter import convert_markdown_to_adf as vendored

    return vendored


convert_markdown_to_adf = _load_convert_markdown_to_adf()
