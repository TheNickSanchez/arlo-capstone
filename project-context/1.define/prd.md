# Product Requirements Document: ARLO (Automated Remediation Loop Orchestrator)

**Document type:** AAMAD Product Requirements Document (PRD)  
**Product:** ARLO — Automated Remediation Loop Orchestrator  
**Phase:** 1 Define  
**Owner persona:** `@product-mgr` (`product-mgr`)  
**Date:** 2026-08-31  
**Status:** MVP-authoritative for product scope (supersedes MRD domain where they conflict; see Assumptions)

## Context & Instructions

This PRD defines the MVP for a multi-agent system that orchestrates **human-gated enterprise IT and endpoint remediations**. Each work item is a named ARLO instance bound to a Jira or ServiceNow ticket. ARLO investigates with read-only MCP actions, proposes a remediation plan, **sleeps at an approval gate**, and only then may execute state-changing actions on endpoints or tickets.

**Deep Research Report / MRD:** `project-context/1.define/mrd.md` (2026-08-31). The MRD researched an **AppSec / Jira vulnerability-code** concept (draft PRs, scanners, pre-write HITL on source). This PRD **re-scopes the product** to **Enterprise IT & Endpoint Remediation** per operator instruction on 2026-08-31. Transferable MRD findings (HITL as architecture, named concurrent instances, portfolio dashboard, decision history, least-privilege tools, `claude-agent-sdk` runtime) are retained. AppSec-specific scope (git write, draft PR, SAST/SCA) is **out of MVP** and listed under Future Work / Open Questions.

**System Description:** N/A — `project-context/1.define/system-description.md` was not produced. Operator supplied a complete product definition (persona, MCP authorized actions, HITL lifecycle, dashboard). Formal `*elicit-requirements` skipped with rationale under Assumptions.

**System Concept:** One hardened agent blueprint (“ARLO”) is cloned into many durable, ticket-mapped instances (`ARLO-675`, `ARLO-676`, …). Each instance runs a stateful HITL loop: Trigger → Investigation & Research → Proposal/Summary Generation → Approval Gate Pause (agent sleeps) → Human Approves → Execution → Validation & Ticket Closure. MCP servers expose Jira, ServiceNow, Jamf, and Intune **authorized actions only** (this PRD does not specify MCP server implementation).

**Selected Runtime:** `claude-agent-sdk` (`aamad.config.yml` `runtime.target`). Environment variable `AAMAD_TARGET_RUNTIME` was **unset** at PRD authoring; adapter-registry would default to `crewai` if env is used without export. Build/CI **must** set `AAMAD_TARGET_RUNTIME=claude-agent-sdk` so env and config cannot diverge. Runtime constrains Phase 2 implementation conventions; it is not the product definition.

---

### 1. Executive Summary

**Problem Statement** (Research-backed where MRD transfers; domain from operator):

* **Specific operator problem.** Enterprise IT, desktop, and endpoint teams receive a continuous stream of Jira and ServiceNow tickets for device non-compliance, configuration drift, failed profiles/policies, and related endpoint incidents. Today an operator context-switches across Jira or ITSM, ServiceNow CMDB/change, Jamf (Apple), and Intune (Windows/mobile), assembles evidence by hand, drafts a plan, waits on change discipline, then clicks remediations in MDM consoles. Nothing in that loop is a single auditable “run.” Fully autonomous agents that apply profiles, scripts, or policies without a human gate are unacceptable: endpoint mutation and ticket mutation are production-impacting.

* **Quantified impact and pain points.** Adjacent evidence (not claimed as ARLO’s own measured baseline):
  * Verizon 2026 DBIR: vulnerability exploitation was the leading initial-access vector at **31%** of breaches (up from 20%); CISA KEV full-remediation rate fell **38% → 26%**; median time-to-full-resolution rose **32 → 43 days** (MRD Sources 1–4).
  * IBM 2025 Cost of a Data Breach: global average **USD 4.44 million**; extensive AI/automation in security operations associated with **USD 1.9 million** lower breach cost (MRD Sources 11–12). These figures support executive language for **governed** automation, not unsupervised endpoint writes.
  * Industry UEM practice in 2026 commonly splits **Intune (Windows / Microsoft-centric)** and **Jamf Pro (Apple depth)** as a two-console estate, with ITSM/change remaining in ServiceNow (Tech Vendor Index 2026 endpoint comparison; Tanium/ServiceNow ITX positioning). Ticket-to-console swivel is therefore structural, not a tooling accident.
  * “Autonomous IT” vendors (e.g. Tanium AI Agent / ITX for ServiceNow) market reduced MTTR by acting from ITSM — and still surface **human review of recommended actions** before deploy in documented flows. ARLO’s capstone differentiator is **mandatory sleep-at-gate** plus a **fleet dashboard of named runs**, not a claim of novel MDM APIs.

* **Target market or user population scope.** Capstone / internal operational tool for enterprise IT & endpoint remediation operators (service desk leads, MDM admins, change-aware IT ops, and managers watching in-flight work). Commercial TAM from the MRD (ASPM / DevSecOps / AppSec) is **not** the planning envelope for this PRD. Geographic/commercial expansion is N/A for MVP (see §9 and Assumptions).

**Solution Overview** (Evidence-based):

* **Multi-agent system approach and unique value proposition.** ARLO is an **Enterprise IT & Endpoint Remediation Specialist** blueprint. Operators spin up a **new instance per ticket**. The instance investigates using **read-authorized** MCP actions, produces a proposal and discovery summary, then **pauses (sleeps)** until a human approves. Only after an approval record exists may the instance execute **approved** Jamf/Intune remediations, ServiceNow change-request tracking, and Jira ticket mutations (including close). Every step is written to an audit log.

* **Key differentiators vs alternatives.**
  * vs **manual MDM + ITSM consoles:** one named loop per ticket, durable state, and a single approval card instead of four tools.
  * vs **fully autonomous endpoint agents:** ARLO **never** executes a state-changing action on an endpoint or ticket without explicit human approval (architectural guardrail, not a prompt suggestion).
  * vs **single chat session (Cursor/Claude in IDE):** many concurrent instances (`ARLO-675`, `ARLO-676`) with portfolio status; HITL sleep does not block sibling runs.
  * vs **scanner-tied AppSec autofix (MRD competitors):** out of category. ARLO MVP does not patch application source code.

