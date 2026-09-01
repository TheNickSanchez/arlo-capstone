"""Platform routing for Jamf vs Intune (no new MCP tools)."""

from __future__ import annotations

from worker.activities.investigate import infer_asset_tag, infer_platform


def test_macos_ticket_routes_to_jamf() -> None:
    assert infer_platform({"summary": "MacBook FileVault failed after Jamf policy"}) == "macOS"


def test_windows_ticket_routes_to_intune() -> None:
    assert infer_platform({"description": "BitLocker missing on Windows laptop"}) == "Windows"


def test_explicit_platform_wins() -> None:
    assert infer_platform({"platform": "macOS", "summary": "Windows mention"}) == "macOS"


def test_asset_tag_from_snow_and_ticket_text() -> None:
    assert infer_asset_tag({}, {"asset_tag": "MBP-04471"}) == "MBP-04471"
    assert infer_asset_tag({"summary": "Check WIN-88213 after reboot"}, None) == "WIN-88213"
    assert infer_asset_tag({"summary": "no device id"}, None) is None
