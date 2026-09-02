# Backend epic: ARLO

**Document type:** AAMAD backend epic specification  
**Product:** ARLO — Automated Remediation Loop Orchestrator  
**Phase:** 2 Build  
**Owner persona:** `@backend.eng` (`backend-eng`)  
**Status:** Implemented (`*develop-be` + `*define-agents` + `*implement-endpoint` + `*document-backend`)  
**Depends on:** `project-context/2.build/setup.md` (complete)  
**Action:** `develop-be`

Generic persona text that forbids databases and external integrations **does not apply**. PRD/SAD require PostgreSQL, Temporal, Claude Agent SDK, and MCP bindings for MVP. No CrewAI YAML was generated.

## Scope (SAD-authoritative)

Production FastAPI control plane, PostgreSQL schema (including Central Memory and Vector KB), Temporal `ArloRemediationWorkflow` + Activities, Claude Agent SDK inside Activities, MCP stdio/SSE client layer, and a single wired smoke-test Activity that posts a Jira comment to verify API → Temporal → Worker → MCP → DB.

HITL sleep is `workflow.wait_condition` on Signal `approval_decision`. Write MCP tools stay out of `allowed_tools` until an approval row exists; `PreToolUse` PEP is the last-line deny.

## Repository layout (this epic)

```
backend/app/
  main.py                      FastAPI app: CORS, error envelope, lifespan migrations, /health /ready
  api/v1/                      SAD §4 REST: instances, auth, webhooks
  db/                          asyncpg engine/pool, session, Alembic runner
  models/                      SQLAlchemy: users, instances, approvals, audit_events,
                               learned_patterns, kb_articles (pgvector VECTOR(1536)),
                               run_artifacts
  schemas/                     Pydantic request/response + evidence/proposal/validation
  services/                    spawn, HITL persist-before-Signal, audit append-only
  security/                    session cookie / Bearer HMAC token, password hash
  temporal_client.py           start_workflow + signal_approval_decision
  domain/                      status machine, action catalog, proposal hash, workflow dataclasses
backend/migrations/           Alembic; 0001_initial_schema
worker/
  main.py                      Temporal worker entrypoint (task_queue=arlo-activities)
  workflows/remediation.py     ArloRemediationWorkflow + approval_decision Signal
  agents/                      AgentDefinition specialists: orchestrator, discovery,
                               script_writer, jamf_ops (SAD §2)
  activities/                  investigate, write_script, inspect_and_comment, generate_proposal,
                               post_proposal_comment, execute_jamf_test, execute_approved,
                               validate_and_close, test_comment, mark_failed
  mcp/                         ClaudeSDKClient, registry (stdio/SSE), raw_client, stubs, kb_search,
                               adf.py + vendored adf_converter.py (Markdown → Jira ADF)
  pep.py                       PreToolUse / PostToolUse
scripts/
  seed_admin.py                local users row
  test_pipeline.py             POST /api/v1/instances → DB + Temporal + Jira comment + audit
```

## API contracts (SAD §4)

Base path `/api/v1`. JSON. Auth required except `/health` and `/ready`.

| Method | Path | Behavior |
|---|---|---|
| POST | `/instances` | Validate ticket; insert `instances` (`Investigating`); `start_workflow`; 201 `{ arlo_id, status }` |
| GET | `/instances` | Grid; query `status`, `limit`, `offset` |
| GET | `/instances/{arlo_id}` | Mapping, status, timestamps, proposal, approval summary, `latest_artifacts` |
| GET | `/instances/{arlo_id}/artifacts` | Run artifacts for `/runs/[arloId]` tabs; query `type` |
| GET | `/instances/{arlo_id}/artifacts/{artifact_id}` | Single artifact body |
| GET | `/instances/{arlo_id}/audit` | Append-only events, chronological |
| POST | `/instances/{arlo_id}/approve` | Persist `approvals` then Signal; stale `proposal_hash` → 409, no Signal |
| POST | `/instances/{arlo_id}/reject` | Persist + Signal; terminal `Rejected` |
| POST | `/instances/{arlo_id}/cancel` | Signal cancel if not terminal |
| POST | `/auth/login` | Session cookie + Bearer token (no anonymous Approve) |
| POST | `/webhooks/jira` `/webhooks/servicenow` | HMAC; approval-shaped payload → persist + Signal. Auto-spawn is P1. |
| GET | `/health` | Liveness |
| GET | `/ready` | PostgreSQL + Temporal |