* **Expected operational outcomes and success metrics.** Reduce time from ticket-open to **HITL-ready proposal**; reduce time from **approval to validated closure**; keep **unapproved mutations at zero**; give managers a real-time grid of Investigating / Awaiting Approval / Executing / Done. Formal KPIs in §7.

**Strategic Rationale:**

* **Why multi-agent (instance fan-out) is optimal.** Endpoint queues are concurrent: dozens of devices and tickets in flight. A single blocking agent serializes HITL and hides sibling progress (MRD §2). ARLO’s model is **one blueprint, N isolated instances**, each with its own lifecycle phase, approval queue entry, and audit trail — not a researcher–writer sequential crew for a single chat.

* **Business case / operational value (capstone).** Reclaim swivel-chair time; enforce change discipline (ServiceNow CHG check/create for tracking); produce an evidence pack (compliance reads, logs, proposal, approval, execution, validation) on the ticket and in the dashboard. Do not claim IBM-scale ROI as ARLO’s audited result.

* **Market timing and competitive positioning.** N/A as a go-to-market motion (capstone). Category positioning for architecture and QA: **HITL endpoint remediation orchestrator** adjacent to ITSM + UEM, not AST/ASPM. Anti-message: “autonomous production patching of endpoints.”

---

### 2. Market Context & User Analysis

**Target Market / Users** (From operator definition + transferable MRD UX; AppSec TAM not reused as ARLO’s market):

* **Primary user personas**

  | Persona | Characteristics | Primary job-to-be-done |
  |---|---|---|
  | **Endpoint / MDM Administrator** | Owns Jamf Pro and/or Intune; can interpret compliance, profiles, policies, and device logs; accountable for fleet health | Approve or reject ARLO’s proposed Jamf/Intune actions with enough evidence to be safe |
  | **IT Support / Service Desk Engineer** | Lives in Jira and/or ServiceNow; first to see new tickets; limited MDM rights | Spawn an ARLO instance on a ticket; watch Investigating → Awaiting Approval; hand the approval card to the right owner |
  | **Change / IT Operations Lead** | Owns change hygiene; needs CHG existence and tracking before endpoint mutation | Confirm ARLO checked for existing change requests and created tracking CHGs only after approval |
  | **IT / Engineering Manager** | Does not open 40 MDM consoles; needs portfolio progress | Grid of all historical and active runs (`ARLO-675`, …), status, and who approved what |

* **Market segment size and growth projections.** N/A as a commercial forecast for this capstone. MRD ASPM/DevSecOps dollar figures **must not** be cited as ARLO endpoint TAM. Qualitative UEM context: enterprises with material Apple and Windows fleets often run **Jamf + Intune** (two-console), with ServiceNow as CMDB/change (2026 UEM comparison literature). That split is why ARLO’s MCP **authorized action** set includes both MDMs plus ITSM.

* **Geographic focus and expansion.** N/A for MVP (local/capstone deployment).

**User Needs Analysis:**

* **Critical pain points and unmet needs.**
  * Evidence for a single ticket is scattered (ticket text, CMDB/asset, Jamf compliance/logs, Intune compliance/sync).
  * Fear of rubber-stamping AI and of silent MDM writes (OWASP LLM Excessive Agency; MRD HITL rationale remains valid for **any** high-impact tool).
  * No named, durable “run” identity matching the ticket (operators lose state when a chat ends).
  * Managers cannot see Investigating vs stuck-on-human vs Executing vs Done across the queue.
  * Change process is skipped or duplicated: remediations fire without a tracking CHG, or CHGs exist but MDM work is disconnected.

* **User journey mapping and interaction patterns.** See §4 **Stateful Remediation Lifecycle**. Happy path: ticket appears → user maps a new ARLO instance to that ticket → instance investigates (reads only) → proposal appears in UI (and is eligible to post as a discovery summary only as a **gated** ticket write) → instance **sleeps** → human approves in the dashboard → instance executes approved MCP writes → validates device state → closes or transitions the ticket per the approved plan → status **Done**. Manager path: land on the run grid, filter by status, open audit log — **do not require a chat per ticket**.

* **Adoption barriers and success factors.**
  * Barriers: distrust of endpoint mutation; another dashboard; unclear who may approve; MCP/org credential setup; token cost at concurrency.
  * Success factors: default-deny writes; copy that states **“no endpoint or ticket mutation until you approve”**; instance IDs `ARLO-<n>` in UI and logs; immutable audit log; time-to-proposal in minutes for a typical ticket; durable sleep (closing the browser does not skip the gate or lose the run).

**Competitive Landscape** (optional; MRD AppSec table is out of category — replaced for this domain):

* **Direct / analogous workflows:** manual Jamf + Intune + Jira/SNOW; ServiceNow + real-time endpoint platforms (e.g. Tanium ITX / AI Agent for ServiceNow) that investigate and **recommend** actions with deploy-from-ITSM; MDM-native scripts and remediation policies without a per-ticket agent identity.
* **Feature gaps ARLO targets:** (1) one blueprint infinitely instantiated per ticket, (2) **mandatory pre-mutation HITL with agent sleep**, (3) unified run grid + step-level audit of reasoning and actions, (4) scanner-agnostic / MDM-agnostic **orchestration** (Jamf and Intune as peers).
* **Pricing benchmarks.** N/A (capstone). Do not position against Copilot Autofix / Snyk Agent Fix as peers; those are AppSec products from the MRD.

---

### 3. Technical Requirements & Architecture

#### 3.1 Agent Persona & Scope

**Product persona (single blueprint, many instances).**

