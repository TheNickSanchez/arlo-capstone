# Frontend Functional Spec: ARLO Endpoint Remediation Workflow

**Document type:** Frontend functional specification (operator-requested root artifact)  
**Product:** ARLO — Automated Remediation Loop Orchestrator  
**Workflow Name:** ARLO Endpoint Remediation Workflow  
**Owner persona:** `@frontend.eng` (`frontend-eng`)  
**Date:** 2026-08-31  
**Status:** Implemented (mock-backed UI; no FastAPI / Temporal / MCP wiring)

This spec describes the Next.js dashboard in `frontend/`. Product scope is taken from `project-context/1.define/prd.md`. Architecture (routes, polling, in-page HITL, CSS modules) is taken from `project-context/1.define/sad.md` §3. Implementation records live in `project-context/2.build/frontend.md`.

---

## 1. Inputs (Ticket ID / System)

Operators spawn a named instance mapped 1:1 to an **existing** Jira or ServiceNow ticket (PRD UI-P0-01, FR-P0-01). ARLO does not create tickets in MVP.

| Input | Type | Source | Validation |
|---|---|---|---|
| Ticket system | `jira` \| `servicenow` | Radio group on `/` | Required; other values rejected |
| Ticket ID | string (example `JIRA-102`) | Text field | Required; trimmed; min length 3; empty/invalid shows in-page error and **no** instance is created |
| Actor | mock `demo-operator` | Visible in chrome | Real session auth is a `/login` stub for `@integration.eng` |

Nearby copy (required): **No endpoint or ticket mutation until you approve.**

Control: **Run ARLO** submits `RunRequest` to mock `startRun`. First live instance id is `ARLO-675` (seeded history uses `ARLO-673`, `ARLO-674`). Duplicate active mapping to the same ticket+system is blocked (SAD default 409).

---

## 2. Run (State Machine & Telemetry)

### 2.1 Live FSM

```
idle → investigating → awaiting_approval → executing → done
                                         ↘ rejected (P0 Reject)
any non-terminal → error (Failed) when the mock reports a conflict/not found
done | error | rejected | cancelled → idle on Reset (history row retained)
```

| Phase | UI label (PRD vocabulary, not color-only) | Pill tone | Agent / mock behavior |
|---|---|---|---|
| `idle` | Idle | Gray | No focused run |
| `investigating` | Investigating | Blue | Read-only mock audit events; no writes |
| `awaiting_approval` | Awaiting Approval | Yellow | **Halt.** Sleep banner. Approve/Reject enabled only with a visible proposal |
| `executing` | Executing | Blue | Approved writes + validation telemetry |
| `done` | Done | Green | Terminal success; Reset available |
| `error` | Failed | Red | Terminal failure; Reset available |
| `rejected` | Rejected | Red | Terminal; no writes (history + Reject control) |
| `cancelled` | Cancelled | Gray | Reserved P0 label; no Cancel control in this mock |

Illegal transitions are product bugs. Mock `getRunStatus` advances on consecutive polls **except** it **does not** leave `awaiting_approval` until `approveRun` (HITL). That is stricter than a naive auto-cycle through `executing`/`done` and matches PRD §4.1.

`approveRun(arloId, proposalHash)` transitions `awaiting_approval` → `executing` only when the hash matches the stored proposal.

### 2.2 Telemetry

- Status banner: instance id (or “No active run”), **label**, **last updated** timestamp, colored status pill **plus** text.
- Client poll every **2.5s** while a run is non-terminal (SAD AD-11; PRD UI-P0-03). No full-page rewrite.
- Persistent sleep banner on Awaiting Approval: agent is sleeping; **no endpoint or ticket changes until you approve.**
- Mock operator id is shown in the header; Approve is not anonymous in the mock identity sense. Live auth remains unwired.

### 2.3 Controls

| Control | When shown | Keyboard |
|---|---|---|
| Ticket ID, ticket system, **Run ARLO** | Always on `/` | Native form tab order; labelled inputs; submit via button or Enter |
| **Approve Remediation** | `awaiting_approval` and proposal visible | Native button; disabled otherwise |
| **Reject** | Same as Approve (PRD UI-P0-05) | Native button |
| **Reset** | `done`, `error`, `rejected`, or `cancelled` | Native button; returns dashboard focus to idle |
| **Review Proposal** | Active Agents rows in `awaiting_approval`; also on the section action-required banner | Native button; focuses the run and scrolls to Results |

---

## 3. Results (Proposal & Execution Summary)

Shown on `/` (focused run) and `/runs/[arloId]`.

**Proposal** (`ProposalPayload`) appears once investigation completes:

- Ticket key, targeted assets, findings, enumerated write actions (system / action type / target ids), validation checks, residual risk, **diff summary**.
- Proposal hash is visible and is the argument to Approve/Reject.

**Audit** (`AuditEvent[]`) is chronological, append-only, mock-generated:

- Spawn, read MCP actions, proposal persist, HITL sleep/approve/reject, approved writes, validation, completion.
- Policy-deny events are styled as deny (not success). Secrets are never rendered.

Approve is disabled unless the proposal and audit trail are on the same view (PRD FR-P0-05 AC3).

