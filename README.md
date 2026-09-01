# ARLO — Automated Remediation Loop Orchestrator

ARLO is a human-gated multi-agent system for **enterprise IT and endpoint remediation**. Each work item is a named instance (`ARLO-675`, `ARLO-676`, …) bound 1:1 to a Jira or ServiceNow ticket. The instance investigates with read-only tools, proposes a plan, **sleeps at an approval gate**, and only then may execute state-changing actions on endpoints or tickets.

**No endpoint or ticket mutation until a human approves.** That rule is architectural, not a prompt suggestion.

This repository is a capstone MVP built with the [AAMAD](AGENTS.md) framework (v0.7.5). Product scope is defined in [`project-context/1.define/prd.md`](project-context/1.define/prd.md). Architecture is defined in [`project-context/1.define/sad.md`](project-context/1.define/sad.md).

---

## Problem

Enterprise IT, desktop, and endpoint teams take a continuous stream of tickets for device non-compliance, configuration drift, failed profiles/policies, and related incidents. Operators today context-switch across:

- **Jira** or **ServiceNow** (ticket + change)
- **Jamf** (Apple)
- **Intune** (Windows / mobile)
- Internal SOPs / runbooks

They assemble evidence by hand, draft a plan, wait on change discipline, then click remediations in MDM consoles. Nothing in that loop is a single auditable “run.” Fully autonomous agents that apply profiles, scripts, or policies without a human gate are unacceptable: endpoint mutation and ticket mutation are production-impacting.

Typical pain:

- Evidence for one ticket is scattered across four consoles.
- There is no durable, named run identity — state dies when a chat ends.
- Managers cannot see Investigating vs stuck-on-human vs Executing vs Done across the queue.
- Change process is skipped or duplicated (no tracking CHG, or a CHG that is disconnected from MDM work).
- Silent MDM writes and rubber-stamped AI plans are both unacceptable.

## Value proposition

ARLO is an **Enterprise IT & Endpoint Remediation Specialist** blueprint. Operators spin up a **new instance per ticket**. The instance:

1. Investigates using **read-authorized** MCP actions (ticket, asset, Jamf/Intune compliance, official SOPs).
2. Produces a grounded proposal with an explicit action list.
3. **Pauses (sleeps)** until a human approves or rejects.
4. Executes **only the approved** Jamf/Intune remediations, ServiceNow change-request tracking, and Jira ticket mutations.
5. Validates device state and closes or transitions the ticket per the approved plan.

Every step is written to an immutable audit log. Sibling instances run concurrently — one HITL sleep does not freeze the queue.

**What ARLO is not:** an AppSec autofix bot, a source-code patcher, or an unsupervised endpoint agent. Application git/PR/SAST workflows are out of MVP.

---

## Key features (MVP)

| Feature | What operators get |
|---|---|
| **Named instance per ticket** | Spawn `ARLO-<id>` mapped 1:1 to an existing Jira or ServiceNow ticket. Two tickets never share a session. |
| **Read-only investigation** | Ticket context, ServiceNow CHG/asset reads, Jamf compliance + logs, Intune compliance + status refresh, Knowledge Base `kb_search`. No writes. |
| **Grounded proposal** | Evidence, targeted device IDs, enumerated MCP write actions, validation checks, residual risk, runbook citations. |
| **Durable approval gate** | Agent **sleeps**. No auto-approve timer. Restarting the app leaves the instance in **Awaiting Approval** with the same proposal. |
| **Approve / Reject** | Approve records actor, time, and a frozen action list. Reject records rationale and mutates nothing. |
| **Approved writes only** | Jamf profiles/scripts, Intune policies/remediations, ServiceNow CHG create, Jira summary/transition/close — only if listed on the approved plan. |
| **Validation before Done** | Re-read compliance/asset. Close or transition the ticket only if those writes were approved and validation criteria passed. |
| **Fleet dashboard** | Grid of all historical and active runs with status, timestamps, proposal, Approve/Reject, and step-level audit. Not a chat thread. |
| **Concurrent isolated runs** | At least two instances in different phases at once; one sleep does not block siblings. |
| **Visible policy deny** | Blocked write attempts are audit events. Fail closed. Never fail open. |

### Run statuses

| Status | Meaning |
|---|---|
| **Investigating** | Trigger accepted through proposal generation (reads + reasoning) |
| **Awaiting Approval** | Agent sleeping at the HITL gate |
| **Executing** | Approved writes and/or validation in progress |
| **Done** | Terminal success |
| **Rejected** / **Failed** / **Cancelled** | Terminal / operational outcomes so the grid does not lie |

