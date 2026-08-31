-- SAD §4 logical schema contract. Alembic revisions owned by @backend.eng.
-- Do not store secrets in any column. Redact payload_json.

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
