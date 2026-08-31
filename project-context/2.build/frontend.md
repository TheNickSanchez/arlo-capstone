# Frontend epic: ARLO (backlog)

**Document type:** AAMAD frontend epic specification  
**Status:** Backlog — not implemented  
**Owner persona:** `@frontend.eng` (`frontend-eng`)  
**Depends on:** `project-context/2.build/setup.md` (complete)  
**Action when executing:** `*develop-fe` then `*document-frontend`

Replace this backlog with implementation records. Keep Sources, Assumptions, Open Questions, and Audit.

## Scope (SAD-authoritative)

This is a **control-plane dashboard**, not a chat thread. Generic persona “chat UI + Tailwind” does not apply. Follow SAD §3 and `aamad.config.yml`: `ui.theme: system`, `visual_style: minimal`, `prefer_modals: false`. Use CSS modules (or equivalent). Do not add a vendor UI kit. `lucide-react` is installed for icons if needed.

Do not wire FastAPI. Leave data as local placeholders. `@integration.eng` owns `lib/api` calls.

## Routes (already scaffolded)

| Route | Purpose |
|---|---|
| `/` | Run grid + spawn control |
| `/runs/[arloId]` | Detail: status, proposal, Approve/Reject, audit |
| `/login` | Authenticated users; no anonymous Approve |

## Tasks (sequential within this epic)

1. **Shell / layout** — Desktop-width first; system theme; keyboard-operable actions.
2. **`RunGrid`** — All runs (active + historical): `ARLO-<id>`, ticket id, status text (not color-only), created/updated, link to detail. Filter/pagination enough; no delete UX.
3. **`SpawnPanel`** — Jira or ServiceNow ticket id; in-page error on empty/invalid; copy: **no endpoint or ticket mutation until you approve**.
4. **`StatusBadge`** — Exact labels: **Investigating**, **Awaiting Approval**, **Executing**, **Done**, plus **Rejected**, **Failed**, **Cancelled**.
5. **`ProposalPanel` + `ApprovalActions` + `AuditTimeline`** — Same view; Approve/Reject in-page (not modal-first); Approve disabled unless proposal + audit visible and status is Awaiting Approval.
6. **`BannerSleeping`** — Persistent on Awaiting Approval: agent is sleeping; **no endpoint or ticket changes until you approve.**
7. **Poll hook (UI-only)** — Client poll interval 2–5s against placeholder state until integration; no full-page rewrite.
8. **P1 placeholders (visible, non-functional)** — webhook auto-spawn, KEV badges, request-changes, audit export, chat-inside-instance.

## Out of scope

Temporal, MCP, Anthropic SDKs in the browser. Mobile. Batch approve. Functional API calls.

## Handoff

Export component and status-type contracts for `@integration.eng`. Keep `frontend/lib/api.ts` as the only HTTP boundary.

## Sources

1. `project-context/1.define/sad.md` §3, UI-P0 mapping.
2. `project-context/1.define/prd.md` §4.3, §6.
3. `project-context/2.build/setup.md`.
4. `aamad.config.yml` UI keys.
5. `.cursor/agents/frontend-eng.md` (commands only; SAD overrides chat/Tailwind).

## Assumptions

- Placeholder pages in `frontend/app` are layout only.
- Auth UX is `/login`; mechanism (cookie vs bearer) is defined by `@backend.eng` and wired by `@integration.eng`.

## Open Questions

Who may Approve (hides actions later). Chat-inside-instance remains a visible stub.

## Audit

- **Timestamp:** 2026-08-31T21:20:00Z
- **Persona id:** `project-mgr` (backlog only; implementation Audit will be `frontend-eng`)
- **Action:** `document-setup` (epic backlog)
- Resolved AAMAD_TARGET_RUNTIME: claude-agent-sdk (UI has no runtime SDK; recorded for adapter consistency)
- **Prompt Trace:** omitted (no runtime agent execution)
