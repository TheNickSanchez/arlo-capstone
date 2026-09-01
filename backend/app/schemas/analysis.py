"""Ticket analysis contract for the Jira-only inspect slice."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TicketAnalysis(BaseModel):
    ticket_key: str
    summary: str = ""
    what_needs_to_get_done: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    comment_body: str = Field(
        default="",
        description=(
            "Executive Markdown for the Jira comment. Must start with "
            "'[Arlo] Investigation Summary' and use Business Impact & Risk, "
            "Recommended Action Plan, and Open Questions. Converted to ADF "
            "before jira_post_comment. No endpoint or ticket mutations besides this comment."
        ),
    )
