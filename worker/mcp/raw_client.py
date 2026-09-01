"""Plain MCP client session for deterministic (non-Claude) Activities.

Used where an Activity must call exactly one known tool without an LLM
tool-selection loop in between — e.g. the pipeline smoke-test Activity
(`worker/activities/test_comment.py`). Sharing this with the Claude-driven
Activities would blur the PEP boundary (SAD AD-9: writes are gated by
`allowed_tools` + `PreToolUse`, which only applies inside a `ClaudeSDKClient`
session), so this client intentionally bypasses the SDK entirely and is used
only for calls that do not need model reasoning.

Supports the same transport resolution as `worker.mcp.registry` (HTTP/SSE,
stdio command, or the in-repo fixture stub), via the official `mcp` Python
SDK client primitives.
"""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client

from backend.app.domain.actions import McpSystem
from worker.mcp.registry import STUB_MODULE_BY_SYSTEM, resolve_vendor_env


class McpToolCallError(RuntimeError):
    """Raised when a tool call returns `isError` or the server is unreachable."""


@asynccontextmanager
async def mcp_session(system: McpSystem) -> AsyncIterator[ClientSession]:
    env = resolve_vendor_env(system)

    if env.url:
        headers = {"Authorization": f"Bearer {env.token}"} if env.token else None
        async with sse_client(env.url, headers=headers) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
        return

    if env.stdio_cmd:
        parts = env.stdio_cmd.split()
        params = StdioServerParameters(command=parts[0], args=parts[1:])
    else:
        module = STUB_MODULE_BY_SYSTEM[system]
        params = StdioServerParameters(command=sys.executable, args=["-m", module])

    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        yield session


async def call_tool(system: McpSystem, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Open a short-lived MCP session, call one tool, and close it (SAD §6 lifecycle)."""
    async with mcp_session(system) as session:
        result = await session.call_tool(tool_name, arguments)
        if result.is_error:
            text = "; ".join(
                block.text for block in result.content if hasattr(block, "text")
            )
            raise McpToolCallError(f"{system.value}.{tool_name} failed: {text or 'unknown error'}")
        if result.structured_content is not None:
            return dict(result.structured_content)
        texts = [block.text for block in result.content if hasattr(block, "text")]
        return {"text": "\n".join(texts)}