### Lifecycle

```
Trigger (map instance to an existing Jira/SNOW ticket)
    → Investigation & Research          (reads only)
    → Proposal / Summary Generation     (no writes)
    → Approval Gate Pause               (agent sleeps)
    → Human Approves | Rejects | Cancels
    → Execution                         (approved writes only)
    → Validation & Ticket Closure       (Done)
```

Trigger in MVP is **user-initiated spawn** from the dashboard. Automatic webhook auto-spawn is a later enhancement.

---

## Architecture

One hardened agent blueprint is cloned into many durable, ticket-mapped instances. Each instance is a state machine. Illegal transitions are product bugs.

### Runtime agents and roles

| Agent | Role | Responsibility | Tools |
|---|---|---|---|
| **`arlo`** (coordinator) | Enterprise IT & Endpoint Remediation Specialist | Owns lifecycle phase, HITL sleep, budgets, and audit narrative. Never bypasses the gate. | No MCP writes. May invoke specialists. |
| **`arlo-investigator`** | Read-only evidence gatherer | Assembles ticket, asset, device compliance/log, and official runbook context. | Read MCP actions + `kb_search` only. Write tools never present. |
| **Proposal path** | Proposal specialist | Turns the evidence pack into a human-reviewable summary and enumerated action list. | Reads if needed. **No writes.** |
| **`arlo-executor`** | Approved-plan executor | Applies the frozen action list exactly. Halts on the first unauthorized or failed mutation. | Only write tools listed on the approval record. |
| **Validation** | Validation specialist | Re-reads compliance/asset. Closes or transitions the ticket only if those writes were approved and criteria passed. | Validation reads; ticket writes iff on the frozen list. |

Collaboration is **sequential per instance** and **concurrent across instances**. Subagent delegation is allowed only to isolate read vs write tool sets and **must not bypass HITL**.

### How the repo implements that loop

| Layer | Responsibility |
|---|---|
| **Next.js dashboard** | Spawn form, run grid, instance detail, proposal, Approve/Reject, audit timeline. Never talks to Temporal, MCP, or the model provider. |
| **FastAPI control plane** | Auth, spawn, persist instance state, start workflows, emit approval Signals, serve list/detail/audit. |
| **PostgreSQL** | Users, instance metadata, frozen proposal, approval records, mirrored audit, shared operational memory, vector Knowledge Base. |
| **Temporal** | One Workflow per `ARLO-<id>`. The approval gate is a **Signal wait** — the worker, LLM session, and MCP connections are not held while a human decides. |
| **Temporal Worker + Claude Agent SDK** | Investigation, proposal, execution, and validation run **inside Activities**. Write tools are absent from `allowed_tools` until an approval record exists. A `PreToolUse` policy enforcement point denies writes otherwise. |
| **MCP servers** | Authorized actions only for Jira, ServiceNow, Jamf, Intune, and internal `kb_search`. Capstone may use stdio stubs when live tenants are unavailable. Stubs must still obey HITL. |

Selected runtime: **`claude-agent-sdk`** (Python). Set `AAMAD_TARGET_RUNTIME=claude-agent-sdk` in every Build/CI shell — if unset, the AAMAD adapter registry defaults to `crewai`.

Logical architecture (SAD):

![ARLO logical architecture](project-context/1.define/diagrams/arlo-logical-architecture.png)

### Authorized MCP surface (product, not implementation)

**Reads** (Investigation; Validation where specified): Jira ticket context; ServiceNow existing CHGs + asset data; Jamf compliance + logs; Intune compliance + device-status refresh; Knowledge Base `kb_search` (Investigation only).

**Writes** (Execution / Validation only, and only if on the approved plan): Jira post summary / transition / close; ServiceNow create CHG; Jamf apply approved profile or script; Intune apply approved policy or remediation.

Explicitly unauthorized in MVP: wipe/retire/lock device; identity or network changes; arbitrary unsigned scripts; expanding scope to devices not in the ticket/proposal; Knowledge Base writes; any mutation not on the approved list.

---

## Getting started

### Prerequisites

| Tool | Notes |
|---|---|
| **Python** 3.11+ | API + Temporal worker (`requires-python >=3.11`) |
| **Node.js** LTS + npm | Next.js dashboard under `frontend/` |
| **Docker** + Compose | PostgreSQL (pgvector), Temporal, optional LiteLLM and app images |
| **Anthropic-compatible API key** | Direct Anthropic or a LiteLLM virtual key (`ANTHROPIC_API_KEY`) |

