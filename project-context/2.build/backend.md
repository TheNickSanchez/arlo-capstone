# Backend epic: ARLO (backlog)

**Document type:** AAMAD backend epic specification  
**Status:** Backlog — not implemented  
**Owner persona:** `@backend.eng` (`backend-eng`)  
**Depends on:** `project-context/2.build/setup.md` (complete)  
**Action when executing:** `*develop-be` then `*document-backend`

Replace this backlog with implementation records. Keep Sources, Assumptions, Open Questions, and Audit.

## Scope (SAD-authoritative)

Generic persona text that forbids databases and external integrations **does not apply**. PRD/SAD require PostgreSQL, Temporal, Claude Agent SDK, and MCP bindings for MVP.

Do not generate CrewAI YAML. Runtime is `claude-agent-sdk` only.

## Tasks (sequential within this epic)

1. **API contracts (SAD §4)** — FastAPI `/api/v1`: instances CRUD/list, audit, approve/reject/cancel, webhooks, `/health`, `/ready`. Error envelope `{ "error": { "code", "message", "arlo_id" } }`. Auth except health/ready. Duplicate active ticket → 409. Stale `proposal_hash` → 409, no Signal.
2. **PostgreSQL + Alembic** — Models from `backend/app/models/schema.sql`. First revision under `backend/migrations/versions/`. Append-only `audit_events`.
3. **Temporal client on API** — `start_workflow(ArloRemediationWorkflow.run, …, id=workflow_id, task_queue="arlo-activities")`. Signal `approval_decision` only after approvals row is persisted.
4. **`ArloRemediationWorkflow`** — Deterministic: schedule `investigate` → `generate_proposal` → `wait_condition` on Signal → `execute_approved` (approve + hash match only) → `validate_and_close`. No auto-approve timer. No LLM/MCP/DB in Workflow code.
5. **Activities + Claude Agent SDK** — New `ClaudeSDKClient` per Activity; close on completion. Pass `worker.sdk_env.claude_sdk_environ()` into `ClaudeAgentOptions(env=...)` so `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL` route through LiteLLM. Coordinator + `arlo-investigator` / `arlo-executor` `AgentDefinition`s. Turn caps from env. No built-in filesystem/shell tools.
6. **MCP** — HTTP/SSE or stdio per env. Read tools in investigate/proposal/validate; write tools only in execute from frozen list. Fail closed if required server missing.
7. **PEP** — `PreToolUse` deny writes unless phase is Executing and tool ∈ frozen list; `PostToolUse` audit (redact). Policy deny is not success.
8. **AuthN** — Session cookie or signed token using `ARLO_SESSION_SECRET`. No anonymous Approve. Approver → `approvals.actor_id`.

## Out of scope

AppSec/git, auto-spawn from ticket-created webhooks (P1), CrewAI, Temporal Cloud, live production deploy.

## Handoff

`@frontend.eng` may work in parallel. `@integration.eng` needs stable JSON contracts and auth scheme documented in this file after implementation.

## Sources

1. `project-context/1.define/sad.md` §2, §4, AD-1–AD-12.
2. `project-context/1.define/prd.md` §3–§5, FR-P0-01–10.
3. `project-context/2.build/setup.md`.
4. `.cursor/rules/adapter-claude-agent-sdk.mdc`.
5. `.cursor/agents/backend-eng.md` (commands only; SAD overrides “no database”).

## Assumptions

- Scaffold routers and `schema.sql` are contracts, not a complete API.
- LiteLLM is optional; empty `ANTHROPIC_BASE_URL` means direct Anthropic.
- MCP server implementations are not this epic; bind authorized actions only.

## Open Questions

See PRD/SAD Open Questions 1–9, 13 (webhook-originated approval). Confirm idempotency key = `arlo_id` + `proposal_hash` + action id.

## Audit

- **Timestamp:** 2026-08-31T21:20:00Z
- **Persona id:** `project-mgr` (backlog only; implementation Audit will be `backend-eng`)
- **Action:** `document-setup` (epic backlog)
- Resolved AAMAD_TARGET_RUNTIME: claude-agent-sdk
- **Prompt Trace:** omitted (no runtime agent execution)