**Error envelope:** `{ "error": { "code", "message", "arlo_id" } }` with codes `validation_error`, `conflict`, `not_found`, `unauthenticated`, `policy_deny`, `upstream_unavailable`. Duplicate active ticket mapping → **409**. Spawn without ticket id → **400**, no row.

CORS: `FRONTEND_ORIGIN` / localhost:3000, credentials required (httpOnly `arlo_session` cookie).

## PostgreSQL + Alembic

ORM models match SAD §4 (`users`, `instances`, `approvals`, `audit_events`, `learned_patterns`, `kb_articles`). `pgvector` extension + `VECTOR(1536)` on `kb_articles.embedding`. Partial unique index `instances_active_ticket_uidx` enforces one active mapping per ticket.

Connection: SQLAlchemy async engine, **asyncpg** pool (`pool_size=10`, `max_overflow=20`, `pool_pre_ping`). Alembic uses synchronous `psycopg`.

Migrations run:

1. FastAPI lifespan (`backend.app.db.migrate.run_upgrade_head`)
2. Compose API entrypoint `docker/entrypoint-api.sh`
3. `alembic -c backend/alembic.ini upgrade head`

`arlo_id` allocation: sequence `arlo_instance_seq` starting at 675 (`ARLO-<n>`). Workflow id = lowercase display id (`arlo-675`).

## Temporal

API: `client.start_workflow(ArloRemediationWorkflow.run, RemediationWorkflowInput, id=workflow_id, task_queue="arlo-activities")`.

Workflow (`worker/workflows/remediation.py`):

1. If `jira_analysis_only`: Activity `inspect_and_comment` then complete (`Done`). No other MCP, no HITL wait, no execution.
2. Else if `jira_beta_prod`: `investigate` → `write_script` → `generate_proposal` → `post_proposal_comment` → `wait_condition` (no endpoint writes until Signal)
3. Else optional `post_smoke_test_comment` (when `smoke_test_enabled` is set at start time)
4. `investigate` → `write_script` → `generate_proposal`
5. `await workflow.wait_condition(lambda: self._decision is not None)` — worker released; no Claude/MCP held
6. Signal `approval_decision`; Execution only if `action == approve` and hashes match
7. If the frozen list includes Jamf test verbs: bounded Policy **1460** / `arlo_test` loop (`execute_jamf_test` → persist logs → `write_script` refactor → re-test; max `ARLO_SCRIPT_TEST_MAX_ATTEMPTS`)
8. `execute_approved` → `validate_and_close`

No auto-approve timer. Workflow code does not call LLM, MCP, or DB drivers. Lifecycle flags are resolved at `start_workflow` time (`resolve_lifecycle_flags`): `ARLO_JIRA_BETA_PROD` wins over `ARLO_JIRA_ANALYSIS_ONLY`; either mode disables the smoke-test comment.

**Jira comment ADF:** every live `jira_post_comment` body is wrapped with `convert_markdown_to_adf` (`worker/mcp/adf.py`). The import prefers `/Users/nick.sanchez/mcp-servers/atlassian_mcp/shared/adf_converter.py` when that file exists; otherwise the vendored copy in `worker/mcp/adf_converter.py` is used. This is a payload-shape change (MCP catalog: Activity + `jira_cloud.py`), not a new tool.

**Jira-only analysis slice** (`ARLO_JIRA_ANALYSIS_ONLY=true`): MCP tools used are only `jira_get_ticket` and `jira_post_comment`. Claude analyzes the fetched ticket JSON with `allowed_tools=[]`. Comment title is `[Arlo] Investigation Summary` with **Business Impact & Risk**, **Recommended Action Plan**, and **Open Questions**. Do not emit `ARLO Analysis for ARLO-<n>`. Instance `Investigating` → `Done`. Verify with `python scripts/test_pipeline.py --analysis --ticket-id CPE-4297`. Live Jira Cloud REST v3 when `ATLASSIAN_SITE_NAME` / `ATLASSIAN_EMAIL` / `ATLASSIAN_API_TOKEN` are set (stdio stub otherwise). Smoke-test comment is disabled on this path.