| Field | Requirement |
|---|---|
| **Name** | ARLO (Automated Remediation Loop Orchestrator) |
| **Role** | **Enterprise IT & Endpoint Remediation Specialist** |
| **Identity pattern** | One blueprint; each running instance is named `ARLO-<id>` (example: `ARLO-675`, `ARLO-676`) and is **mapped 1:1 to a specific Jira or ServiceNow ticket** for the life of the run |
| **Goal** | Investigate ticket-bound endpoint/IT issues using authorized **read** actions; produce a grounded proposal; **stop**; after explicit human approval, execute **only the approved** MCP mutations; validate; close/transition the ticket per the approved plan; record an audit trail |
| **Non-goals (MVP)** | Application source-code patching, git/PR workflows, original SAST/SCA, EDR kill-chain response, identity provisioning, network ACL changes, production deploy of unrelated apps, autonomous merge/reboot-storms, any mutation that was not in the approved proposal |

**Strict guardrails (non-negotiable, architectural — not prompt-only):**

1. ARLO **must NEVER** execute a **state-changing** action on an **endpoint** or a **ticket** without **explicit human approval** recorded against that instance.
2. **State-changing** includes, without limitation: applying Jamf configuration profiles or scripts; applying Intune policies or remediations; creating ServiceNow change requests; posting Jira comments/summaries; transitioning Jira or ServiceNow ticket statuses; closing tickets. **Read** actions listed in §3.3 may run in Investigation without that approval.
3. Approval is **instance-scoped** and **proposal-scoped**: executing a different action than the approved plan is a new mutation and is forbidden until a new approval.
4. Rejection, timeout, cancel, or missing approval record ⇒ **no MCP write tools**. Fail closed. Never fail open.
5. The Approval Gate is a **durable sleep**: the instance remains in **Awaiting Approval**; the agent does not poll-mutate, does not “helpfully” continue, and does not expire into execution. Process or UI restart must restore the same gate.
6. Humans remain responsible for the production outcome. ARLO does not imply legal or policy sign-off beyond the recorded approver identity.

**Intune “sync device status” classification (MVP):** treated as a **read-side refresh** (pull latest compliance/inventory into the investigation context), **not** as a remediation. If platform sync is later judged a mutation by Security/Architecture, it moves behind the HITL gate (Open Question).

#### 3.2 Runtime & Agent Specifications

Aligned with selected runtime **`claude-agent-sdk`** (adapter: `.cursor/rules/adapter-claude-agent-sdk.mdc`). Product behavior must hold even if a later runtime swap occurs.

* **Agent roles and responsibilities (workflow-derived).**
  * **ARLO Coordinator (per instance):** owns lifecycle phase, HITL sleep, audit events, and which MCP actions are enabled.
  * **Investigation specialist (same instance or subagent):** read-only Jira/SNOW/Jamf/Intune authorized reads; evidence pack.
  * **Proposal specialist:** turns evidence into a human-reviewable summary and explicit action list (no writes).
  * **Execution specialist:** after approval token, runs **only** approved write actions.
  * **Validation specialist:** re-reads compliance/asset state; recommends ticket close/transition (writes still require the approved plan to include those ticket actions).

* **Collaboration patterns.** **Sequential lifecycle** per instance (not a hierarchical manager rewriting policy). **Concurrent fan-out** across instances. Delegation to subagents is allowed for isolation of read vs write tool sets; **delegation must not bypass HITL**. `allow_delegation` style unbounded managers are out of MVP.

* **Task / turn orchestration and delegation boundaries.**
  * Explicit per-instance **turn and token budgets** (no implicit unbounded loops).
  * Write-capable tools **absent from `allowed_tools`** until an approval record exists; `PreToolUse` (or equivalent policy enforcement point **outside the model**) denies writes otherwise.
  * Session resume is **required** for HITL sleep (retain gate, proposal, and audit). Session fork is out of MVP unless SAD justifies it.

* **Adapter-shaped fields (illustrative for Claude Agent SDK; SAD maps 1:1):**

  | Concept | MVP expectation |
  |---|---|
  | Role / goal / backstory | Persona in §3.1; backstory must include the guardrails verbatim in operator-facing docs |
  | Tools | Least-privilege per phase (read set vs write set) |
  | Memory | Default off for reproducibility except **durable instance state** (phase, proposal, approval, audit) which is product state, not optional LLM memory |
  | Delegation | Subagents only with stricter or equal tool policy |
  | Controls | `max_iter` / turn cap, token cap, timeout; hooks `PreToolUse` / `PostToolUse` for PEP and audit |

#### 3.3 Core Agent Definitions

* **agent:** `arlo` (blueprint)  
  * **role:** "Enterprise IT & Endpoint Remediation Specialist"  
  * **goal:** "For the mapped ticket, complete the HITL remediation loop without any unapproved endpoint or ticket mutation."  
  * **tools (logical, not implementation):** Jira read; ServiceNow CHG query + asset read; Jamf compliance read + log fetch; Intune compliance read + device status sync; **after approval:** Jira post summary / transition / close; ServiceNow create CHG; Jamf apply approved profile or script; Intune apply approved policy or remediation.  
  * **runtime notes:** Isolated SDK session (or equivalent) per `ARLO-<id>`; write tools gated by HITL; traces to Build-phase log path with redaction; Python primary language (`aamad.config.yml`).

* **agent:** `arlo-investigator` (optional subagent)  
  * **role:** "Read-only evidence gatherer"  
  * **goal:** "Assemble ticket, asset, and device compliance/log context without mutating anything."  
  * **tools:** Read-only MCP authorized actions only.  
  * **runtime notes:** No write tools in `allowed_tools` at any time.

* **agent:** `arlo-executor` (optional subagent)  
  * **role:** "Approved-plan executor"  
  * **goal:** "Apply the human-approved action list exactly; stop on first unauthorized or failed mutation."  
  * **tools:** Write MCP actions listed in the approval record only.  
  * **runtime notes:** Must not start without approval record; idempotent retries; halt on policy deny.

#### 3.4 MCP Integration Scope (authorized actions only)

This subsection is **product authorization**, not MCP server design, transport, auth implementation, or vendor API mapping. SAD/backend may bind these actions to MCP tools; this PRD does not.

**Global MCP rules:**

