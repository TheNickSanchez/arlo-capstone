"""Intune MCP stub server (SAD AD-10, AD-12; PRD §3.4 Intune authorized actions).

Run as `python -m worker.mcp.servers.intune_stub_server` over stdio.
`intune_sync_device_status` is a read-side refresh, not a remediation
(SAD AD-12) — it never appears in a write `allowed_tools` set.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from mcp.server.mcpserver import MCPServer

app = MCPServer(name="intune-stub")

_SEED: dict[str, Any] = {
    "devices": {
        "WIN-88213": {
            "compliant": False,
            "failed_checks": ["BitLocker policy not applied"],
            "platform": "Windows",
            "last_synced": "2026-08-31T08:00:00Z",
        }
    },
    "applied_policies": [],
    "catalog": {
        "policies": ["BitLocker-Enforce", "Windows-Update-Ring"],
        "groups": ["Windows-Managed", "BitLocker-NonCompliant"],
        "scripts": ["remediate-bitlocker.ps1"],
        "extension_attributes": [],
    },
}


def _store() -> dict[str, Any]:
    from worker.mcp.servers.fixtures import load

    return load("intune", _SEED)


def _save(data: dict[str, Any]) -> None:
    from worker.mcp.servers.fixtures import save

    save("intune", data)


@app.tool()
def intune_read_compliance(device_id: str) -> dict[str, Any]:
    """Read device compliance and policy posture (read)."""
    data = _store()
    device = data["devices"].get(device_id)
    catalog = data.get("catalog") or _SEED["catalog"]
    if device is None:
        return {"found": False, "device_id": device_id, "catalog": catalog}
    return {"found": True, "device_id": device_id, "catalog": catalog, **device}


@app.tool()
def intune_sync_device(device_id: str) -> dict[str, Any]:
    """Read-side refresh of the latest device/compliance view (SAD AD-12: not a remediation)."""
    data = _store()
    device = data["devices"].get(device_id)
    catalog = data.get("catalog") or _SEED["catalog"]
    if device is None:
        return {"found": False, "device_id": device_id, "catalog": catalog}
    device["last_synced"] = datetime.now(UTC).isoformat()
    _save(data)
    return {"found": True, "device_id": device_id, "catalog": catalog, **device}


@app.tool()
def intune_apply_policy(device_id: str, policy_id: str) -> dict[str, Any]:
    """Apply an approved policy or remediation (write; post-HITL only)."""
    data = _store()
    device = data["devices"].setdefault(device_id, {"compliant": False, "failed_checks": [], "platform": "Windows"})
    device["compliant"] = True
    device["failed_checks"] = []
    device["last_synced"] = datetime.now(UTC).isoformat()
    record = {"device_id": device_id, "policy_id": policy_id, "applied_at": device["last_synced"]}
    data["applied_policies"].append(record)
    _save(data)
    return {"ok": True, **record}


if __name__ == "__main__":
    app.run(transport="stdio")
