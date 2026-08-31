"""Environment mapping for Claude Agent SDK so LiteLLM routing is not dropped.

@backend.eng MUST pass this dict into ClaudeAgentOptions(env=...) when constructing
ClaudeSDKClient. Do not construct the client here (no agent logic in setup).
"""

from __future__ import annotations

import os


def claude_sdk_environ() -> dict[str, str]:
    """Copy process env and force Anthropic + runtime keys used by the SDK subprocess."""
    env = dict(os.environ)
    env["AAMAD_TARGET_RUNTIME"] = "claude-agent-sdk"
    env["ANTHROPIC_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY", "")
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    if base_url:
        env["ANTHROPIC_BASE_URL"] = base_url
    return env
