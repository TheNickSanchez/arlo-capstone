"""Executive Jira comment contract (analysis-only and beta-prod)."""

from __future__ import annotations

from backend.app.schemas.analysis import TicketAnalysis
from backend.app.schemas.proposal import ProposalPayload
from worker.activities.comment_format import (
    EXECUTIVE_TITLE,
    executive_comment_from_analysis,
    executive_comment_from_proposal,
    render_executive_comment,
    strip_redundant_branding,
)


def test_executive_comment_has_required_sections() -> None:
    body = render_executive_comment(
        impact="CVE-2024-0001 on 12 macOS endpoints; unpatched runtime exposure.",
        actions=["Deploy the Jamf policy after the change window", "Validate version inventory"],
        questions=["Confirm the Saturday maintenance window"],
    )
    assert body.startswith(EXECUTIVE_TITLE)
    assert "**Business Impact & Risk**" in body
    assert "**Recommended Action Plan**" in body
    assert "**Open Questions**" in body
    assert "ARLO Analysis for" not in body
    assert "* Deploy the Jamf policy after the change window" in body


def test_strips_repetitive_branding() -> None:
    raw = "ARLO Analysis for ARLO-677\n\nNeed a patch window."
    assert "ARLO-677" not in strip_redundant_branding(raw)
    assert "Need a patch window." in strip_redundant_branding(raw)


def test_analysis_fallback_uses_structured_fields() -> None:
    analysis = TicketAnalysis(
        ticket_key="CPE-4297",
        summary="Outdated Ruby on managed Macs.",
        what_needs_to_get_done=["Add an EA for Ruby version"],
        unknowns=["Target Ruby version?"],
        comment_body="ARLO Analysis for ARLO-680\nSomething informal.",
    )
    body = executive_comment_from_analysis(analysis)
    assert body.startswith(EXECUTIVE_TITLE)
    assert "ARLO Analysis for ARLO-680" not in body
    assert "Outdated Ruby" in body


def test_proposal_comment_prefers_model_template() -> None:
    proposal = ProposalPayload(
        ticket_key="JIRA-102",
        comment_body=(
            f"{EXECUTIVE_TITLE}\n\n**Business Impact & Risk**\nFileVault is off.\n\n"
            "**Recommended Action Plan**\n* Re-apply the profile\n\n"
            "**Open Questions**\n* When can we reboot?"
        ),
    )
    assert executive_comment_from_proposal(proposal).startswith(EXECUTIVE_TITLE)
