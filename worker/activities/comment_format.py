"""Executive Jira comment Markdown (converted to ADF at the Jira client)."""

from __future__ import annotations

import re

from backend.app.schemas.analysis import TicketAnalysis
from backend.app.schemas.proposal import ProposalPayload

EXECUTIVE_TITLE = "[Arlo] Investigation Summary"
_BRANDING_RE = re.compile(
    r"^\s*(\*{0,2})?(ARLO|Arlo)\s+Analysis\s+for\s+ARLO-\d+",
    re.IGNORECASE,
)


def strip_redundant_branding(body: str) -> str:
    """Drop self-referential lines such as 'ARLO Analysis for ARLO-677'."""
    kept = [line for line in body.splitlines() if not _BRANDING_RE.match(line)]
    return "\n".join(kept).strip()


def render_executive_comment(
    *,
    impact: str,
    actions: list[str],
    questions: list[str],
) -> str:
    action_lines = [f"* {item.strip()}" for item in actions if item and item.strip()]
    question_lines = [f"* {item.strip()}" for item in questions if item and item.strip()]
    if not action_lines:
        action_lines = ["* Review the ticket evidence and confirm the remediation owner."]
    if not question_lines:
        question_lines = ["* Confirm the maintenance window and target versions."]
    impact_text = (impact or "").strip() or (
        "Impact is not yet quantified from the ticket evidence."
    )
    return (
        f"{EXECUTIVE_TITLE}\n\n"
        f"**Business Impact & Risk**\n"
        f"{impact_text}\n\n"
        f"**Recommended Action Plan**\n"
        + "\n".join(action_lines)
        + "\n\n"
        "**Open Questions**\n"
        + "\n".join(question_lines)
    )


def executive_comment_from_analysis(analysis: TicketAnalysis) -> str:
    body = strip_redundant_branding(analysis.comment_body.strip())
    if body.startswith(EXECUTIVE_TITLE):
        return body
    return render_executive_comment(
        impact=analysis.summary,
        actions=analysis.what_needs_to_get_done,
        questions=analysis.unknowns,
    )


def executive_comment_from_proposal(proposal: ProposalPayload) -> str:
    body = strip_redundant_branding((proposal.comment_body or "").strip())
    if body.startswith(EXECUTIVE_TITLE):
        return body
    impact = (
        proposal.residual_risk
        or proposal.solution_summary
        or " ".join(proposal.findings[:2])
    )
    actions = [
        f"{action.system}.{action.action_type}"
        + (f" → {', '.join(action.target_ids)}" if action.target_ids else "")
        for action in proposal.write_actions
    ]
    if not actions:
        actions = list(proposal.findings[:5])
    questions = [gap.reason for gap in proposal.evidence_gaps]
    return render_executive_comment(impact=impact, actions=actions, questions=questions)
