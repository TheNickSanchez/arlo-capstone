# Frontend epic: ARLO dashboard (mock-backed)

**Document type:** AAMAD frontend epic  
**Product:** ARLO — Automated Remediation Loop Orchestrator  
**Phase:** 2 Build  
**Owner persona:** `@frontend.eng` (`frontend-eng`)  
**Date:** 2026-08-31  
**Status:** Complete for UI epic (mock data; FastAPI unwired)  
**Action:** `*develop-fe` + `*add-placeholders` + `*style-ui` + `*document-frontend`

## Purpose

Implement the MVP **control-plane dashboard** (not a chat thread) from SAD §3 and PRD §4.3 / §6, using in-memory mock services so the HITL loop is demonstrable without `@integration.eng`.

Operator-facing contract: root `frontend-functional-spec.md` (workflow **ARLO Endpoint Remediation Workflow**).

## What was built

### Routes

| Route | Implementation |
|---|---|
| `/` | Spawn (Inputs), **Active Agents**, focused Run banner + controls, Results, **Run History** |
| `/runs/[arloId]` | Instance detail: status, sleep banner, Approve/Reject/Reset, proposal, audit |
| `/login` | Visible stub; fields disabled; copy that session auth is for integration |

### Components

`AppShell`, `Dashboard`, `SpawnPanel`, `StatusBanner`, `StatusBadge`, `BannerSleeping`, `ApprovalActions`, `ProposalPanel`, `AuditTimeline`, `RunGrid`, `FleetActionBanner`, `FutureWorkStubs`, `RunDetailView`.

Styling: `app/globals.css` + `styles/dashboard.module.css`. System theme (`color-scheme: light dark`), minimal panels, **no vendor UI kit**, **no Tailwind**. `lucide-react` unused. `prefer_modals: false` — Approve/Reject are in-page.

### Mock layer

`frontend/lib/services.ts` (no `fetch`):

- `startRun(ticketId, ticketSystem)` → `{ arlo_id }` starting at **ARLO-675**
- `getRunStatus(arloId)` advances `investigating` → `awaiting_approval`, then **halts** until approve; after approve, `executing` → `done`
- `approveRun(arloId, proposalHash)` → `executing` when hash matches

`frontend/lib/api.ts` still exports `API_BASE` only.

### FSM and a11y

Phases: `idle` \| `investigating` \| `awaiting_approval` \| `executing` \| `done` \| `error`, plus `rejected` / `cancelled` for PRD labels. Pills: gray / blue / yellow / green / red **and** text labels (Investigating, Awaiting Approval, Executing, Done, Failed, Rejected, Cancelled). Native labelled inputs and buttons; `:focus-visible`; skip link; `aria-live` on the status banner.

P1 placeholders (disabled): webhook auto-spawn, KEV/SLA badges, request-changes, audit export, chat-inside-instance.

## Out of scope (honored)

Temporal, MCP, Anthropic SDKs in the browser. Live FastAPI calls. Mobile layout. Batch approve. Functional login.

## Handoff to `@integration.eng`

Replace mock `services.ts` with `lib/api.ts` clients for SAD §4 (`POST /instances`, GET list/detail/audit, POST approve/reject). Keep poll interval 2–5s. Surface 409 stale `proposal_hash`. Wire `/login` so Approve is not available anonymously.

## Traceability notes (runtime)

Selected runtime `claude-agent-sdk` does not change the UI: no LLM token streaming to the browser (SAD). HITL sleep is displayed as a banner; durability is backend/Temporal.

## Sources

1. `project-context/1.define/prd.md` §4.3, §6.
2. `project-context/1.define/sad.md` §3, AD-5, AD-11, state machine.
3. `project-context/2.build/setup.md`.
4. `aamad.config.yml` UI + coding_standards.
5. `.cursor/agents/frontend-eng.md`.
6. `frontend-functional-spec.md`.

## Assumptions

- SAD overrides the generic persona “chat UI + Tailwind”.
- Mock store is process/module memory; full reload reseeds history (`ARLO-673`, `ARLO-674`).
- Mock approver `demo-operator` until auth is wired.
- Duplicate active ticket spawn blocked (SAD default 409).

## Open Questions

1. Approve ACL (PRD Open Question 2).
2. Cancel control vs status-only in this mock.
3. Cookie vs bearer — backend epic.

## Audit

- **Timestamp:** 2026-08-31T21:57:53Z
- **Persona id:** `frontend-eng`
- **Action:** `develop-fe` / `document-frontend`
- **Output path:** `project-context/2.build/frontend.md`
- **Resolved AAMAD_TARGET_RUNTIME:** `claude-agent-sdk` (no UI SDK; recorded for adapter consistency)
- **Config loaded:** `aamad.config.yml`
- **Tool usage:** Read (persona, PRD, SAD, setup, frontend backlog, existing `frontend/app` scaffold); Write (spec, mock services, components, CSS, routes); Shell (`npm run dev`, UTC clock).
- **Prompt Trace:** omitted. No runtime agent execution; no secrets in UI copy.
- **Model / temperature / max_tokens:** Cursor Grok 4.6 interactive session; IDE-controlled.
- **Prohibited actions honored:** no backend connection; P1 features visual stubs only.

- **Timestamp:** 2026-08-31T22:52:50Z
- **Persona id:** `frontend-eng`
- **Action:** `develop-fe` / `document-frontend` (Active Fleet vs Run History split)
- **Output path:** `project-context/2.build/frontend.md`
- **Resolved AAMAD_TARGET_RUNTIME:** `claude-agent-sdk`
- **Prompt Trace:** omitted (UI layout only).
- **Notes:** Single History table replaced by **Active Agents** (`investigating` / `awaiting_approval` / `executing`) and Run History (`done` / `rejected` / `error`=Failed / `cancelled`). Action-required banner + Review Proposal on awaiting-approval rows. Empty copy: “No active agents in flight.” Card title renamed from Active Fleet to Active Agents.
