"""Instance request/response payloads (SAD §4 API Architecture)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from backend.app.schemas.artifact import LatestArtifacts
from backend.app.schemas.proposal import ProposalPayload

TicketSystem = Literal["jira", "servicenow"]


class InstanceCreateRequest(BaseModel):
    """`POST /api/v1/instances` body (SAD §4)."""

    ticket_system: TicketSystem
    ticket_id: str = Field(min_length=1)

    @field_validator("ticket_id")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if len(trimmed) < 1:
            raise ValueError("ticket_id must not be blank")
        return trimmed


class InstanceCreateResponse(BaseModel):
    arlo_id: str
    status: str


class ApprovalSummary(BaseModel):
    action: str
    actor_id: str
    at: datetime
    rationale: str | None = None


class InstanceSummary(BaseModel):
    """One grid row (PRD UI-P0-02)."""

    arlo_id: str
    ticket_system: TicketSystem
    ticket_key: str
    status: str
    created_at: datetime
    updated_at: datetime


class InstanceListResponse(BaseModel):
    items: list[InstanceSummary]
    total: int
    limit: int
    offset: int


class InstanceDetail(BaseModel):
    """Instance detail (PRD FR-P0-03, UI-P0-04/05)."""

    arlo_id: str
    ticket_system: TicketSystem
    ticket_key: str
    status: str
    created_at: datetime
    updated_at: datetime
    proposal: ProposalPayload | None = None
    proposal_hash: str | None = None
    latest_approval: ApprovalSummary | None = None
    latest_artifacts: LatestArtifacts | None = None


class AuditEventOut(BaseModel):
    at: datetime
    arlo_id: str
    phase: str
    kind: str
    summary: str
    mcp_system: str | None = None
    action: str | None = None
    result: str | None = None
    policy_deny: bool = False


class AuditListResponse(BaseModel):
    items: list[AuditEventOut]


class ApproveRequest(BaseModel):
    proposal_hash: str
    rationale: str | None = None


class RejectRequest(BaseModel):
    proposal_hash: str
    reason: str | None = None


class CancelRequest(BaseModel):
    reason: str | None = None


class DecisionResponse(BaseModel):
    arlo_id: str
    status: str
