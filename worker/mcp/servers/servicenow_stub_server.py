"""ServiceNow MCP stub server (SAD AD-10; PRD §3.4 ServiceNow authorized actions).

Run as `python -m worker.mcp.servers.servicenow_stub_server` over stdio.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from mcp.server.mcpserver import MCPServer

app = MCPServer(name="servicenow-stub")

_SEED: dict[str, Any] = {
    "assets": {
        "JIRA-102": {"asset_tag": "MBP-04471", "owner": "j.rivera@example.com", "model": "MacBook Pro 16 2023"},
        "JIRA-88": {"asset_tag": "MBP-03390", "owner": "a.chen@example.com", "model": "MacBook Pro 14 2022"},
    },
    "change_requests": {},
    "next_chg_number": 100042,
}


def _store() -> dict[str, Any]:
    from worker.mcp.servers.fixtures import load

    return load("servicenow", _SEED)


def _save(data: dict[str, Any]) -> None:
    from worker.mcp.servers.fixtures import save

    save("servicenow", data)


@app.tool()
def snow_check_chg(ticket_key: str) -> dict[str, Any]:
    """Check for an existing change request tracking this ticket (read)."""
    data = _store()
    existing = [chg for chg in data["change_requests"].values() if chg.get("ticket_key") == ticket_key]
    return {"ticket_key": ticket_key, "existing_change_requests": existing}


@app.tool()
def snow_read_asset(ticket_key: str) -> dict[str, Any]:
    """Read CI/asset data for the device tied to this ticket (read)."""
    data = _store()
    asset = data["assets"].get(ticket_key)
    if asset is None:
        return {"found": False, "ticket_key": ticket_key}
    return {"found": True, "ticket_key": ticket_key, **asset}


@app.tool()
def snow_create_chg(ticket_key: str, short_description: str) -> dict[str, Any]:
    """Create a new change request for tracking (write; post-HITL only)."""
    data = _store()
    chg_number = f"CHG{data['next_chg_number']}"
    data["next_chg_number"] += 1
    record = {
        "chg_number": chg_number,
        "ticket_key": ticket_key,
        "short_description": short_description,
        "created_at": datetime.now(UTC).isoformat(),
        "state": "New",
    }
    data["change_requests"][chg_number] = record
    _save(data)
    return {"ok": True, **record}


if __name__ == "__main__":
    app.run(transport="stdio")