### 1. Pin the runtime and install

```bash
source scripts/set-runtime.sh          # export AAMAD_TARGET_RUNTIME=claude-agent-sdk
./scripts/setup.sh                     # venv, pip install -e ".[dev]", npm install
```

`setup.sh` copies `.env.example` → `.env` if `.env` is missing.

### 2. Configure environment

Edit `.env`. Fill secrets locally. **Never commit `.env`.**

Required for a local loop:

| Variable | Purpose |
|---|---|
| `AAMAD_TARGET_RUNTIME` | Must be `claude-agent-sdk` |
| `ANTHROPIC_API_KEY` | LiteLLM virtual key or Anthropic key |
| `ANTHROPIC_BASE_URL` | `http://localhost:4000` with local LiteLLM; empty for direct Anthropic |
| `DATABASE_URL` | PostgreSQL (Compose default: `postgresql://arlo:arlo@localhost:5432/arlo`) |
| `TEMPORAL_ADDRESS` | `localhost:7233` on the host |
| `ARLO_SESSION_SECRET` | Long random string for session/JWT signing |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` |
| `ARLO_ADMIN_PASSWORD` | Local seed admin (optional; `scripts/seed_admin.py`) |

MCP URLs/tokens are for live tenants. Leave them empty and use stdio stub commands when demonstrating without Jamf/Intune/Jira/ServiceNow access. Stubs must not report write success that skipped the approval gate.

### 3. Start infrastructure

```bash
docker compose up                      # postgres :5432, temporal :7233, temporal-ui :8088
```

Optional model proxy:

```bash
docker compose --profile litellm up
```

### 4. Run the application (host processes)

```bash
# API (Alembic runs on startup)
.venv/bin/uvicorn backend.app.main:app --reload --port 8000

# Temporal worker (separate terminal)
.venv/bin/python -m worker.main

# Dashboard (separate terminal)
cd frontend && npm run dev
```

Or, after images are built:

```bash
docker compose --profile app up        # api :8000, worker, frontend :3000
```

### 5. Seed a local admin (optional)

```bash
.venv/bin/python scripts/seed_admin.py
```

### Local endpoints

| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| API liveness | http://localhost:8000/health |
| API readiness | http://localhost:8000/ready (PostgreSQL + Temporal) |
| Temporal UI | http://localhost:8088 |

### Tests and lint

```bash
source scripts/set-runtime.sh
.venv/bin/pytest
.venv/bin/ruff check backend worker
cd frontend && npm run lint
```

---

## Project structure

```
arlo-capstone/
├── aamad.config.yml                 # Runtime, language, UI, security, testing preferences
├── AGENTS.md                        # AAMAD persona index
├── CHECKLIST.md                     # Phase 1–3 execution checklist
├── pyproject.toml                   # Shared Python package (API + worker)
├── docker-compose.yml               # postgres, temporal, api, worker, frontend, litellm
├── .env.example                     # Secret *names* only
│
├── backend/                         # FastAPI control plane
│   ├── app/                         # API, domain, models, services, security
│   └── migrations/                  # Alembic (0001_initial_schema)
│
├── worker/                          # Temporal worker + Claude Agent SDK
│   ├── workflows/                   # ArloRemediationWorkflow + approval Signal
│   ├── activities/                  # investigate, proposal, execute, validate
│   ├── mcp/                         # SDK client, registry, stubs, kb_search
│   └── pep.py                       # PreToolUse / PostToolUse policy + audit
│
├── frontend/                        # Next.js App Router dashboard
│   └── app/                         # /, /runs/[arloId], /login
│
├── docker/                          # Dockerfiles, postgres init, LiteLLM, Temporal
├── scripts/                         # setup, runtime pin, compose wrapper, seed admin
│
├── project-context/
│   ├── 1.define/                    # PRD, SAD, MRD, architecture diagrams
│   ├── 2.build/                     # setup, backend, frontend, integration, qa, security
│   └── 3.deliver/                   # deploy.md + user-guide.md (after QA + security)
│
└── .cursor/
    ├── agents/                      # Persona contracts (@product-mgr, @backend.eng, …)
    ├── rules/                       # AAMAD core + runtime adapter rules
    └── templates/                   # Artifact templates