**Jira beta-prod slice** (`ARLO_JIRA_BETA_PROD=true`): Investigation identifies Apple (`macOS` → Jamf) vs Windows (`Windows` → Intune) from ticket text, then uses existing read tools (`jamf_read_compliance` / `jamf_fetch_logs` or `intune_read_compliance` / `intune_sync_device`) including stub `catalog` (policies, groups, scripts, Extension Attributes). Claude records asset gaps. `generate_proposal` persists the plan and moves the instance to `Awaiting Approval`. `post_proposal_comment` publishes the executive Markdown via ADF. The Workflow then `wait_condition`s on Signal `approval_decision`. No Jamf/Intune/ServiceNow writes are scheduled before that wait. Verify with `python scripts/test_pipeline.py --beta-prod --ticket-id CPE-4297`.

## Claude Agent SDK + MCP

- New `ClaudeSDKClient` per Activity (`worker/mcp/claude_client.py`); closed on completion. `tools=[]` (no filesystem/shell). `strict_mcp_config=True`. `permission_mode=dontAsk` (PEP is the gate).
- `ClaudeAgentOptions(env=claude_sdk_environ())` so `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` reach the SDK subprocess (LiteLLM-compatible).
- Specialists: `AgentDefinition` `arlo_orchestrator` / `discovery_agent` / `script_writer_agent` / `jamf_ops_agent` (`worker/agents/`). `worker/mcp/agents.py` re-exports `coordinator_agents` for compatibility.
- `discovery_agent` tools = Investigation reads + `kb_search`. `script_writer_agent` tools = `[]`. `jamf_ops_agent` tools = `jamf_upload_script`, `jamf_policy_set_script`, `jamf_execute_test_policy` (∩ frozen list).
- Run artifacts (`run_artifacts`) persist discovery packs, generated scripts, and test logs keyed by `arlo_id`. Next.js fetches `GET /api/v1/instances/{arlo_id}/artifacts` for the Script and Test Logs tabs.
- MCP: HTTP/SSE when `*_MCP_URL` is set; else stdio command; else in-repo fixture stub (`worker/mcp/servers/*`).
- Internal `kb_search`: in-process SDK MCP over `kb_articles`.
- PEP: deny vendor writes unless phase is Executing (Activity `writes_enabled`) **and** tool ∈ frozen list. Policy deny is audited, never treated as success.

Turn caps from env: investigation 24 / 900s; execution 16 / 900s. Max concurrent runs default 5.

### Changing MCP tools (operator iteration)

Playbook for `@backend.eng`: `.cursor/rules/mcp-tool-catalog.mdc`. Short form:

| Change | Where |
|---|---|
| Same Jira/SNOW/Jamf/Intune/KB **action**, different payload or comment text | Activity + Pydantic schema only (Jira analysis: `schemas/analysis.py`, `inspect_and_comment.py`) |
| New or renamed **authorized** action | PRD §3.4 first if missing → `backend/app/domain/actions.py` → matching tool on `worker/mcp/servers/*` (live Jira: also `jira_cloud.py`) → Activity call site if it is a pre-call → `backend/tests/test_actions.py` → this file |
| PEP / `allowed_tools` | Derived from the catalog. Do not fork lists in `pep.py` or `agents.py` unless the specialist prompt must mention the new tool by name |

Writes stay Execution-phase and HITL-gated except the documented smoke-test and Jira-analysis comment exceptions.

## Smoke-test execution path (operator verification)

**Not** a production remediation write. `ARLO_SMOKE_TEST_ENABLED` (default true) is copied onto `RemediationWorkflowInput` at `start_workflow` time so the Workflow stays deterministic.

Activity `worker/activities/test_comment.py` calls Jira MCP `jira_post_comment` with:

`[Arlo] Backend pipeline connected. Instance {arlo_id} initialized.`

