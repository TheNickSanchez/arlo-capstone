-- SAD §4 logical schema contract. Authoritative implementation is the Alembic
-- revision at backend/migrations/versions/0001_initial_schema.py (generated
-- from the ORM models in backend/app/models/). This file is documentation;
-- keep it in sync by hand when the schema changes.
-- Do not store secrets in any column. Redact payload_json.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE SEQUENCE IF NOT EXISTS arlo_instance_seq START WITH 675 INCREMENT BY 1;

-- users: id, username, password hash or IdP subject, created_at
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT,
    idp_subject     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- instances: arlo_id PK, ticket mapping, status, proposal, workflow_id, timestamps, created_by
CREATE TABLE IF NOT EXISTS instances (
    arlo_id         TEXT PRIMARY KEY,
    ticket_system   TEXT NOT NULL CHECK (ticket_system IN ('jira', 'servicenow')),
    ticket_key      TEXT NOT NULL,
    status          TEXT NOT NULL,
    proposal_json   JSONB,
    proposal_hash   TEXT,
    workflow_id     TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      UUID REFERENCES users (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS instances_active_ticket_uidx
    ON instances (ticket_system, ticket_key)
    WHERE status NOT IN ('Done', 'Rejected', 'Failed', 'Cancelled');

-- approvals: actor, action, frozen list, matching proposal_hash
CREATE TABLE IF NOT EXISTS approvals (
    id                  UUID PRIMARY KEY,
    arlo_id             TEXT NOT NULL REFERENCES instances (arlo_id),
    action              TEXT NOT NULL CHECK (action IN ('approve', 'reject', 'cancel')),
    actor_id            UUID NOT NULL REFERENCES users (id),
    at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    proposal_hash       TEXT,
    frozen_actions_json JSONB,
    rationale           TEXT
);

-- audit_events: append-only mirrored log for the dashboard
CREATE TABLE IF NOT EXISTS audit_events (
    id              BIGSERIAL PRIMARY KEY,
    arlo_id         TEXT NOT NULL REFERENCES instances (arlo_id),
    at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    phase           TEXT NOT NULL,
    kind            TEXT NOT NULL,
    summary         TEXT NOT NULL,
    payload_json    JSONB,
    mcp_system      TEXT,
    action          TEXT,
    result          TEXT,
    policy_deny     BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS audit_events_arlo_at_idx ON audit_events (arlo_id, at);

-- learned_patterns: Shared Operational Memory (SAD AD-13)
CREATE TABLE IF NOT EXISTS learned_patterns (
    id                          UUID PRIMARY KEY,
    app_name                    TEXT NOT NULL,
    platform                    TEXT NOT NULL,
    pattern_type                TEXT NOT NULL,
    problem_description         TEXT NOT NULL,
    problem_description_hash    TEXT NOT NULL,
    solution_payload            JSONB NOT NULL,
    created_by_arlo_id          TEXT NOT NULL,
    success_count               INT NOT NULL DEFAULT 1,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_verified_at            TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS learned_patterns_app_name_idx ON learned_patterns (app_name);
CREATE INDEX IF NOT EXISTS learned_patterns_platform_idx ON learned_patterns (platform);
CREATE INDEX IF NOT EXISTS learned_patterns_natural_key_idx
    ON learned_patterns (app_name, platform, pattern_type);

-- kb_articles: Vector Knowledge Base (SAD AD-14, pgvector)
CREATE TABLE IF NOT EXISTS kb_articles (
    id              UUID PRIMARY KEY,
    title           TEXT NOT NULL,
    category        TEXT NOT NULL,
    content         TEXT NOT NULL,
    embedding       VECTOR(1536),
    metadata_json   JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS kb_articles_category_idx ON kb_articles (category);
CREATE INDEX IF NOT EXISTS kb_articles_embedding_ivfflat_idx
    ON kb_articles USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
