"""Proposal contract (PRD FR-P0-03; SAD §2, §4).

`ProposalWriteAction` entries are the *frozen* enumerated writes: system,
action type (must resolve in `backend.app.domain.actions`), and target ids.
Nothing outside this list may execute after approval (PRD FR-P0-06 AC1).
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from backend.app.domain.actions import lookup


class ProposalWriteAction(BaseModel):
    system: str
    action_type: str
    target_ids: list[str] = Field(default_factory=list)

    @field_validator("action_type")
    @classmethod
    def _must_be_authorized(cls, action_type: str, info) -> str:
        system = info.data.get("system")
        if system and lookup(system, action_type) is None:
            raise ValueError(f"unauthorized action: {system}.{action_type} (PRD §3.4)")
        return action_type


class PatternCitation(BaseModel):
    kind: str = "learned_pattern"
    id: str
    app_name: str | None = None
    platform: str | None = None
    success_count: int | None = None


class KbCitation(BaseModel):
    kind: str = "kb_article"
    id: str
    title: str
    category: str | None = None
    score: float | None = None


class EvidenceGap(BaseModel):
    system: str
    reason: str


_PATTERN_TYPES = {"script_fix", "version_endpoint", "vendor_gotcha"}


class ProposalPayload(BaseModel):
    """Persisted verbatim on `instances.proposal_json`; identity = `proposal_hash`."""

    ticket_key: str
    targeted_assets: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    write_actions: list[ProposalWriteAction] = Field(default_factory=list)
    validation_checks: list[str] = Field(default_factory=list)
    residual_risk: str = ""
    evidence_gaps: list[EvidenceGap] = Field(default_factory=list)
    pattern_citations: list[PatternCitation] = Field(default_factory=list)
    kb_citations: list[KbCitation] = Field(default_factory=list)
    pattern_type: str | None = None
    """One of `learned_patterns.pattern_type` (SAD §4 AD-13: `script_fix` /
    `version_endpoint` / `vendor_gotcha`), set only when this fix is reusable
    across instances; null for one-off/ticket-specific remediations."""
    solution_summary: str = ""
    """Reusable fix description persisted to `learned_patterns.solution_payload`
    on Validation success (SAD §2 step 8). Empty when `pattern_type` is null."""
    comment_body: str = ""
    """Optional executive Markdown posted to Jira in beta-prod / proposal comment."""
    proposal_hash: str | None = None
    """Populated after `canonical_json_hash`; excluded from the hash input itself."""

    @field_validator("pattern_type")
    @classmethod
    def _known_pattern_type(cls, value: str | None) -> str | None:
        if value is not None and value not in _PATTERN_TYPES:
            raise ValueError(f"unknown pattern_type: {value} (SAD §4 AD-13)")
        return value