---

## 4. Active Agents and Run History

The dashboard no longer uses a single combined History table. PRD UI-P0-02 still requires **all** runs to remain visible; they are partitioned into two sections on `/`.

### 4.1 Active Agents

Card title: **Active Agents**. Filter statuses: `investigating`, `awaiting_approval`, `executing`.

| Behavior | Rule |
|---|---|
| Empty state | **No active agents in flight.** |
| Action-required banner | Rendered at the **top** of this section when **any** in-flight row is `awaiting_approval`. Copy states that approval is required before endpoint or ticket mutation. Banner includes **Review Proposal** for the first waiting instance. |
| Row actions | **Open detail** → `/runs/[arloId]`. Rows in `awaiting_approval` also show **Review Proposal** next to Open detail (focuses the run on `/` and scrolls to Results). |
| Columns | Instance id, ticket (system + key), status badge + label, created, last updated, actions |

`idle` is not an Active Agents row; it is the focused Run panel when nothing is selected.

### 4.2 Run History

Filter statuses: `done`, `rejected`, `failed` (FSM phase `error`, UI label **Failed**), `cancelled`.

Seeded rows: `ARLO-673` (Done / JIRA-88), `ARLO-674` (Rejected / INC0010041). Empty copy if none: “No completed runs yet.”

Each row: instance id (focuses Run/Results), ticket, status, timestamps, **Open detail**. No delete UX. **Review Proposal** is not shown on terminal rows.

Layout on `/`: Inputs → **Active Agents** → Run → Results → **Run History** → future-work stubs.

---

## 5. Contracts

Canonical TypeScript definitions also live in `frontend/lib/types.ts`.

```typescript
export type TicketSystem = "jira" | "servicenow";

export type RunPhase =
  | "idle"
  | "investigating"
  | "awaiting_approval"
  | "executing"
  | "done"
  | "error"
  | "rejected"
  | "cancelled";

export interface RunRequest {
  ticketId: string;
  ticketSystem: TicketSystem;
}

export interface RunStatus {
  arloId: string;
  ticketId: string;
  ticketSystem: TicketSystem;
  phase: RunPhase;
  lastUpdated: string;
  createdAt: string;
  proposalHash?: string;
  errorMessage?: string;
}

export interface ProposalPayload {
  proposalHash: string;
  ticketKey: string;
  targetedAssets: string[];
  findings: string[];
  writeActions: Array<{
    system: "jira" | "servicenow" | "jamf" | "intune";
    actionType: string;
    targetIds: string[];
  }>;
  validationChecks: string[];
  residualRisk: string;
  diffSummary: string;
}

export interface AuditEvent {
  at: string;
  arloId: string;
  phase: RunPhase;
  kind: string;
  summary: string;
  mcpSystem?: string;
  action?: string;
  result?: "success" | "fail" | "skip" | "deny";
  policyDeny?: boolean;
}
```

### Mock service signatures (`frontend/lib/services.ts`)

```typescript
startRun(ticketId: string, ticketSystem: string): Promise<{ arlo_id: string }>
getRunStatus(arloId: string): Promise<RunStatus>
approveRun(arloId: string, proposalHash: string): Promise<RunStatus>
```

Helpers used by the UI (still mock, no HTTP): `rejectRun`, `getProposal`, `listAuditEvents`, `listRuns`.

`frontend/lib/api.ts` remains the FastAPI boundary (`API_BASE` only) for `@integration.eng`.

---

## 6. Spec Sync Checklist

| Feature | Spec section | Code | Status |
|---|---|---|---|
| Workflow name “ARLO Endpoint Remediation Workflow” | Header | Dashboard copy / this spec | Done |
| Inputs: ticket ID + system + Run ARLO | §1 | `components/SpawnPanel.tsx` | Done |
| Empty ticket in-page error, no spawn | §1 | `lib/services.ts` `startRun` | Done |
| HITL guarantee copy near spawn | §1 | `SpawnPanel` | Done |
| FSM idle → investigating → awaiting_approval → executing → done | §2.1 | `lib/fsm.ts`, `lib/services.ts` | Done |
| Halt at awaiting_approval until approve | §2.1 | `getRunStatus` + `approveRun` | Done |
| Status banner, last updated, colored pill + text label | §2.2 | `StatusBanner`, `StatusBadge` | Done |
| Pill tones: gray / blue / yellow / green / red | §2.2 | `fsm.phaseTone` + CSS | Done |
| Sleep banner on Awaiting Approval | §2.2 | `BannerSleeping` | Done |
| Poll 2–5s without full reload | §2.2 | `hooks/useArloRun.ts` 2500ms | Done |
| Approve Remediation in-page | §2.3 | `ApprovalActions` | Done |
| Reset on done / error | §2.3 | `ApprovalActions` + Dashboard | Done |
| Reject (PRD P0, in-page) | §2.3 | `rejectRun` | Done |
| Review Proposal (in-page, next to Open detail) | §2.3, §4.1 | `RunGrid` + Dashboard `handleReviewProposal` | Done |
| Proposal + diff summary | §3 | `ResultsView` `ProposalPanel` | Done |
| Step-by-step audit list | §3 | `ResultsView` `AuditTimeline` | Done |
| Active Agents table (`investigating`, `awaiting_approval`, `executing`) | §4.1 | `isActiveFleetPhase` + `RunGrid` | Done |
| Active Agents empty state “No active agents in flight.” | §4.1 | `RunGrid` `emptyMessage` | Done |
| Action-required banner when any run is `awaiting_approval` | §4.1 | `FleetActionBanner` | Done |
| Run History table (`done`, `rejected`, `failed`/`error`, `cancelled`) | §4.2 | `isHistoryPhase` + `RunGrid` | Done |
| Seeded ARLO-673 / ARLO-674; next spawn ARLO-675 | §4.2 | `lib/mock-data.ts` | Done |
| Routes `/`, `/runs/[arloId]`, `/login` | SAD §3 | `app/` | Done |
| Mock services, no network/Temporal | §5 | `lib/services.ts` | Done |
| Contracts `RunRequest`, `RunStatus`, `ProposalPayload`, `AuditEvent` | §5 | `lib/types.ts` | Done |
| Keyboard-operable inputs and buttons | §2.3 | Native controls, labels, `:focus-visible` | Done |
| P1 stubs (webhook, KEV, request-changes, export, chat) | SAD §3 | `FutureWorkStubs` | Done |
| `npm run dev` starts without errors | Delivery | `frontend/` Next.js 15 | Done (verified) |
| FastAPI / Temporal / MCP not called from UI | Persona | `lib/api.ts` unused by UI | Done |

