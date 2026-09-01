"""Evidence pack contract (SAD §2 step 2; PRD FR-P0-02).

Output of the `investigate` Activity's Retrieval Phase: ticket + asset +
device context, plus the automatically-injected `learned_patterns` matches
and `kb_search` hits, plus any declared gaps (a missing read is a gap, not a
fabricated fact — SAD §2: "do not invent device state").
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.app.schemas.proposal import EvidenceGap, KbCitation, PatternCitation


class EvidencePack(BaseModel):
    ticket_key: str
    app_name: str | None = None
    platform: str | None = None
    ticket_summary: str = ""
    ticket_description: str = ""
    assets: list[dict] = Field(default_factory=list)
    devices: list[dict] = Field(default_factory=list)
    change_requests: list[dict] = Field(default_factory=list)
    matched_patterns: list[PatternCitation] = Field(default_factory=list)
    kb_hits: list[KbCitation] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    evidence_gaps: list[EvidenceGap] = Field(default_factory=list)
