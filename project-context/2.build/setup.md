# Setup: ARLO Phase 2 (Build)

**Document type:** AAMAD setup epic  
**Product:** ARLO — Automated Remediation Loop Orchestrator  
**Phase:** 2 Build  
**Owner persona:** `@project.mgr` (`project-mgr`)  
**Date:** 2026-08-31  
**Status:** Complete (scaffold + env + dependencies; no ARLO business logic)  
**Action:** `setup-project` + `install-dependencies` + `configure-env` + `document-setup`

## Purpose

Scaffold the repository layout, environment contract, Compose topology, and sequential Build-epic backlog for ARLO. Implementation of HITL, MCP writes, Temporal Workflows, and the dashboard belongs to downstream personas.

## Prerequisites

| Tool | Used in this setup | Notes |
|---|---|---|
| Python | 3.11.10 (project `.venv`) | `requires-python >=3.11`; Docker images pin `python:3.11-slim` |
| Node.js | v24.13.1 | Frontend scaffold; Docker image `node:22-alpine` |
| npm | 11.8.0 | `frontend/` |
| Docker | 29.7.2 present | Compose plugin may require Docker Desktop context; infra not started in this epic |
| `AAMAD_TARGET_RUNTIME` | **hardcoded `claude-agent-sdk`** | Must not remain unset (adapter-registry defaults to `crewai`) |

Required Define inputs present: `project-context/1.define/prd.md`, `project-context/1.define/sad.md`. Config: `aamad.config.yml` (`runtime.target: claude-agent-sdk`, `language.primary: python`, `security.require_security_assessment: true`).

## Repository layout

```
backend/                         FastAPI control plane (SAD §4)
  app/main.py                    Liveness `/health` only; empty routers mounted
  app/config.py                  pydantic-settings env names
  app/routers/instances.py       Route contract; no handlers
  app/routers/approvals.py       Approve/reject persist-before-Signal contract
  app/routers/webhooks.py        HMAC + Signal contract; P1 auto-spawn out of MVP
  app/models/schema.sql          SAD §4 table contract (users, instances, approvals, audit_events)
  app/db/                        Session helpers — implement in @backend.eng
  alembic.ini                    Migration config (DATABASE_URL override in env.py)
  migrations/                    Empty versions/; first revision in @backend.eng
worker/                          Temporal Worker (SAD §2, AD-2)
  main.py                        Entrypoint stub (NotImplementedError)
  sdk_env.py                     Forces ANTHROPIC_API_KEY + ANTHROPIC_BASE_URL into SDK env
  pep.py                         PreToolUse PEP placeholder
  workflows/arlo_remediation.py  ArloRemediationWorkflow placeholder
  activities/                    investigate, generate_proposal, execute_approved, validate_and_close
frontend/                        Next.js App Router (SAD §3)
  app/page.tsx                   `/` run-grid placeholder
  app/runs/[arloId]/page.tsx     Instance detail placeholder
  app/login/page.tsx             Auth placeholder
  lib/api.ts                     API_BASE only; no fetch wiring
docker/                          api / worker / frontend Dockerfiles; postgres; litellm; temporal
docker-compose.yml               postgres, temporal, temporal-ui; profiles `app` and `litellm`
scripts/set-runtime.sh           export AAMAD_TARGET_RUNTIME=claude-agent-sdk
scripts/setup.sh                 venv, pip, npm; copies .env.example → .env if missing
scripts/dev-up.sh                compose wrapper with runtime pin
.env.example                     SAD §4 keys + LiteLLM; no secret values
pyproject.toml                   Shared API + worker Python package
project-context/2.build/         This epic + downstream backlogs + logs/
```

## Environment configuration

Copy `.env.example` → `.env` and fill secrets locally. Do not commit `.env`.

SAD §4 names (plus operator LiteLLM keys):

