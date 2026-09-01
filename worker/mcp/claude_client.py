"""ClaudeSDKClient session factory (SAD AD-2, AD-8; adapter-claude-agent-sdk).

Every Activity opens a new `ClaudeSDKClient`, runs one prompt, and closes the
client (and therefore every MCP stdio/SSE session bound into
`ClaudeAgentOptions.mcp_servers`) when the Activity ends. SDK sessions are
never resumed across the HITL Signal wait — Temporal Workflow Id is the
durable session.

MCP transport (HTTP/SSE vs stdio) is resolved by `worker.mcp.registry` and
passed in as `mcp_servers`. This module does not open MCP connections itself.
"""

from __future__ import annotations

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ResultMessage

from backend.app.config import settings
from worker.sdk_env import claude_sdk_environ


class ClaudeQueryError(RuntimeError):
    """Raised when a ClaudeSDKClient session ends in error or with no ResultMessage."""


def build_claude_options(**kwargs: object) -> ClaudeAgentOptions:
    """Least-privilege defaults for every Activity session (SAD §2 runtime notes).

    `tools=[]` disables Claude Code built-in filesystem/shell tools. MCP tools
    remain available through `mcp_servers` + `allowed_tools`. `dontAsk` means
    the CLI will not prompt a human — `PreToolUse` PEP is the permission gate.
    """
    kwargs.setdefault("tools", [])
    kwargs.setdefault("strict_mcp_config", True)
    kwargs.setdefault("permission_mode", "dontAsk")
    kwargs.setdefault("env", claude_sdk_environ())
    kwargs.setdefault("model", settings.claude_model)
    return ClaudeAgentOptions(**kwargs)  # type: ignore[arg-type]


async def run_claude_session(*, prompt: str, options: ClaudeAgentOptions) -> ResultMessage:
    """Open a ClaudeSDKClient, send `prompt`, collect the ResultMessage, close.

    Matches SAD AD-8: "new ClaudeSDKClient per Activity invocation; close on
    Activity completion. Do not resume SDK session across HITL."
    """
    result: ResultMessage | None = None
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            if isinstance(message, ResultMessage):
                result = message
    if result is None:
        raise ClaudeQueryError("ClaudeSDKClient produced no ResultMessage (transport ended early)")
    if result.is_error:
        raise ClaudeQueryError(f"ClaudeSDKClient failed (subtype={result.subtype}): {result.result}")
    return result