* ARLO may only perform actions listed below. Anything not listed is **out of scope** (deny).
* **Read** actions: allowed in **Investigation & Research** (and Validation reads) without HITL.
* **Write / state-changing** actions: allowed **only in Execution or Validation & Ticket Closure** and **only if present on the approved proposal** for that instance.

##### Jira (work-item system of record, with ServiceNow as alternate trigger)

| Action | Type | When allowed | Purpose |
|---|---|---|---|
| Read ticket context | Read | Investigation, Validation | Title, description, comments, status, assignee, linked identifiers, attachments metadata needed to ground the proposal |
| Post discovery summaries | Write | After HITL, as part of the approved plan | Publish investigation/proposal summary onto the ticket for audit outside ARLO |
| Transition ticket statuses | Write | After HITL, as part of the approved plan | Move the ticket along the agreed workflow (e.g. In Progress → Done) |
| Close tickets | Write | After HITL, typically after Validation success | Close when validation criteria in the approved plan are met |

##### ServiceNow (change tracking and asset context)

| Action | Type | When allowed | Purpose |
|---|---|---|---|
| Check for existing change requests | Read | Investigation | Avoid duplicate CHGs; cite existing CHG in the proposal |
| Create new change requests for tracking | Write | After HITL, as part of the approved plan | Tracking artifact for the approved endpoint work — not a substitute for HITL |
| Read asset data | Read | Investigation, Validation | CI/asset fields needed to target the correct device and owner |

##### Jamf (Apple endpoints)

| Action | Type | When allowed | Purpose |
|---|---|---|---|
| Read device compliance state | Read | Investigation, Validation | Compliance status, failed smart groups / policy flags as exposed to ARLO |
| Fetch device logs | Read | Investigation | Evidence for root-cause and proposal grounding |
| Apply approved configuration profiles or scripts | Write | After HITL, **only** the profile/script identifiers in the approved plan | Remediate Apple endpoint state |

##### Intune (Windows / mobile endpoints)

| Action | Type | When allowed | Purpose |
|---|---|---|---|
| Read device compliance state | Read | Investigation, Validation | Compliance and policy posture |
| Sync device status | Read-side refresh (MVP) | Investigation, Validation | Refresh latest device/compliance view; not a remediation |
| Apply approved policies or remediations | Write | After HITL, **only** the policy/remediation identifiers in the approved plan | Remediate Windows/mobile endpoint state |

**Explicitly unauthorized (non-exhaustive, MVP deny):** wipe/retire/delete device; lock/lost-mode; disable account; rotate secrets; dump credentials; export full disk; change IdP groups; modify firewall/network gear; run arbitrary unsigned scripts not named in the approved plan; expand scope to devices not identified in the ticket/proposal.

#### 3.5 Integration Requirements

* **Required external services (logical).** Jira; ServiceNow; Jamf; Intune; LLM provider for the selected runtime (secret **name** `ANTHROPIC_API_KEY` and optional org gateway/base URL per adapter — values never in artifacts).
* **Database and storage (MVP).** Durable store for: instance id, mapped ticket (system + key), phase/status, proposal document, approval/rejection record (actor, timestamp, rationale), audit log events, artifact links. Local/project store is sufficient for capstone; multi-tenant SaaS deferred.
* **Authentication and security.** Secrets only via environment (`.env.example` names). Least-privilege tokens per system. `security.require_security_assessment: true` — `@security.eng` assessment required before Deliver. No secrets in Prompt Trace, Jira comments, CHG text, or audit UI.
* **Performance and scalability targets.** See §5. MVP: demonstrate **≥2 concurrent** isolated instances; document a configurable max-concurrency cap.

#### 3.6 Infrastructure Specifications

* **Cloud / hosting (MVP).** Smallest AAMAD-appropriate target: local or single-service/compose. No live production deploy without operator authorization (Deliver-phase rule).
* **Compute and memory.** Laptop/dev-class sufficient; cost driver is LLM tokens × concurrent instances, not cluster size.
* **Network and security.** Outbound to Jira, ServiceNow, Jamf, Intune, and model gateway only as configured. Fail closed if a required MCP/tool is unauthorized or unavailable (Diagnostic; do not skip HITL).
* **Monitoring and logging.** Instance lifecycle telemetry is a **product feature**: spawn, phase changes, tool attempts, policy denies, HITL wait, approve/reject, execution results, validation, close, fail, cancel. Persist traces under `project-context/2.build/logs` during Build; redact secrets.

---

### 4. Functional Requirements

#### 4.1 The Stateful Remediation Lifecycle (HITL)

Exact functional flow (P0). Each instance is a **state machine**. Illegal transitions are product bugs.

```
Trigger (New Jira/SNOW ticket)
    → Investigation & Research
    → Proposal / Summary Generation
    → Approval Gate Pause (Agent sleeps)
    → Human Approves
    → Execution
    → Validation & Ticket Closure
```

**Phase contracts:**

| Phase | Status shown in UI (P0 labels) | Agent behavior | Allowed MCP classes | Exit criteria |
|---|---|---|---|---|
| **Trigger** | (ephemeral → Investigating) | Bind instance `ARLO-<id>` to exactly one ticket (Jira **or** ServiceNow) | None required | Mapping persisted; run visible on the grid |
| **Investigation & Research** | **Investigating** | Gather evidence; reason in audit log | **Reads only** (Jira context; SNOW existing CHG + assets; Jamf compliance + logs; Intune compliance + status sync) | Evidence pack complete or halt with Diagnostic if blocking reads fail |
| **Proposal / Summary Generation** | **Investigating** (until proposal persisted) | Produce human-reviewable summary + **explicit action list** (each action maps to an authorized write in §3.4) | Reads if needed; **no writes** | Proposal stored on the instance |
| **Approval Gate Pause** | **Awaiting Approval** | **Agent sleeps.** No tool writes. No countdown-to-auto-approve. Durable across restart | None (writes) | Human **Approve** or **Reject** (or Cancel) |
| **Human Approves** | **Awaiting Approval** → **Executing** | Record approver identity, timestamp, and the frozen approved action list | None until record committed | Approval record exists and matches proposal hash/id |
| **Execution** | **Executing** | Perform **only** approved writes (Jamf/Intune applies; SNOW create CHG if approved; Jira post summary / transitions if approved) | Approved writes only | All approved actions attempted; per-action success/fail in audit |
| **Validation & Ticket Closure** | **Executing** then **Done** | Re-read compliance/asset; if validation criteria in the approved plan pass, perform approved close/transition | Validation **reads**; ticket close/transition only if those writes were approved | Terminal **Done** (success) or terminal failure status (see below) |

