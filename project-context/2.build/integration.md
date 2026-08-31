# Integration epic: ARLO (backlog)

**Document type:** AAMAD integration epic specification  
**Status:** Backlog — blocked on frontend + backend implementation  
**Owner persona:** `@integration.eng` (`integration-eng`)  
**Depends on:** `frontend.md` and `backend.md` implementation (not just this backlog)  
**Action when executing:** `*integrate-api` then `*verify-messageflow` then `*log-integration`

Replace this backlog with implementation records. Keep Sources, Assumptions, Open Questions, and Audit.

## Scope (SAD-authoritative)

Generic persona “chat round-trip” does not apply. Wire the **dashboard** to FastAPI. The UI never talks to Temporal, MCP, or Anthropic.

MVP list/detail are request/response. Do not require LLM token streaming to the browser.

## Tasks (sequential within this epic)

1. **Typed client** — Expand `frontend/lib/api.ts` for SAD §4 paths. Base URL `NEXT_PUBLIC_API_BASE_URL`.
2. **Auth** — Login → session cookie or signed header required on all `/api/v1` except `/health` and `/ready`. Unauthenticated Approve must fail.
3. **Spawn** — `POST /instances` → row appears in grid in **< 3s** (excluding first MCP auth). Invalid ticket → in-page error, no row.
4. **Poll** — Grid and detail every **2–5s** while non-terminal; last-known status while in flight.
5. **Approve / Reject / Cancel** — Send `proposal_hash`. Persist-then-Signal is backend; UI must surface 409 conflict (stale hash) without implying success.
6. **Audit** — `GET .../audit` chronological; never render secrets.
7. **Error envelope** — Map `validation_error`, `conflict`, `not_found`, `unauthenticated`, `policy_deny`, `upstream_unavailable`.
8. **CORS / cookies** — Compose: UI `:3000`, API `:8000`. Document credentials mode.
9. **Verify** — Spawn → Awaiting Approval (fixture/stub) → Approve or Reject reflected in UI without full reload.

## Out of scope

Implementing MCP servers, Temporal Workflows, or new product features. P1 webhook auto-spawn.

## Handoff

`@qa.eng` uses the wired path for smoke. Record any contract drift vs SAD in this file.

## Sources

1. `project-context/1.define/sad.md` §3 API client boundary, §4, §6 sequence diagram, AD-11 polling.
2. `project-context/1.define/prd.md` UI-P0-01–05, FR-P0-01, FR-P0-05, FR-P0-08.
3. `project-context/2.build/setup.md`, `frontend.md`, `backend.md`.
4. `.cursor/agents/integration-eng.md` (commands only; SAD overrides chat-only scope).

## Assumptions

- Polling satisfies UI-P0-03 for MVP (no SSE required).
- Duplicate spawn 409 until product amends Open Question 3.

## Open Questions

Webhook-originated approval vs dashboard-only (SAD Open Question 13). Cookie vs bearer final choice from `@backend.eng`.

## Audit

- **Timestamp:** 2026-08-31T21:20:00Z
- **Persona id:** `project-mgr` (backlog only; implementation Audit will be `integration-eng`)
- **Action:** `document-setup` (epic backlog)
- Resolved AAMAD_TARGET_RUNTIME: claude-agent-sdk
- **Prompt Trace:** omitted (no runtime agent execution)
