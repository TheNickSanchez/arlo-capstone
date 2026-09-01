"""MCP integration layer (SAD §2, §6 "MCP connection model").

The Worker is the only MCP *client*. Two consumption patterns live here:

1. `worker.mcp.registry` builds `claude_agent_sdk` `McpServerConfig` entries
   (stdio or HTTP/SSE) for binding into `ClaudeAgentOptions.mcp_servers`.
2. `worker.mcp.claude_client` constructs a per-Activity `ClaudeSDKClient`
   (SAD AD-8: open/close with the Activity; never resume across HITL).
3. `worker.mcp.raw_client` is a plain (non-Claude) MCP client session used by
   deterministic Activities that call a single tool directly — e.g. the
   pipeline smoke-test Activity (`worker/activities/test_comment.py`).

`worker.mcp.servers.*` are local stdio stub servers (SAD AD-10: "Local stubs
... Capstone fixtures when live tenants are unavailable"). They implement the
same tool surface a production Jira/ServiceNow/Jamf/Intune MCP server would
expose for PRD §3.4 authorized actions, backed by an in-memory fixture store
instead of a real vendor tenant.
"""