**Human Rejects (P0):** no execution; persist rejection rationale; instance terminal (recommended UI status **Rejected**, see statuses). Ticket and endpoints unchanged by ARLO.

**Sleep semantics (P0):** “Agent sleeps” means **orchestrated pause**, not silent crash. The instance remains queryable; audit log shows last reasoning step and “waiting for human approval.” Waking occurs **only** on Approve / Reject / Cancel by an authorized user.

**Trigger rules (P0):** A user **spins up** a new ARLO instance from the UI and maps it to a specific existing ticket. Automatic webhook auto-spawn on every new ticket is **P1** (not required to demonstrate the lifecycle).

#### 4.2 Core Features (Priority P0)

##### FR-P0-01 — Spawn instance mapped to a ticket

* **User story:** As a Service Desk Engineer, I want to spin up a new ARLO instance mapped to a specific Jira or ServiceNow ticket, so that investigation starts without mixing two tickets in one run.
* **Acceptance criteria:**
  1. Given a valid ticket identifier, when I create a run, then a unique instance id `ARLO-<n>` is assigned and shown in the UI.
  2. Given a mapping, when the instance starts, then it is 1:1 with that ticket for the run lifetime (no remapping in MVP).
  3. Given two spawn requests for two tickets, when both succeed, then both appear as separate rows (e.g. `ARLO-675`, `ARLO-676`) and do not share mutable session state.
* **Constraints:** Cannot spawn without a ticket id. Duplicate active mapping to the same ticket: block or warn (Open Question); do not silently merge sessions.

##### FR-P0-02 — Read-only investigation

* **User story:** As an MDM Administrator, I want ARLO to research ticket, asset, and device evidence without changing anything, so that I can trust the proposal.
* **Acceptance criteria:**
  1. During **Investigating**, only §3.4 **Read** (and Intune sync-as-refresh) actions occur.
  2. QA can verify (logs/policy) that write tools are not invoked in this phase.
  3. Partial MCP failure (e.g. Jamf down, ticket is Windows) does not authorize skipping HITL; instance may continue with declared evidence gaps in the proposal or halt with Diagnostic per SAD — must not invent device state.

##### FR-P0-03 — Proposal / discovery summary generation

* **User story:** As an MDM Administrator, I want a single proposal that lists evidence, intended MCP writes, and validation checks, so that I can approve or reject without opening four consoles first.
* **Acceptance criteria:**
  1. Proposal includes: ticket key; targeted asset/device identifiers; findings from authorized reads; **enumerated write actions** (system, action type, target ids); expected validation; residual risk / unknowns.
  2. Proposal is stored on the instance **before** sleep.
  3. Posting that summary **to Jira** is a **write** and must not occur until HITL (FR-P0-05).

##### FR-P0-04 — Approval gate pause (agent sleeps)

* **User story:** As an IT Manager, I want ARLO to stop and wait when a proposal is ready, so that nothing mutates until a human decides.
* **Acceptance criteria:**
  1. On proposal persist, status becomes **Awaiting Approval**.
  2. No state-changing MCP action runs while in this status (QA bypass attempts must fail).
  3. Sleep is durable: restarting the app leaves the instance in **Awaiting Approval** with the same proposal.
  4. There is no auto-approve timer in MVP.

##### FR-P0-05 — Human approve / reject

* **User story:** As an MDM Administrator, I want to approve or reject the exact action list, so that execution cannot drift.
* **Acceptance criteria:**
  1. Approve records actor, time, and frozen action list; status → **Executing**.
  2. Reject records actor, time, and optional reason; no writes; terminal rejected state.
  3. Approve is disabled unless the reviewer can see the proposal and audit trail so far.
  4. Approving a stale proposal after a new investigation is forbidden (proposal identity/version must match).

##### FR-P0-06 — Execution of approved MCP writes only

* **User story:** As a Change Lead, I want execution to match the approved plan (including CHG create if listed), so that tracking and endpoint work stay aligned.
* **Acceptance criteria:**
  1. Only actions on the frozen list run.
  2. Each action result (success/fail/skip) is an audit event.
  3. Failure of one action does not grant extra unauthorized actions; halt or continue-per-plan as specified in the proposal (default: **halt remaining writes**, record Diagnostic).

##### FR-P0-07 — Validation and ticket closure

* **User story:** As a Service Desk Engineer, I want ARLO to re-check device compliance and then close or transition the ticket only if that was approved, so that “Done” means validated, not merely “script sent.”
* **Acceptance criteria:**
  1. Validation uses **read** compliance/asset actions.
  2. Close/transition execute only if those writes were in the approved plan **and** validation criteria passed (or the approved plan explicitly allows close-on-partial — default is **no**).
  3. Success path ends in **Done**.

##### FR-P0-08 — Dashboard: spawn + run grid + status + audit (see §4.3)

Covered in Dashboard Requirements; listed here for priority.

##### FR-P0-09 — Concurrent isolated runs

* **User story:** As an IT Manager, I want multiple ARLO instances in flight at once, so that one HITL sleep does not freeze the queue.
* **Acceptance criteria:** At least two instances in different phases simultaneously (e.g. one Awaiting Approval, one Investigating) without crossed audit events or crossed ticket mappings.

##### FR-P0-10 — Policy deny is visible

* **User story:** As a Security reviewer, I want blocked write attempts in the audit log, so that I can see the guardrail working.
* **Acceptance criteria:** Any denied write (phase violation or tool not on approved list) is logged; instance does not proceed as if the write succeeded.