| Name | Purpose |
|---|---|
| `AAMAD_TARGET_RUNTIME` | Must be `claude-agent-sdk` |
| `ANTHROPIC_API_KEY` | LiteLLM virtual key **or** Anthropic key |
| `ANTHROPIC_BASE_URL` | LiteLLM / org gateway (empty = direct Anthropic) |
| `LITELLM_MASTER_KEY` | Local proxy management (optional) |
| `LITELLM_UPSTREAM_ANTHROPIC_API_KEY` | Key the LiteLLM container uses upstream (optional) |
| `DATABASE_URL` | PostgreSQL |
| `TEMPORAL_ADDRESS` | Temporal frontend gRPC |
| `ARLO_SESSION_SECRET` | FastAPI session/JWT signing |
| `JIRA_MCP_URL` / `JIRA_MCP_TOKEN` | Remote Jira MCP |
| `SNOW_MCP_URL` / `SNOW_MCP_TOKEN` | ServiceNow MCP |
| `JAMF_MCP_URL` / `JAMF_MCP_TOKEN` | Jamf MCP |
| `INTUNE_MCP_URL` / `INTUNE_MCP_TOKEN` | Intune MCP |
| `JIRA_MCP_STDIO_CMD` (and SNOW/JAMF/INTUNE) | Stdio stubs |
| `JIRA_WEBHOOK_SECRET` / `SNOW_WEBHOOK_SECRET` | Webhook HMAC |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend → FastAPI |
| `ARLO_TASK_QUEUE` | Default `arlo-activities` |
| Turn/timeout caps | Investigation 24 / 900s; execution 16 / 900s |

**LiteLLM routing (operator instruction):**

- Host worker + local proxy: `ANTHROPIC_BASE_URL=http://localhost:4000`
- Compose worker + `litellm` profile: `ANTHROPIC_BASE_URL=http://litellm:4000`
- Compose worker + host proxy: `ANTHROPIC_BASE_URL=http://host.docker.internal:4000`
- No proxy: leave `ANTHROPIC_BASE_URL` empty

`@backend.eng` must construct `ClaudeSDKClient` with `ClaudeAgentOptions(env=claude_sdk_environ())` from `worker/sdk_env.py` so both `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL` reach the SDK subprocess.

## Runtime enforcement

Hardcoded `export AAMAD_TARGET_RUNTIME=claude-agent-sdk` in:

- `scripts/set-runtime.sh`
- `scripts/setup.sh`
- `scripts/dev-up.sh`
- `.env.example`
- `docker-compose.yml` (`x-arlo-runtime` on `api` and `worker`)
- `docker/api.Dockerfile` and `docker/worker.Dockerfile` `ENV`

Do not generate CrewAI `config/agents.yaml`.

## Compose topology

Default (`docker compose up`): `postgres` (5432), `temporal` (7233), `temporal-ui` (8088 → 8080 in-container).

Profile `app`: `api` (8000), `worker`, `frontend` (3000). Start after entrypoints are implemented; worker currently raises `NotImplementedError`.

Profile `litellm`: `ghcr.io/berriai/litellm:main-latest` on 4000 with `docker/litellm/config.yaml`.

Health: postgres `pg_isready`. API `/health` is liveness-only. `/ready` returns 503 until `@backend.eng` wires PostgreSQL + Temporal.

No live production deploy from this epic.

## Dependencies installed

Python (`.venv`, Python 3.11.10), including: `claude-agent-sdk==0.2.149`, `fastapi==0.141.1`, `temporalio==1.32.0`, `uvicorn==0.52.4`, `asyncpg==0.31.0`, `pydantic==2.13.5`, `sqlalchemy==2.0.52`, `alembic==1.19.1`. Dev: `pytest==9.1.1`, `httpx==0.28.1`, `ruff==0.16.5`.

Frontend (`frontend/node_modules`): `next@15.5.25`, `react@19.2.8`, `react-dom@19.2.8`, `lucide-react@0.511.0`, `typescript@5.9.3`. `npm audit` reported 2 issues (1 moderate, 1 high) — `@security.eng` to review; `--force` not run.

## Local bring-up (operator)

