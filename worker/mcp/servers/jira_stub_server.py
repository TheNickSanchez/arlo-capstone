"""Jira MCP stub server (SAD AD-10; PRD §3.4 Jira authorized actions).

Run as `python -m worker.mcp.servers.jira_stub_server` over stdio. Exposes
exactly the PRD §3.4 Jira actions: one read tool and the three write tools
(each still requires the caller to have already passed HITL approval — this
server does not enforce phase; that is `worker.pep`'s job on the Claude side,
and the smoke-test Activity calls this tool directly and deliberately,
outside the agent's tool loop; see `worker/activities/test_comment.py`).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from mcp.server.mcpserver import MCPServer

app = MCPServer(name="jira-stub")

_SEED: dict[str, Any] = {
    "tickets": {
        "JIRA-102": {
            "ticket_key": "JIRA-102",
            "summary": "MacBook Pro failing FileVault compliance check",
            "description": "Device reports FileVault disabled after macOS upgrade; Jamf smart group flags non-compliant.",
            "status": "Open",
            "assignee": "service-desk@example.com",
            "app_name": "filevault",
            "platform": "macOS",
            "comments": [],
        },
        "JIRA-88": {
            "ticket_key": "JIRA-88",
            "summary": "Node.js LTS runtime missing from PATH after Jamf policy run",
            "description": "Post-install script cannot resolve /opt/homebrew/bin/node under Jamf's clean root PATH.",
            "status": "Open",
            "assignee": "service-desk@example.com",
            "app_name": "node",
            "platform": "macOS",
            "comments": [],
        },
    }
}


def _store() -> dict[str, Any]:
    from worker.mcp.servers.fixtures import load

    return load("jira", _SEED)


def _save(data: dict[str, Any]) -> None:
    from worker.mcp.servers.fixtures import save

    save("jira", data)


@app.tool()
def jira_get_ticket(ticket_key: str) -> dict[str, Any]:
    """Read ticket context: title, description, status, assignee (PRD §3.4 Jira read)."""
    from worker.mcp.jira_cloud import get_ticket, live_jira_configured

    if live_jira_configured():
        return get_ticket(ticket_key)
    data = _store()
    ticket = data["tickets"].get(ticket_key)
    if ticket is None:
        return {"found": False, "ticket_key": ticket_key}
    return {"found": True, **ticket}


@app.tool()
def jira_post_comment(ticket_key: str, body: str) -> dict[str, Any]:
    """Publish a discovery/proposal summary comment onto the ticket (write; post-HITL only)."""
    from worker.mcp.jira_cloud import live_jira_configured, post_comment

    if live_jira_configured():
        return post_comment(ticket_key, body)
    data = _store()
    ticket = data["tickets"].setdefault(
        ticket_key,
        {"ticket_key": ticket_key, "summary": "", "description": "", "status": "Open", "comments": []},
    )
    comment = {"body": body, "at": datetime.now(UTC).isoformat()}
    ticket["comments"].append(comment)
    _save(data)
    return {"ok": True, "ticket_key": ticket_key, "comment": comment}


@app.tool()
def jira_transition_ticket(ticket_key: str, status: str) -> dict[str, Any]:
    """Move the ticket to a new workflow status (write; post-HITL only)."""
    from worker.mcp.jira_cloud import live_jira_configured

    if live_jira_configured():
        return {"ok": False, "reason": "live Jira transition is not enabled in this slice"}
    data = _store()
    ticket = data["tickets"].get(ticket_key)
    if ticket is None:
        return {"ok": False, "reason": "unknown ticket"}
    previous = ticket["status"]
    ticket["status"] = status
    _save(data)
    return {"ok": True, "ticket_key": ticket_key, "previous_status": previous, "status": status}


@app.tool()
def jira_close_ticket(ticket_key: str) -> dict[str, Any]:
    """Close the ticket (write; post-HITL only, and only after Validation success)."""
    return jira_transition_ticket(ticket_key=ticket_key, status="Closed")


if __name__ == "__main__":
    app.run(transport="stdio")