#### 4.3 Dashboard Requirements (P0)

A web UI (not a single chat thread as the manager path). `aamad.config.yml`: `ui.theme: system`, `visual_style: minimal`, `prefer_modals: false` — prefer in-page panels over modal-heavy UX.

##### UI-P0-01 — Spin up a new ARLO instance mapped to a ticket

* Control to create a run: select/enter **Jira or ServiceNow** ticket identifier; confirm; instance appears immediately in the list with status **Investigating** (or equivalent starting status).
* Empty/invalid ticket id: in-page error, no instance created.
* Copy nearby: **no endpoint or ticket mutation until approval**.

##### UI-P0-02 — List / grid of all historical and active runs

* Rows (or cards in a grid) for **every** run, including finished ones.
* Each row shows at least: instance id (e.g. **ARLO-675**, **ARLO-676**), mapped ticket identifier, current status, timestamps (created, last updated), and a way to open detail/audit.
* Support both **active** and **historical** without dropping Done/Rejected/Failed runs from history in MVP (pagination/filter is enough; no deletion UX required).

##### UI-P0-03 — Real-time status indicators

P0 status vocabulary (exact labels for UI and API):

| Status | Meaning |
|---|---|
| **Investigating** | Trigger accepted through proposal generation (reads + reasoning) |
| **Awaiting Approval** | Agent sleeping at HITL gate |
| **Executing** | Approved writes and/or validation in progress |
| **Done** | Terminal success (validation + approved closure path completed) |

Additional terminal/operational statuses required so the grid does not lie (P0, labels may be visually secondary but must exist): **Rejected**, **Failed**, **Cancelled**.

Indicators must update without a full page rewrite as the source of truth (polling or equivalent is acceptable for MVP; “real-time” means operators are not forced to refresh blindly to see phase changes).

##### UI-P0-04 — Audit log view (reasoning and actions)

* Instance detail includes a **step-by-step** log: reasoning summaries, MCP actions attempted (read and write), results, policy denies, HITL events (sleep, approve, reject), execution and validation outcomes.
* Ordering is chronological and immutable (no silent edits of past events).
* Secrets and raw tokens never rendered.
* This view is the explainability surface for HITL (EU AI Act-style oversight is an Open Question; the log is still required for capstone QA).

##### UI-P0-05 — Approval actions on the instance

* On **Awaiting Approval**, Approve and Reject are available on the instance detail (in-page, not a blocking modal-first flow per config preference).
* The pending proposal (action list) is visible on the same view as the audit log.

#### 4.4 Enhanced Features (Priority P1)

* Auto-spawn from Jira/ServiceNow webhooks when a ticket is created or labeled.
* KEV/severity/SLA badges and sort keys on the grid (from MRD; useful if tickets carry those fields).
* Request-changes loop (human comments; instance re-enters Investigation without executing).
* Filter/export audit log by ticket, actor, outcome.
* Duplicate-ticket / existing-CHG intelligence beyond a simple existence check.
* Batch approve is **not** default (HITL bottleneck risk); if added, still per-instance records.

#### 4.5 Future Features (Priority P2)

* AppSec/code remediation loop from MRD (git branch, draft PR, scanner metadata) — **explicitly not MVP** after this PRD’s domain pivot.
* Graduated autonomy for pre-classified low-risk actions (still logged) — never silent.
* Device wipe, retire, lost mode, identity changes.
* Multi-ticket bulk orchestration, enterprise IAM/SSO, multi-tenant SaaS.
* Auto-merge, auto-close without validation, or auto-approve on timeout.

---

### 5. Non-Functional Requirements

**Performance Requirements:**

* **Response time.** Spawn → instance visible on grid: **< 3s** under local MVP load (excluding first-time MCP auth). First investigation artifacts (audit steps) begin within **1 minute** of spawn under nominal API/LLM conditions (not a hard SLA if vendor APIs stall; then Diagnostic).
* **Throughput and concurrency.** Support **≥ 2** concurrent instances in MVP demonstration; configurable **max concurrent runs** (recommended default **5** for capstone cost control; Open Question for final cap). HITL sleep must **not** consume a busy-loop of LLM turns.
* **Availability.** Capstone: best-effort local uptime. Do not skip HITL or fail open if the orchestrator restarts.

**Security & Compliance:**

* **Data protection.** Ticket text, device logs, and asset data stay in the durable store and vendor systems; no training-data exfil by ARLO; redact secrets in traces.
* **Access control.** MVP: authenticated app users (mechanism in SAD). Approver identity must be attributable. No anonymous Approve.
* **Regulatory.** Capstone is not a declared high-risk EU AI Act deployment; HITL + audit still designed as if oversight will be reviewed (`@security.eng`). Change-management alignment: ServiceNow CHG **create** is tracking, not a license to skip ARLO HITL.

**Scalability & Reliability:**

* **Scaling triggers.** Defer horizontal scale; document queueing if max concurrency is hit (P1).
* **Fault tolerance.** Model provider down: remain Awaiting Approval or Investigating; **never** execute writes to “catch up” without the gate. Jira/SNOW down: local instance state remains source of truth for in-flight approvals. MCP write fail: halt remaining writes (default), record Failed with Diagnostic.
* **Idempotency.** Retries of create CHG / apply profile must not blindly duplicate without checking (SAD specifies keys).

---

### 6. User Experience Design

**Interface Requirements:**

* **Interaction patterns.** Control-plane UI: **Create run** + **Grid** + **Instance detail (proposal + Approve/Reject + audit)**. Chat-inside-instance is optional P1, not the manager path.
* **Platform.** Web, desktop-width first; mobile not in MVP. Theme `system`, visual style `minimal`.
* **Accessibility.** Keyboard-operable Approve/Reject; status not color-only (include text labels **Investigating**, **Awaiting Approval**, **Executing**, **Done**).

**Agent Interaction Design:**

