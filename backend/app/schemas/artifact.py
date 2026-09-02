"""Run artifact API contracts (SAD §4 AD-17; `/runs/[arloId]` tabs)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ArtifactType = Literal["discovery_pack", "generated_script", "test_execution_log"]


class ArtifactOut(BaseModel):
    id: uuid.UUID
    arlo_id: str
    artifact_type: ArtifactType
    attempt: int
    content_text: str | None = None
    content_json: dict | None = None
    metadata_json: dict | None = None
    created_by_agent: str
    created_at: datetime


class ArtifactListResponse(BaseModel):
    items: list[ArtifactOut]
    total: int


class LatestArtifacts(BaseModel):
    """Newest row per type for `GET /instances/{arlo_id}` first paint."""

    discovery_pack: ArtifactOut | None = None
    generated_script: ArtifactOut | None = None
    test_execution_log: ArtifactOut | None = None


class GeneratedScriptPayload(BaseModel):
    language: Literal["zsh", "powershell"]
    filename: str
    contents: str
    changelog: str = ""
    platform: str | None = None


class TestExecutionLogPayload(BaseModel):
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    policy_id: int = 1460
    event: str = "arlo_test"
    command: str = ""
    script_id: str | None = None
    ok: bool = False
    script_artifact_id: str | None = None
    attempt: int = 0
