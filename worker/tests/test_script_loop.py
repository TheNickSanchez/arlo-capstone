"""Policy 1460 test-loop helpers (SAD AD-18)."""

from __future__ import annotations

from backend.app.domain.workflow_contracts import proposal_has_jamf_test_actions
from worker.activities.write_script import fallback_script


def test_fallback_script_macos_zsh() -> None:
    script = fallback_script(platform="macOS")
    assert script.language == "zsh"
    assert "zsh" in script.contents or script.filename.endswith(".sh")


def test_fallback_refactor_strips_fail_marker() -> None:
    prior = "#!/bin/zsh\necho ARLO_TEST_FAIL\n"
    script = fallback_script(
        platform="macOS",
        prior_script=prior,
        test_log={"exit_code": 1, "stderr": "arlo_test failed"},
    )
    assert "ARLO_TEST_FAIL" not in script.contents
    assert "refactored" in script.changelog.lower() or "refactored" in script.contents


def test_proposal_has_jamf_test_actions_pure() -> None:
    assert proposal_has_jamf_test_actions(
        {
            "write_actions": [
                {"system": "jamf", "action_type": "execute_test_policy", "target_ids": ["1460"]},
            ]
        }
    )
    assert not proposal_has_jamf_test_actions({"write_actions": []})
    assert not proposal_has_jamf_test_actions({})
