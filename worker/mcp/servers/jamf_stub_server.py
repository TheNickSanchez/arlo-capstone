"""Jamf MCP stub server (SAD AD-10; PRD §3.4 Jamf authorized actions — Apple endpoints).

Run as `python -m worker.mcp.servers.jamf_stub_server` over stdio.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from mcp.server.mcpserver import MCPServer

app = MCPServer(name="jamf-stub")

_SEED: dict[str, Any] = {
    "devices": {
        "MBP-04471": {
            "compliant": False,
            "failed_checks": ["FileVault disabled"],
            "platform": "macOS",
            "last_checkin": "2026-08-31T10:00:00Z",
        },
        "MBP-03390": {
            "compliant": False,
            "failed_checks": ["PATH missing /opt/homebrew/bin for root scripts"],
            "platform": "macOS",
            "last_checkin": "2026-08-31T09:15:00Z",
        },
    },
    "applied_profiles": [],
    "catalog": {
        "policies": ["FileVault-Enforce", "Gatekeeper-Required"],
        "smart_groups": ["FileVault-NonCompliant", "macOS-Managed"],
        "scripts": ["install-node.sh"],
        "extension_attributes": ["HomebrewVersion"],
    },
}


def _store() -> dict[str, Any]:
    from worker.mcp.servers.fixtures import load

    return load("jamf", _SEED)


def _save(data: dict[str, Any]) -> None:
    from worker.mcp.servers.fixtures import save

    save("jamf", data)


@app.tool()
def jamf_read_compliance(asset_tag: str) -> dict[str, Any]:
    """Read device compliance status and failed policy/smart-group flags (read)."""
    data = _store()
    device = data["devices"].get(asset_tag)
    catalog = data.get("catalog") or _SEED["catalog"]
    if device is None:
        return {"found": False, "asset_tag": asset_tag, "catalog": catalog}
    return {"found": True, "asset_tag": asset_tag, "catalog": catalog, **device}


@app.tool()
def jamf_fetch_logs(asset_tag: str, limit: int = 20) -> dict[str, Any]:
    """Fetch recent device logs for root-cause evidence (read)."""
    data = _store()
    device = data["devices"].get(asset_tag, {})
    checks = device.get("failed_checks", [])
    logs = [f"{asset_tag}: policy check failed — {reason}" for reason in checks][:limit]
    return {"asset_tag": asset_tag, "logs": logs}


@app.tool()
def jamf_apply_profile(asset_tag: str, profile_id: str) -> dict[str, Any]:
    """Apply an approved configuration profile or script (write; post-HITL only)."""
    data = _store()
    device = data["devices"].setdefault(asset_tag, {"compliant": False, "failed_checks": [], "platform": "macOS"})
    device["compliant"] = True
    device["failed_checks"] = []
    device["last_checkin"] = datetime.now(UTC).isoformat()
    record = {"asset_tag": asset_tag, "profile_id": profile_id, "applied_at": device["last_checkin"]}
    data["applied_profiles"].append(record)
    _save(data)
    return {"ok": True, **record}


if __name__ == "__main__":
    app.run(transport="stdio")
