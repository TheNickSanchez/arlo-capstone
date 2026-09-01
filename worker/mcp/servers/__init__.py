"""Local stdio stub MCP servers (SAD AD-10: capstone fixtures for MVP demo/testing).

Each module here is a standalone MCP server process (`python -m
worker.mcp.servers.<name>`) exposing exactly the PRD §3.4 authorized actions
for one vendor system, backed by a JSON fixture file instead of a live
tenant. These are Build-time integration stand-ins, not the product's MCP
server implementation (SAD: "MCP server implementations are out of scope for
this SAD beyond transport and authorized-action binding").

Fixture state is intentionally file-backed (`worker/mcp/servers/fixtures.py`)
rather than purely in-memory: each Activity spawns a fresh stdio subprocess
(AD-10 lifecycle), so state must survive across process boundaries for the
smoke test and demo runs to be observable.
"""