```

**Correspondence rule:** instance id `ARLO-<id>` = Temporal Workflow Id = PostgreSQL `instances.arlo_id` = dashboard row key. UI, API, Workflow, and database use the same status vocabulary.

---

## Who this is for

| Persona | Job in ARLO |
|---|---|
| **IT Support / Service Desk** | Spawn an instance on a ticket; watch Investigating → Awaiting Approval; hand the approval card to the right owner. |
| **Endpoint / MDM Administrator** | Approve or reject proposed Jamf/Intune actions with enough evidence to be safe. |
| **Change / IT Operations Lead** | Confirm existing CHGs were checked and tracking CHGs are created only after approval. |
| **IT / Engineering Manager** | Grid of all historical and active runs — who approved what — without opening 40 MDM consoles. |

---

## Next steps for contributors

Work is sequenced by AAMAD personas. Do not invent product scope — if it is not in the PRD, it is not MVP.

### Remaining Build / Deliver work

1. **`@integration.eng`** — Replace the frontend mock services with the FastAPI client (`POST /instances`, list/detail/audit, Approve/Reject with `proposal_hash`, session auth). The UI must never call Temporal, MCP, or Anthropic.
2. **`@qa.eng`** — Unit + integration + smoke against PRD `FR-P0-*` / `UI-P0-*`. Required bar: unapproved mutations = **zero**; HITL bypass blocked **100%**; ≥ 2 concurrent isolated instances.
3. **`@security.eng`** — Required before Deliver (`security.require_security_assessment: true`). Secrets, PEP layers, attributable Approve, dependency audit.
4. **`@devops.eng`** — `project-context/3.deliver/deploy.md` + `user-guide.md`. Generate CI config only; do not trigger a live production deploy without operator authorization.

Invoke personas in Cursor as `@product-mgr`, `@system.arch`, `@project.mgr`, `@frontend.eng`, `@backend.eng`, `@integration.eng`, `@qa.eng`, `@security.eng`, `@devops.eng`. See [`AGENTS.md`](AGENTS.md) and [`CHECKLIST.md`](CHECKLIST.md). Run `aamad validate` to check artifact quality gates.

### Product backlog (not MVP)

**P1**

- Auto-spawn from Jira/ServiceNow webhooks when a ticket is created or labeled.
- Request-changes loop (human comments; instance re-enters Investigation without executing).
- KEV/severity/SLA badges on the grid.
- Filter/export audit log; richer duplicate-ticket / existing-CHG intelligence.

**P2 / explicitly out of MVP**

- AppSec / git / draft-PR / SAST loop (researched in the MRD, **superseded** by this PRD’s IT/endpoint scope).
- Graduated autonomy, device wipe/retire/lost mode, identity or network changes.
- Batch approve, multi-ticket bulk orchestration, enterprise SSO/IAM, multi-tenant SaaS.
- Auto-merge, auto-close without validation, or auto-approve on timeout — these stay forbidden.

### Contributor rules of the road

- **PRD is scope-authoritative.** The MRD targeted an AppSec/code concept; do not revive git write or scanner scope without an explicit PRD amendment.
- **HITL is architecture.** Write-capable tools stay out of `allowed_tools` until an approval record exists. A policy enforcement point outside the model is the last-line deny.
- **Fail closed.** Missing approval, rejection, MCP unavailable, or policy deny never “helpfully” continues into writes.
- **Secrets stay in environment variables.** Commit names from `.env.example` only. Never put tokens in artifacts, Prompt Trace, Jira comments, CHGs, or the audit UI.
- **Prefer stubs that tell the truth.** If live Jamf/Intune/Jira/ServiceNow tenants are unavailable, stubs must still refuse unapproved writes.

---

## Documentation map

| Artifact | Path |
|---|---|
| Product requirements | [`project-context/1.define/prd.md`](project-context/1.define/prd.md) |
| System architecture | [`project-context/1.define/sad.md`](project-context/1.define/sad.md) |
| Market research (AppSec-era; HITL/concurrency only) | [`project-context/1.define/mrd.md`](project-context/1.define/mrd.md) |
| Frontend functional spec | [`frontend-functional-spec.md`](frontend-functional-spec.md) |
| Setup / env / Compose | [`project-context/2.build/setup.md`](project-context/2.build/setup.md) |
| Backend epic | [`project-context/2.build/backend.md`](project-context/2.build/backend.md) |
| Frontend epic | [`project-context/2.build/frontend.md`](project-context/2.build/frontend.md) |
| AAMAD personas | [`AGENTS.md`](AGENTS.md) |

---

## License and notices

Capstone / internal operational MVP. No commercial go-to-market, pricing, or packaging. Third-party systems (Jira, ServiceNow, Jamf, Intune, Anthropic, Temporal) remain under their own terms. Do not embed vendor secrets in this repository.