and appends `audit_events.kind=smoke_test`. It uses `worker.mcp.raw_client` (no Claude loop). Disable with `ARLO_SMOKE_TEST_ENABLED=false`.

Verification script: `python scripts/test_pipeline.py` (unique `JIRA-PIPE-<epoch>` by default so reruns do not 409).

## AuthN

Signed HMAC session token (`ARLO_SESSION_SECRET`). Bearer header or `arlo_session` cookie. Approver → `approvals.actor_id`. Seed via `python scripts/seed_admin.py`. Any authenticated user may Approve until PRD Open Question 2 is resolved.

## Out of scope (this epic)

AppSec/git, webhook auto-spawn (P1), CrewAI, Temporal Cloud, live production deploy, frontend wiring (`@integration.eng`).

## Handoff

`@frontend.eng` may work in parallel. `@integration.eng` needs:

- Base URL `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`)
- `POST /api/v1/auth/login` → cookie + `token`; send `Authorization: Bearer` or cookie
- Spawn body `{ ticket_system: "jira"|"servicenow", ticket_id }`
- Approve/Reject body `{ proposal_hash }` (409 on stale hash)
- Error envelope `{ error: { code, message, arlo_id } }`
- Poll GET list/detail/artifacts/audit every 2–5s while non-terminal
- Detail includes `latest_artifacts` for Proposal / Script / Test Logs first paint

## Sources

1. `project-context/1.define/sad.md` §1–§4, §6, AD-1–AD-18 (Temporal, Claude in Activities, MCP, FastAPI, PostgreSQL, HITL Signal, specialists, `run_artifacts`, Policy 1460 loop).
2. `project-context/1.define/prd.md` §3–§5, FR-P0-01–10, UI-P0 status vocabulary, MCP authorized actions.
3. `project-context/2.build/setup.md` (layout, env names, Compose, LiteLLM routing).
4. `.cursor/rules/adapter-claude-agent-sdk.mdc` (ClaudeSDKClient, hooks, least-privilege tools, session-per-Activity).
5. `.cursor/agents/backend-eng.md` (commands; SAD overrides “no database”).
6. Operator instruction (2026-09-01): production directory layout, Alembic on startup, smoke-test Jira comment, `scripts/test_pipeline.py`.
7. Operator instruction (2026-09-01): Markdown → ADF via `convert_markdown_to_adf`, executive analysis comment template, `ARLO_JIRA_BETA_PROD` discovery + proposal + HITL pause.
7. Operator instruction (2026-09-01): Markdown → ADF via `convert_markdown_to_adf`, executive analysis comment template, `ARLO_JIRA_BETA_PROD` discovery + proposal + HITL pause.

## Assumptions

- SAD overrides the generic backend-eng “no database / no integrations” prohibition for this product.
- Duplicate active ticket spawn is 409 (SAD default for PRD Open Question 3).
- Any authenticated ARLO user may Approve (PRD Open Question 2 unset).
- Numeric `ARLO-<n>` ids; sequence starts at 675.
- Capstone MCP stubs over stdio are acceptable when `*_MCP_URL` is empty; they still persist fixture writes so the smoke test is observable.
- The smoke-test Jira comment is an **operator-authorized HITL exception** for pipeline verification only. It is not a remediation write, is not in investigator `allowed_tools`, and is gated by `ARLO_SMOKE_TEST_ENABLED` / `smoke_test_enabled` on the Workflow input.
- The Jira-only analysis slice (`ARLO_JIRA_ANALYSIS_ONLY`) is a second **operator-authorized** exception: inspect + analysis comment, then stop. It does not enable Jamf/Intune/ServiceNow, HITL execution, or ticket close. `Investigating` → `Done` is legal only for this completion path; `Investigating` → `Executing` remains forbidden.
- `ARLO_JIRA_BETA_PROD` is a third **operator-authorized** exception for the discovery/proposal Jira comment (same `jira_post_comment` action, still not in investigator `allowed_tools`). It enables Jamf/Intune **reads** and sleeps at `Awaiting Approval`. It does not authorize endpoint writes before the approval Signal.
- `jamf_upload_script`, `jamf_policy_set_script`, and `jamf_execute_test_policy` are Build-time bindings of PRD §3.4 “Apply approved configuration profiles or scripts.” Policy **1460** / event `arlo_test` are env-overridable isolated test-policy identifiers. The test-loop Activity uses `raw_client` for those three tools **after** a frozen-list check (same HITL gate as PEP; no shell).
- `run_artifacts` rows are append-only. Script refactors increment `attempt`.
- LiteLLM is optional; empty `ANTHROPIC_BASE_URL` means the SDK uses its default Anthropic endpoint.
- `kb_articles` ingest is setup/admin, not an Investigation tool. Embeddings require `EMBEDDING_*`; KB miss is a declared gap, not fail-open.
- Local Compose Postgres password `arlo` is a documented capstone default, not a production secret.
- `ARLO_SESSION_SECRET` should be set for any persistent environment; if unset, tokens are ephemeral per API process.

