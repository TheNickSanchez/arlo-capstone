# QA epic: ARLO (backlog)

**Document type:** AAMAD QA epic specification  
**Status:** Backlog — blocked on integration  
**Owner persona:** `@qa.eng` (`qa-eng`)  
**Depends on:** implemented `frontend.md`, `backend.md`, `integration.md`  
**Action when executing:** `*test-unit` → `*test-integration` → `*qa` / `*verify-flow` → `*log-defects` → `*future-work`

Replace this backlog with results. Keep Unit / Integration / Smoke sections plus Sources, Assumptions, Open Questions, and Audit.

`aamad.config.yml`: `require_unit_tests: true`, `require_integration_tests: true`, `map_to_acceptance_criteria: true`. Map checks to PRD FR-P0-* / UI-P0-* (no `user-stories/` directory at setup).

## Unit (planned)

- Proposal hash stability (canonical JSON).
- Illegal status transitions (SAD state machine).
- PEP deny matrix (write tools in Investigating; off-list tools in Executing).
- API validation (missing ticket id → 400; stale hash → 409).

## Integration (planned)

- FastAPI + PostgreSQL (spawn, list, audit append-only).
- Temporal test env (time-skipping): Signal wait does not occupy a worker; Approve schedules `execute_approved`.
- MCP **stubs**: reads in Investigating; writes only after approval. Stubs must not report write success that skipped the gate.
- Dual instance: two Workflows, different phases, no crossed mappings/audit (FR-P0-09). Configurable cap default 5; demo bar ≥ 2.

## Smoke / acceptance (planned)

Fixture ticket → Awaiting Approval → Approve → Done **and** a Reject path. Dashboard shows named ids, sleep banner, audit of reads before HITL and writes only after. Unapproved mutations = **zero**. HITL bypass blocked 100% (FR-P0-04, FR-P0-10).

## Runtime adapter checks

Hooks fire; `allowed_tools` per phase; Diagnostic on missing MCP; `AAMAD_TARGET_RUNTIME=claude-agent-sdk`; no CrewAI YAML.

## Future work (do not test as MVP)

Webhook auto-spawn, request-changes, KEV badges, batch approve, AppSec/git, Temporal Cloud, mobile.

## Handoff

After results (pass or explicitly scoped gaps), recommend `@security.eng` before Deliver.

## Sources

1. `project-context/1.define/sad.md` §9.
2. `project-context/1.define/prd.md` §4, §5, §7.
3. `project-context/2.build/setup.md` and (when present) implementation artifacts.
4. `aamad.config.yml` testing keys.
5. `.cursor/agents/qa-eng.md`.

## Assumptions

- No tests were run in setup (nothing to accept yet).
- User stories were not produced; AC mapping uses PRD FR-P0 / UI-P0 ids.

## Open Questions

Live MCP vs stubs for demo (PRD Open Question 9). Validation failure vs close-on-partial (default: do not close).

## Audit

- **Timestamp:** 2026-08-31T21:20:00Z
- **Persona id:** `project-mgr` (backlog only; results Audit will be `qa-eng`)
- **Action:** `document-setup` (epic backlog)
- Resolved AAMAD_TARGET_RUNTIME: claude-agent-sdk
- **Prompt Trace:** omitted (no runtime agent execution)
