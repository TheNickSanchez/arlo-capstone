# Security epic: ARLO (backlog)

**Document type:** AAMAD security assessment specification  
**Status:** Backlog — blocked on `qa.md` results  
**Owner persona:** `@security.eng` (`security-eng`)  
**Depends on:** `qa.md` plus implemented backend/frontend/integration  
**Action when executing:** `*assess-security` (`*scan-secrets`, `*review-deps` as needed) then `*document-security`

`aamad.config.yml` sets `security.require_security_assessment: true`. This file is required before Deliver. Do not modify application business logic; route fixes to owning personas.

Replace this backlog with severity-ranked findings (Critical / High / Medium / Low / Info). Keep Sources, Assumptions, Open Questions, and Audit.

## Planned assessment surfaces (SAD §8)

1. **Secrets** — No committed `.env` values; traces/audit/UI/Jira/CHG redaction; `.env.example` names only.
2. **HITL enforcement layers** — Temporal (no Execution Activity without Approve Signal); SDK `allowed_tools`; `PreToolUse` PEP; MCP catalog deny-by-default.
3. **AuthN/AuthZ** — No anonymous Approve; attributable `actor_id`; webhook HMAC before Signal.
4. **Injection / validation** — Parameterized SQL; ticket id and enum validation; canonical proposal hash.
5. **Excessive Agency (OWASP)** — Write tools absent until approval; fail closed; Intune sync classification (PRD Open Question 5).
6. **Dependencies** — `npm audit` (2 findings recorded at setup, 1 high); Python supply chain (`claude-agent-sdk`, `temporalio`, FastAPI).
7. **LiteLLM** — Virtual key vs master key vs upstream key separation; `ANTHROPIC_BASE_URL` not logged.

## Out of scope unless PRD expands

Enterprise IAM/SSO, network segmentation, production pen-test, EU AI Act high-risk declaration.

## Handoff

Critical/High mitigated or explicitly accepted before `@devops.eng` `*prepare-release`.

## Sources

1. `project-context/1.define/sad.md` §8.
2. `project-context/1.define/prd.md` §3.1 guardrails, §5 Security.
3. `project-context/2.build/setup.md`.
4. `aamad.config.yml` security keys.
5. `.cursor/agents/security-eng.md`.

## Assumptions

- Assessment is not started; this is a backlog.
- Capstone is not a declared EU AI Act high-risk deployment; HITL + audit still designed for oversight review.

## Open Questions

Intune sync read vs mutation. Who may Approve. EU personal device data in demo (PRD Open Question 12). Trademark “ARLO” not in this epic.

## Audit

- **Timestamp:** 2026-08-31T21:20:00Z
- **Persona id:** `project-mgr` (backlog only; assessment Audit will be `security-eng`)
- **Action:** `document-setup` (epic backlog)
- Resolved AAMAD_TARGET_RUNTIME: claude-agent-sdk
- **Prompt Trace:** omitted (no runtime agent execution)