* **Human-agent communication.** Humans approve **plans**, not opaque tool blobs. Action lists use the authorized-action names from §3.4.
* **Feedback and errors.** Failed MCP reads: message on instance + audit. Failed writes: **Executing** → **Failed** with last successful action identified. Never show success if policy denied.
* **Transparency.** Persistent banner on Awaiting Approval: agent is sleeping; **no endpoint or ticket changes until you approve.** Audit log is step-by-step reasoning **and** actions.

---

### 7. Success Metrics & KPIs

**Business / Operational Metrics:**

* Mean time: ticket mapped → **Awaiting Approval** (HITL-ready proposal).
* Mean time: **Approve** → **Done** (or Failed with explanation).
* % proposals **Approved** vs **Rejected** vs **Cancelled**.
* Unapproved endpoint or ticket mutations in QA/prod: **zero**.
* Concurrent in-flight instances demonstrated: **≥ 2**.

Industry MTTR figures (Edgescan 54.81-day app/API; Verizon 43-day KEV median) are **reporting context from MRD**, not ARLO’s numeric commitment (different domain).

**Technical Metrics:**

* HITL bypass attempts blocked: **100%** in QA.
* Decision/audit completeness: **100%** of write attempts have either an approval record or a policy-deny event.
* Per-instance turn/token budget never exceeded without halt + Diagnostic.
* No secrets in UI, tickets, CHGs, or traces (spot-check).

**User Experience Metrics:**

* Task completion: operator can spawn, wait, approve, and see **Done** (or Rejected) without leaving the dashboard.
* Time-to-value: first HITL-ready proposal on a fixture ticket in minutes, not hours (qualitative capstone bar).
* Satisfaction: informal operator review that the grid + audit are usable without chat (no numeric CSAT required).

---

### 8. Implementation Strategy

**Development Phases:**

* **Phase 1 (Define):** MRD (complete, AppSec-era); this PRD; SAD/SFS via `@system.arch`; user stories via `@product-mgr` `*create-stories` as follow-on.
* **Phase 2 (Build):** `@project.mgr` setup → `@backend.eng` / `@frontend.eng` → `@integration.eng` → `@qa.eng` → `@security.eng` (`security.md` required by config). Runtime adapter: Claude Agent SDK (Python). Modules: core instance state machine + HITL; MCP **bindings** for authorized actions; dashboard.
* **Phase 3 (Deliver):** `@devops.eng` deploy.md + user-guide.md after QA (and security assessment).

**Resource Requirements:** Capstone AAMAD crew; LLM budget proportional to max concurrency; fixture tickets and non-prod Jamf/Intune/Jira/SNOW or **stubs** if live systems are unavailable (Open Question).

**Risk Mitigation:**

| Risk | Mitigation |
|---|---|
| Ungoverned endpoint/ticket writes | Policy PEP outside the model; write tools absent until approval; QA bypass tests (FR-P0-10) |
| MRD vs PRD domain confusion in later personas | This PRD is scope-authoritative; AppSec/git is P2 |
| Unset `AAMAD_TARGET_RUNTIME` → crewai default | Export `claude-agent-sdk` in Build/CI |
| HITL sleep lost on restart | Durable instance store (FR-P0-04) |
| MCP vendors unavailable in capstone | Contract tests + stubs; do not fake successful writes |
| Cost at concurrency | Max instances + turn caps |
| Rubber-stamp UX | Force visible action list + audit on Approve |

---

### 9. Launch & Go-to-Market Strategy

N/A for this capstone/internal MVP. No pricing, packaging, or sales motion. Operator-facing “launch” is a local/demo runbook in Deliver (`user-guide.md` required by `documentation.require_user_guide: true`).

---

## Quality Assurance Checklist

- [x] Requirements traceable to operator PRD request, MRD (transferred HITL/concurrency/dashboard only), `aamad.config.yml`, or recorded Assumptions
- [x] Technical specifications feasible with `claude-agent-sdk` (hooks, isolated sessions, least-privilege tools); MCP listed as authorized actions only
- [x] Success metrics aligned with HITL-zero-bypass, named instances, and dashboard statuses
- [x] MVP vs Future Work boundaries explicit (AppSec/git P2; webhooks P1)
- [x] Commercial GTM marked N/A; AppSec TAM not reused as endpoint TAM
- [x] Agent persona, MCP scope, HITL lifecycle, and dashboard sections included as specified by the operator

---

## Sources

1. Operator instruction (2026-08-31): PRD content for ARLO — persona **Enterprise IT & Endpoint Remediation Specialist**; HITL never mutate endpoint/ticket without approval; MCP authorized actions for Jira, ServiceNow, Jamf, Intune; lifecycle Trigger → Investigation → Proposal → Approval Gate Pause (sleep) → Approve → Execution → Validation & Closure; dashboard spawn, `ARLO-675`/`ARLO-676` grid, statuses Investigating / Awaiting Approval / Executing / Done, audit log. Primary product-scope source.
2. `project-context/1.define/mrd.md` (2026-08-31) — HITL-as-architecture, named concurrent instances, portfolio dashboard, decision history, runtime `claude-agent-sdk`, OWASP Excessive Agency, Verizon/IBM figures used only as adjacent risk/automation context. **Not** used for AppSec/git MVP scope.
3. `aamad.config.yml` — `runtime.target: claude-agent-sdk`, `language.primary: python`, `libraries.approved: [claude-agent-sdk]`, UI theme/system/minimal, `prefer_modals: false`, `security.require_security_assessment: true`, testing and user-guide flags.
4. `.cursor/templates/prd-template.md`, `.cursor/agents/product-mgr.md`, `.cursor/rules/aamad-core.mdc`, `.cursor/rules/adapter-registry.mdc`, `.cursor/rules/adapter-claude-agent-sdk.mdc`, `AGENTS.md` (AAMAD 0.7.5).
5. Verizon 2026 DBIR / IBM Cost of a Data Breach 2025 — cited via MRD Sources; not re-fetched for this PRD.
6. Tech Vendor Index, “Best Endpoint Management for Enterprise (2026)” — Intune + Jamf two-console enterprise pattern. https://techvendorindex.com/compare/best-endpoint-for-enterprise/
7. Tanium, AI Agent for ServiceNow overview — investigate / recommend / human-initiated deploy pattern (analog, not a requirement to integrate Tanium). https://help.tanium.com/bundle/tanium-ai-agent-for-servicenow/page/ServiceNow_Integrations/AIAgentForServiceNow/overview.htm
8. Tanium ITX / Autonomous IT for ServiceNow materials — ITSM + endpoint closed-loop positioning; CHG-aligned remediations as industry narrative.
9. OWASP Top 10 for LLM Applications (Excessive Agency / human approval for high-impact actions) — via MRD citations.