```bash
source scripts/set-runtime.sh          # export AAMAD_TARGET_RUNTIME=claude-agent-sdk
cp -n .env.example .env                # fill secrets
docker compose up                      # postgres + temporal + UI
# after backend/frontend implementation:
docker compose --profile app up
docker compose --profile litellm up    # optional
cd frontend && npm run dev             # or compose frontend
.venv/bin/uvicorn backend.app.main:app --reload --port 8000
```

Alembic (after `@backend.eng` writes the first revision from `schema.sql`):

`alembic -c backend/alembic.ini upgrade head`

## Sequential Build epics (next)

| Order | Persona | Artifact | May start |
|---|---|---|---|
| 1 | `@project.mgr` | `setup.md` | Done |
| 2a | `@frontend.eng` | `frontend.md` | Now (UI only; no API wiring) |
| 2b | `@backend.eng` | `backend.md` | Now (parallel with 2a) |
| 3 | `@integration.eng` | `integration.md` | After 2a and 2b have contracts |
| 4 | `@qa.eng` | `qa.md` | After integration |
| 5 | `@security.eng` | `security.md` | After QA (`require_security_assessment: true`) |
| 6 | `@devops.eng` | `3.deliver/deploy.md` | After QA (and security) |

Epic specs for steps 2–5 are in this directory with status **Backlog**. Owning personas replace backlog text with implementation records; keep Sources / Assumptions / Open Questions / Audit.

### What is next — `@frontend.eng` (`*develop-fe`)

Control-plane dashboard, not chat. Routes `/`, `/runs/[arloId]`, `/login`. Components per SAD §3: `RunGrid`, `SpawnPanel`, `StatusBadge`, `ProposalPanel`, `ApprovalActions`, `AuditTimeline`, `BannerSleeping`. Exact status labels. CSS modules / system theme — **not** Tailwind (SAD + `ui.visual_style: minimal`). Visible non-functional P1 placeholders. Do not call FastAPI.

### What is next — `@backend.eng` (`*develop-be`)

**SAD is authoritative over the generic persona “no database / no integrations” line.** MVP requires FastAPI contracts, PostgreSQL + Alembic, Temporal `ArloRemediationWorkflow` + four Activities, `ClaudeSDKClient` inside Activities with `claude_sdk_environ()`, MCP HTTP/SSE or stdio, `PreToolUse` PEP. No CrewAI YAML. New SDK session per Activity; Signal wait for HITL.

### What is next — `@integration.eng` (`*integrate-api`)

Typed `lib/api` to `/api/v1`. Auth cookies/headers. Poll 2–5s. Approve/Reject sends `proposal_hash`; 409 on stale hash. Error envelope `{ error: { code, message, arlo_id } }`.

### What is next — `@qa.eng` (`*test-unit` / `*test-integration` / `*qa`)

Map tests to PRD FR-P0-*. HITL bypass = zero writes. Concurrent ≥ 2 instances. MCP stubs must not fake write success.

### What is next — `@security.eng` (`*assess-security`)

After `qa.md`. Secrets, PEP, webhook HMAC, Intune sync classification (PRD Open Question 5). Do not change app logic.

## Diagnostic

None. Define artifacts and `aamad.config.yml` were present. Runtime resolved to `claude-agent-sdk`.

## Sources

1. `project-context/1.define/prd.md` (2026-08-31) — HITL, MCP authorized actions, dashboard, NFRs; Build must export `AAMAD_TARGET_RUNTIME=claude-agent-sdk`.
2. `project-context/1.define/sad.md` (2026-08-31) — Compose topology, FastAPI/Temporal/PostgreSQL/Next.js, env names §4, Activities, LiteLLM-adjacent `ANTHROPIC_BASE_URL`.
3. Operator `*setup-project` instruction (2026-08-31) — directory layout, LiteLLM service + `ANTHROPIC_BASE_URL`, hardcoded runtime, dependency lists, epic backlog files.
4. `aamad.config.yml` — python, `claude-agent-sdk`, unit+integration tests, security assessment required.
5. `.cursor/agents/project-mgr.md`, `.cursor/rules/aamad-core.mdc`, `.cursor/rules/adapter-registry.mdc`, `.cursor/rules/adapter-claude-agent-sdk.mdc`, `AGENTS.md` (AAMAD 0.7.5).

