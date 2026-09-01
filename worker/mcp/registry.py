"""MCP server config registry for Claude Agent SDK Activities (SAD §6, AD-10).

Builds the `mcp_servers` dict passed into `ClaudeAgentOptions`. Transport is
resolved per vendor system from settings: a `<SYSTEM>_MCP_URL` selects
HTTP/SSE (production/shared tenant), a `<SYSTEM>_MCP_STDIO_CMD` selects a
local stdio stub (capstone fixtures), and if neither is set the system falls
back to the in-repo stub server module so Investigation never silently runs
with zero tools during local development.

Fail closed (SAD §6): if a vendor system that appears in the requested tool
set has no resolvable config, callers must raise rather than start a Claude
session missing that server.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from claude_agent_sdk.types import McpServerConfig, McpSSEServerConfig, McpStdioServerConfig

from backend.app.config import settings
from backend.app.domain.actions import McpSystem

# Local stub server modules, run as `python -m <module>` over stdio, used when
# no live MCP endpoint or explicit stdio command is configured (dev/demo).
STUB_MODULE_BY_SYSTEM: dict[McpSystem, str] = {
    McpSystem.JIRA: "worker.mcp.servers.jira_stub_server",
    McpSystem.SERVICENOW: "worker.mcp.servers.servicenow_stub_server",
    McpSystem.JAMF: "worker.mcp.servers.jamf_stub_server",
    McpSystem.INTUNE: "worker.mcp.servers.intune_stub_server",
}


@dataclass(frozen=True)
class VendorMcpEnv:
    url: str
    token: str
    stdio_cmd: str


def resolve_vendor_env(system: McpSystem) -> VendorMcpEnv:
    return {
        McpSystem.JIRA: VendorMcpEnv(settings.jira_mcp_url, settings.jira_mcp_token, settings.jira_mcp_stdio_cmd),
        McpSystem.SERVICENOW: VendorMcpEnv(
            settings.snow_mcp_url, settings.snow_mcp_token, settings.snow_mcp_stdio_cmd
        ),
        McpSystem.JAMF: VendorMcpEnv(settings.jamf_mcp_url, settings.jamf_mcp_token, settings.jamf_mcp_stdio_cmd),
        McpSystem.INTUNE: VendorMcpEnv(
            settings.intune_mcp_url, settings.intune_mcp_token, settings.intune_mcp_stdio_cmd
        ),
    }[system]


def build_server_config(system: McpSystem) -> McpServerConfig:
    """Resolve one vendor MCP server config from env (AD-10 transport rules)."""
    env = resolve_vendor_env(system)

    if env.url:
        config: McpSSEServerConfig = {"type": "sse", "url": env.url}
        if env.token:
            config["headers"] = {"Authorization": f"Bearer {env.token}"}
        return config

    if env.stdio_cmd:
        parts = env.stdio_cmd.split()
        return McpStdioServerConfig(type="stdio", command=parts[0], args=parts[1:])

    # Fall back to the in-repo fixture stub over stdio (same interpreter).
    module = STUB_MODULE_BY_SYSTEM[system]
    return McpStdioServerConfig(type="stdio", command=sys.executable, args=["-m", module])


def build_mcp_servers(systems: list[McpSystem]) -> dict[str, McpServerConfig]:
    """Build the `{server_name: config}` map for `ClaudeAgentOptions.mcp_servers`."""
    return {system.value: build_server_config(system) for system in systems}