## Assumptions

- **MRD skip/partial:** MRD exists but targeted AppSec code remediation. This PRD **supersedes MRD product domain**. Later personas must follow this PRD for scope. MRD skip-equivalent rationale for AppSec TAM in §2: wrong category after operator pivot.
- **System description skipped:** Operator provided the four required product blocks in the `*create-prd` request; a separate elicitation questionnaire was not required to avoid conflicting artifacts.
- HITL applies to **all** §3.4 writes, including Jira discovery-summary posts, ticket transitions, closes, and ServiceNow CHG **create**. Investigation is read-only (+ Intune status sync as refresh).
- “Agent sleeps” is a **durable orchestrated pause**, not process termination without state.
- Instance naming `ARLO-675` is an example of the `ARLO-<id>` scheme; sequential integers are sufficient for MVP (need not equal the Jira key).
- Trigger is **user-initiated spawn** mapped to an **existing** ticket (Jira or ServiceNow). Tickets are not created by ARLO in MVP.
- Jamf scope is **Apple endpoints**; Intune scope is **Windows and mobile**; a ticket may need only one MDM. ARLO must not apply the other MDM’s writes without evidence and approval.
- “Approved configuration profiles or scripts” / “approved policies or remediations” means **approved in the ARLO HITL proposal**, not a separate undocumented MDM pre-approval catalog (though orgs may constrain IDs in SAD).
- Runtime: config `claude-agent-sdk`; env `AAMAD_TARGET_RUNTIME` unset at authoring — Build must export it.
- Language Python; no CrewAI YAML as MVP runtime.
- Capstone may use stubs/sandboxes for Jamf/Intune/Jira/SNOW if production tenants are unavailable; stubs must still obey HITL (no fake success that hides skipped gates).
- Merge/wipe/identity/network actions are out of scope.
- GTM §9 is N/A (internal/capstone).
- Approver role: any authenticated ARLO user in MVP unless SAD tightens (Open Question).

## Open Questions

1. Confirm Jira Cloud vs Server/DC and ServiceNow instance (prod vs subprod) for MVP fixtures.
2. Who may Approve — any authenticated user, ticket assignee, MDM admin role, or change manager? Affects ACL in SAD.
3. Duplicate spawn on an already-active ticket: reject, attach to existing instance, or allow parallel runs?
4. Should Jira comment-only “heartbeat” ever be allowed pre-HITL? **PRD default: no.** Stakeholder override would need an explicit amendment.
5. Intune device sync: confirm read-side vs mutation with Security.
6. Validation failure: remain open with Failed, or still close if the approved plan says so? **PRD default: do not close.**
7. Numeric `ARLO-<id>` vs encoding ticket key in the instance name.
8. Max concurrent instances and monthly LLM budget (MRD Open Question carried forward).
9. Live MCP servers vs contract stubs for capstone demo.
10. Whether `@product-mgr` should also run `*create-stories` immediately after this PRD.
11. Freedom-to-operate / trademark “ARLO” (carried from MRD; not researched).
12. EU AI Act applicability if demo uses EU personal device data.
13. Language: remain Python vs TypeScript Claude Agent SDK (config says Python).
14. MRD AppSec/git loop: archive as P2 only, or did stakeholders intend a **combined** IT + AppSec product? **PRD assumes IT/endpoint only.**

## Audit

- **Timestamp:** 2026-08-31T19:35:00Z (operator local 2026-08-31 12:35 PDT)
- **Persona id:** `product-mgr`
- **Action:** `create-prd`
- **Output path:** `project-context/1.define/prd.md`
- **Resolved `AAMAD_TARGET_RUNTIME`:** `claude-agent-sdk` via `aamad.config.yml` `runtime.target`; shell env **unset** at authoring (adapter-registry default `crewai` would apply if env were preferred without export — warning recorded)
- **Config loaded:** `aamad.config.yml` (python, `libraries.approved: [claude-agent-sdk]`, UI minimal/system, `prefer_modals: false`, `security.require_security_assessment: true`, unit+integration tests, user guide required)
- **Inputs read:** `.cursor/agents/product-mgr.md`, `.cursor/templates/prd-template.md`, `project-context/1.define/mrd.md`, `aamad.config.yml`, `AGENTS.md`, adapter-registry and `adapter-claude-agent-sdk` rules, operator `*create-prd` specification
- **Prompt Trace:** omitted. Define-phase requirements synthesis; no runtime agent execution against Jira/ServiceNow/Jamf/Intune; no secret-bearing prompts. Trace omission rationale: not a high-risk executable run; citations live in Sources.
- **Model / temperature / max_tokens:** Cursor Grok 4.6 interactive session; temperature/max_tokens not independently set by this persona (IDE-controlled).
- **Write method:** temp-write `prd.md.tmp` then atomic replace to `prd.md`.
- **Prohibited actions honored:** no application code; no SAD/SFS/Build/Deliver edits; no MCP implementation specs; no invented market TAM for endpoint UEM; MRD/domain conflict recorded under Assumptions and Open Questions.
- **Self-check (required headings):** Executive Summary; Market Context & User Analysis; Technical Requirements & Architecture (including Agent Persona & Scope, Core Agent Definitions, MCP Integration Scope); Functional Requirements (including Stateful Remediation Lifecycle and Dashboard Requirements); Non-Functional Requirements; User Experience Design; Success Metrics & KPIs; Implementation Strategy; Launch & Go-to-Market Strategy; Quality Assurance Checklist; Sources; Assumptions; Open Questions; Audit.