## Assumptions

- Project Manager does not implement HITL, MCP tool calls, Temporal Workflow bodies, or dashboard behavior. Empty routers, SQL contract, health stub, and SDK env helper are scaffolding/config only.
- Generic `@backend.eng` / `@frontend.eng` / `@integration.eng` persona files describe a chat MVP; ARLO SAD/PRD override those defaults.
- Local Compose Postgres password `arlo` is a documented capstone default, not a production secret.
- Temporal auto-setup shares the ARLO Postgres instance and creates its own `temporal` / `temporal_visibility` databases as the superuser.
- Temporal UI is published on host **8088** to avoid colliding with common 8080 usage.
- `app` and `litellm` Compose profiles keep unimplemented worker/optional proxy from blocking infra bring-up.
- Duplicate active ticket spawn defaults to 409 (SAD).
- Any authenticated user may Approve until PRD Open Question 2 is resolved.
- MCP servers themselves are out of scope; bindings + stubs are `@backend.eng`.
- `npm audit` findings are deferred to `@security.eng`; no `--force` upgrade during setup.

## Open Questions

Carried from PRD/SAD where they affect setup; not resolved here:

1. Live MCP vs stdio stubs for demo.
2. Who may Approve (ACL).
3. Duplicate spawn policy confirmation (SAD default 409).
4. Intune device sync: read-side vs mutation (`@security.eng`).
5. Jira Cloud vs Server/DC and ServiceNow prod vs subprod (MCP URL shape).
6. Numeric `ARLO-<n>` vs encoding ticket key in workflow id.
7. Docker Compose plugin availability on this host (`docker compose` not on the CLI path used during setup; Docker Engine 29.7.2 is installed).
8. Whether operator will run LiteLLM in Compose vs a host proxy vs direct Anthropic.
9. Pin Temporal image tags in Deliver vs keep `1.27.2` / UI `2.34.0`.

## Audit

- **Timestamp:** 2026-08-31T21:20:00Z (operator local 2026-08-31 ~14:20 PDT)
- **Persona id:** `project-mgr`
- **Action:** `setup-project` + `install-dependencies` + `configure-env` + `document-setup`
- **Output path:** `project-context/2.build/setup.md`
- Resolved AAMAD_TARGET_RUNTIME: claude-agent-sdk (hardcoded in scripts, `.env.example`, Compose, Dockerfiles; `aamad.config.yml` `runtime.target` matches). Shell was unset at session start; setup scripts do not rely on ambient export.
- **Config loaded:** `aamad.config.yml` (python, claude-agent-sdk, UI minimal/system, prefer_modals false, security assessment required, unit+integration tests)
- **Inputs read:** `.cursor/agents/project-mgr.md`, `project-context/1.define/prd.md`, `project-context/1.define/sad.md`, `aamad.config.yml`, adapter-registry and `adapter-claude-agent-sdk` rules, downstream persona files (for backlog handoff only)
- **Prompt Trace:** omitted. Setup-phase scaffolding; no runtime agent execution against Jira/ServiceNow/Jamf/Intune; no secret-bearing prompts. Rationale: not a high-risk executable run; citations in Sources.
- **Model / temperature / max_tokens:** Cursor Grok 4.6 interactive session; temperature/max_tokens not independently set by this persona (IDE-controlled).
- **Tool usage:** Read (persona, PRD, SAD, config, validator, agents); Glob; Shell (mkdir, pip, npm, chmod, import check); Write (layout, env, compose, placeholders, epic backlogs).
- **Write method:** temp-write `setup.md.tmp` then atomic replace to `setup.md`.
- **Prohibited actions honored:** no HITL/MCP/Workflow/dashboard business logic; no CI/CD pipelines; no secret values; no README beyond this setup.md (AAMAD root README untouched).
- **Self-check (required headings):** Sources; Assumptions; Open Questions; Audit.
- **Installed versions recorded:** claude-agent-sdk 0.2.149; fastapi 0.141.1; temporalio 1.32.0; next 15.5.25; react 19.2.8.