## Open Questions

Carried from PRD/SAD; not resolved here:

1. Live MCP vs stdio stubs for demo (default: stubs when URLs empty; Jira Cloud REST when Atlassian env names are set).
2. Who may Approve (ACL) — any authenticated user until product amends.
3. Duplicate spawn policy confirmation (implemented as 409).
4. Intune device sync: read-side vs mutation (`@security.eng`).
5. Jira Cloud vs Server/DC MCP URL/auth shape.
6. Embedding provider that yields 1536 dimensions.
7. Whether dashboard MVP must list matched pattern / KB citations (payload is already on instance detail).
8. Webhook-originated approval vs dashboard-only (ingress exists; P0 actor remains dashboard).
9. When to restore the full HITL remediation path after the Jira-analysis-only slice.
10. Whether `ARLO_JIRA_BETA_PROD` should remain a flag after the capstone demo or become the default spawn path (analysis-only stays the inspect-and-stop slice).
11. Live Jamf/Intune MCP payloads may omit stub `catalog` fields; gap records are then required rather than inventing EA/policy inventory.
12. Whether `@product-mgr` should split PRD §3.4 Jamf write into explicit upload / policy-set / execute-test rows (SAD binds them as granular tools of the existing write).
13. Whether a failing Policy 1460 test should return to Awaiting Approval (P1 request-changes) instead of Failed after the attempt bound.

## Audit

- **Timestamp:** 2026-09-01T23:49:16Z (operator local 2026-09-01 ~16:49 PDT)
- **Persona id:** `backend-eng`
- **Action:** `define-agents` + persist artifacts (SAD specialist topology)
- **Output path:** `project-context/2.build/backend.md`; `worker/agents/`; `worker/activities/write_script.py`; `worker/activities/execute_jamf_test.py`; `backend/app/models/run_artifact.py`; `backend/migrations/versions/0002_run_artifacts.py`
- **Resolved AAMAD_TARGET_RUNTIME:** `claude-agent-sdk` via `aamad.config.yml` (`AAMAD_TARGET_RUNTIME` unset in this shell)
- **Config loaded:** `aamad.config.yml`
- **Inputs read:** `.cursor/agents/backend-eng.md`; SAD §2/§4/§6 AD-16–18; PRD §3.4 Jamf write; `mcp-tool-catalog.mdc`; existing Activities and catalog
- **Changes:** four `AgentDefinition` modules; Jamf test-policy tool bindings of the existing PRD write; `run_artifacts` + list/detail APIs; Temporal `write_script` + Policy 1460 test-loop; specialist `allowed_tools` segregation
- **Prompt Trace:** omitted. Agent prompts are the SAD-normative strings in `worker/agents/`; no secret values; no `.env` read into artifacts.
- **Model / temperature / max_tokens:** Cursor Grok 4.6 interactive session. Runtime Activities use `CLAUDE_MODEL` from env; `write_script` falls back to a deterministic template if Claude is unavailable.
- **Tool usage:** Read (SAD, PRD, catalog, Activities); Write (agents, catalog, stubs, schema, Activities, Workflow, tests, this file).
- **Write method:** in-place under `backend/`, `worker/`, `project-context/2.build/backend.md`.
- **Prohibited actions honored:** no new PRD product verbs (Jamf tools bind the existing apply-scripts write); no Bash/`sudo` on the SDK agent; no vendor writes before HITL; no secret values in artifacts.
- **Self-check (required headings):** Sources; Assumptions; Open Questions; Audit.