---

## Sources

1. `project-context/1.define/prd.md` — §4.1 lifecycle, §4.3 dashboard UI-P0-01–05, §6 a11y and sleep copy, FR-P0-01/05/08.
2. `project-context/1.define/sad.md` — §3 frontend stack/routes/components; AD-11 polling; state machine; UI never talks to Temporal/MCP/Anthropic.
3. `project-context/2.build/setup.md` — Next.js App Router scaffold, `lucide-react` present, CSS-modules guidance in frontend backlog.
4. `aamad.config.yml` — `ui.theme: system`, `visual_style: minimal`, `prefer_modals: false`, `coding_standards.type_checking: true`, `max_file_lines: 400`.
5. `.cursor/agents/frontend-eng.md` — UI only; no backend connection; log in `frontend.md`.
6. Operator request (2026-08-31): root `frontend-functional-spec.md`, mock `services.ts`, FSM, banner, controls, audit/results, checklist; follow-up to split Active Fleet vs Run History.

## Assumptions

- Generic persona “chat UI + Tailwind” is overridden by SAD §3 (control-plane dashboard, CSS modules, system theme).
- Mock HITL halt at `awaiting_approval` is required even though a literal consecutive-call cycle listed `executing`/`done` without a gate. PRD is authoritative.
- `rejected` and `cancelled` extend the six live FSM states so **Run History** can show PRD P0 labels. Cancel is not a button in this mock. UI label **Failed** maps from phase `error` (spec “failed”).
- Mock identity `demo-operator` stands in for attributable Approve until `/login` is wired.
- In-memory mock store resets on full page reload; durability is a backend/Temporal concern.
- Duplicate active ticket spawn is blocked (SAD default) pending PRD Open Question 3.

## Open Questions

1. Who may Approve (PRD Open Question 2) — UI currently shows actions to the mock operator.
2. Whether Cancel should be an in-page control in this mock (P0 status exists; control deferred to integration/backend Signal).
3. Chat-inside-instance remains a disabled stub (P1).

## Audit

- **Timestamp:** 2026-08-31T21:57:53Z
- **Persona id:** `frontend-eng`
- **Action:** `develop-fe` (functional spec + mock dashboard)
- **Output path:** `frontend-functional-spec.md`
- **Resolved AAMAD_TARGET_RUNTIME:** `claude-agent-sdk` (UI has no runtime SDK; recorded for adapter consistency)
- **Config loaded:** `aamad.config.yml` (system/minimal UI, prefer_modals false, type checking, max_file_lines 400)
- **Prompt Trace:** omitted. Frontend mock UI only; no runtime agent execution against Jira/ServiceNow/Jamf/Intune; no secret-bearing prompts.
- **Model / temperature / max_tokens:** Cursor Grok 4.6 interactive session; temperature/max_tokens not independently set by this persona (IDE-controlled).
- **Write method:** direct write of spec after code alignment; checklist updated after `npm run dev` verification.
- **Prohibited actions honored:** no FastAPI/Temporal/MCP/Anthropic client in the UI; P1 features are visible stubs only.

- **Timestamp:** 2026-08-31T22:52:50Z
- **Persona id:** `frontend-eng`
- **Action:** `develop-fe` (split Active Fleet / Run History; spec sync)
- **Output path:** `frontend-functional-spec.md`
- **Resolved AAMAD_TARGET_RUNTIME:** `claude-agent-sdk`
- **Prompt Trace:** omitted (UI-only layout change; no runtime agent execution).
- **Write method:** in-place spec update after `RunGrid` / `Dashboard` split.