## Audit

- **Timestamp:** 2026-09-01T20:40:00Z (operator local 2026-09-01 ~13:40 PDT)
- **Persona id:** `backend-eng`
- **Action:** `develop-be` (Jira-only inspect+comment slice)
- **Output path:** `project-context/2.build/backend.md`
- **Resolved AAMAD_TARGET_RUNTIME:** `claude-agent-sdk`
- **Config loaded:** `aamad.config.yml`
- **Inputs read:** operator request to inspect a live ticket, evaluate work, post an analysis comment, and stop; PRD/SAD HITL remaining for later MCP tools.
- **Prompt Trace:** omitted. Analysis prompt is ticket JSON already fetched via `jira_get_ticket`; no secrets in this artifact. Live Atlassian token values are env-only.
- **Model / temperature / max_tokens:** Cursor Grok 4.6 interactive session. Runtime analysis Activity uses `CLAUDE_MODEL` from env (`allowed_tools=[]`, `max_turns=8`).
- **Tool usage:** Read/Write for workflow, Jira Cloud REST helper, inspect Activity, tests, this file.
- **Write method:** in-place under `backend/`, `worker/`, `scripts/`.
- **Prohibited actions honored:** no other MCP systems; no ticket close/transition; no HITL execution; no secret values in artifacts.
- **Self-check (required headings):** Sources; Assumptions; Open Questions; Audit.

## Audit

- **Timestamp:** 2026-09-01T22:40:00Z (operator local 2026-09-01 ~15:40 PDT)
- **Persona id:** `backend-eng`
- **Action:** `document-backend` (MCP tool-change playbook)
- **Output path:** `project-context/2.build/backend.md`; `.cursor/rules/mcp-tool-catalog.mdc`; `.cursor/agents/backend-eng.md`
- **Resolved AAMAD_TARGET_RUNTIME:** `claude-agent-sdk`
- **Config loaded:** `aamad.config.yml`
- **Inputs read:** operator request for a single ordered map (PRD → actions.py → MCP server → PEP/allowed_tools) so Jira/MCP tweaks are repeatable.
- **Prompt Trace:** omitted. Documentation-only; no runtime execution.
- **Tool usage:** Read (persona, actions.py, pep.py, backend.md); Write (rule, persona, this file, epics-index, AGENTS.md).
- **Prohibited actions honored:** no new MCP tools added; no secrets.
- **Self-check (required headings):** Sources; Assumptions; Open Questions; Audit.

## Audit

- **Timestamp:** 2026-09-01T23:20:00Z (operator local 2026-09-01 ~16:20 PDT)
- **Persona id:** `backend-eng`
- **Action:** `develop-be` (ADF comments, executive analysis prompt, `ARLO_JIRA_BETA_PROD`)
- **Output path:** `project-context/2.build/backend.md`; `backend/`; `worker/`
- **Resolved AAMAD_TARGET_RUNTIME:** `claude-agent-sdk`
- **Config loaded:** `aamad.config.yml`
- **Inputs read:** operator prompt for ADF converter integration, executive analysis persona, and beta-prod discovery/proposal lifecycle; PRD §3.4; SAD HITL; `mcp-tool-catalog.mdc`; existing inspect/investigate/proposal Activities.
- **Prompt Trace:** omitted. System prompts are the executive Markdown template already recorded in this artifact; no secrets. Live Atlassian token values remain env-only.
- **Model / temperature / max_tokens:** Cursor Grok 4.6 interactive session. Runtime Activities use `CLAUDE_MODEL` from env.
- **Tool usage:** Read/Write for worker Activities, Jira Cloud ADF wrap, lifecycle flags, tests, this file.
- **Write method:** in-place under `backend/`, `worker/`, `scripts/`.
- **Prohibited actions honored:** no new MCP tools; no Jamf/Intune writes before HITL; no secret values in artifacts.
- **Self-check (required headings):** Sources; Assumptions; Open Questions; Audit.
