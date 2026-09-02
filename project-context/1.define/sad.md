# System Architecture Document: ARLO (Automated Remediation Loop Orchestrator)

**Document type:** AAMAD System Architecture Document (SAD)  
**Product:** ARLO — Automated Remediation Loop Orchestrator  
**Phase:** 1 Define  
**Owner persona:** `@system.arch` (`system-arch`)  
**Date:** 2026-08-31 (updated 2026-09-01)  
**Status:** MVP-authoritative for architecture (product scope from PRD; stack constraints from operator `*create-sad` instruction)  
**Action:** `update-sad` (Subagent Specialist Topology + Artifact Storage Model)

## Context & Instructions

This SAD is the Build-phase blueprint for ARLO. Product behavior is taken only from `project-context/1.define/prd.md`. Architectural stack constraints in this document (Temporal.io, Claude Agent SDK in Temporal Activities, MCP, FastAPI, Next.js, PostgreSQL, Central Memory / Vector KB) are operator-specified for `*create-sad` / SAD updates and do not invent new product features.

Align agent and API design with runtime `claude-agent-sdk` (`.cursor/rules/adapter-claude-agent-sdk.mdc`). Prefer lean MVP views; defer nonessential NFRs to Future Work.

## Input Requirements

**PRD Document**: `project-context/1.define/prd.md` (2026-08-31; MVP-authoritative for product scope)  
**MRD** (optional): `project-context/1.define/mrd.md` (2026-08-31; transferable HITL / concurrency / dashboard / runtime only — AppSec/git domain superseded by PRD)  
**User Stories** (when present): N/A — `project-context/1.define/user-stories/` not produced at SAD authoring  
**MVP Scope**: One blueprint, N ticket-mapped instances; read-only investigation; proposal; durable HITL sleep; approved MCP writes only; dashboard grid + audit (PRD §4); Shared Operational Memory (`learned_patterns`) and Vector Knowledge Base (`kb_articles` + `kb_search`) for cross-instance grounding (operator SAD update)  
**Selected Runtime**: `claude-agent-sdk`

---

### 1. MVP Architecture Philosophy & Principles

**MVP Design Principles**:

- **PRD-first.** Every component exists to deliver PRD P0: named instances, HITL sleep, least-privilege MCP, fleet dashboard. Do not add AppSec/git, auto-spawn, or graduated autonomy.
- **HITL is architecture, not a prompt.** Write-capable MCP tools are absent from `allowed_tools` until an approval record exists. A Temporal Workflow **Signal wait** is the durable sleep. A `PreToolUse` policy enforcement point (PEP) outside the model is the last-line deny.
- **Durable loops, idle workers.** Long-running agent loops are Temporal Workflows. Human wait must not occupy a worker thread, an LLM session, or an MCP connection.
- **One blueprint, N isolated runs.** Each `ARLO-<id>` is one Temporal Workflow + one PostgreSQL instance row. Sibling runs do not share mutable Claude sessions or MCP auth context. They **do** share read-only Central Memory and the Vector KB so a validated fix in `ARLO-675` can ground `ARLO-680` without merging sessions.
- **Shared memory is product state, not LLM memory.** PRD keeps conversational/SDK memory off. `learned_patterns` and `kb_articles` are durable PostgreSQL artifacts. Retrieval never authorizes endpoint or ticket writes; persist happens only after successful Validation of an already-approved plan.
- **Observable by default.** Phase changes, tool attempts, policy denies, HITL events, memory retrievals, and pattern persists are first-class product data (mirrored audit log), not only ops logs.
- **Fail closed.** Missing approval, rejected proposal, MCP unavailable, or policy deny never “helpfully” continues into writes (PRD §3.1, §5).
- **Smallest deployable slice.** Local Compose: Next.js, FastAPI, PostgreSQL, Temporal (dev), one Python worker. No live production deploy without operator authorization.

**Core vs Future Features**:

| Layer | MVP | Future Work / excluded |
|---|---|---|
| Orchestration | Temporal Workflow per instance; Signal wait at approval gate | Temporal Cloud HA, multi-cluster, continue-as-new for multi-day mega-histories unless a single run exceeds history limits |
| Agent brain | Claude Agent SDK inside Temporal Activities; `arlo_orchestrator` + three specialists (`discovery_agent`, `script_writer_agent`, `jamf_ops_agent`) | CrewAI YAML runtime; unbounded delegated managers; extra specialist roles beyond the four |
| Tools | MCP authorized actions only (Jira, ServiceNow, Jamf, Intune) | Wipe/retire/lost-mode; IdP; network ACLs; arbitrary unsigned scripts; git/PR/SAST |
| Trigger | User spawn from UI mapped to an **existing** ticket | Auto-spawn from ticket webhooks (PRD P1) |
| UI | Next.js run grid + instance detail tabs (Proposal, Script, Test Logs, Audit Trail); Approve/Reject; polling | Chat-inside-instance (P1); mobile; batch approve |
| Data | PostgreSQL metadata + mirrored audit + **run artifacts** (`run_artifacts`: discovery packs, generated scripts, test logs); **Shared Operational Memory** (`learned_patterns`); **Vector KB** (`kb_articles` + pgvector); Temporal event history for workflow durability | Multi-tenant SaaS; enterprise SSO/IAM; unsupervised pattern promotion without validation |
| HITL | Approve / Reject / Cancel; no auto-approve timer | Request-changes re-entry (P1); timeout-to-execute (explicitly forbidden) |

**Explicit exclusions (MVP):** application source-code patching; git/PR; original SAST/SCA; EDR kill-chain; identity provisioning; network ACL changes; auto-merge; auto-close without validation; auto-approve on timeout; device wipe/retire/lock; multi-ticket bulk orchestration.

#### Stakeholders, Concerns, and Viewpoints (ISO/IEC/IEEE 42010)

| Stakeholder | Concerns | Primary viewpoint |
|---|---|---|
| Endpoint / MDM Administrator | Safe, evidence-backed approve/reject; no silent MDM writes | Logical + process (HITL gate, MCP write set) |
| IT Support / Service Desk | Spawn on a ticket; see Investigating → Awaiting Approval | Frontend + process |
| Change / IT Operations Lead | CHG check/create only as approved tracking | Logical (ServiceNow MCP) + data (approval record) |
| IT / Engineering Manager | Fleet grid of named runs; who approved what | Frontend + data (mirrored logs) |
| Security reviewer | PEP outside the model; deny visible in audit; secrets never in traces | Security + process |
| Build personas (`@backend.eng`, `@frontend.eng`, `@integration.eng`) | Contracts, runtime adapter, least-privilege tools | All views; this SAD |
| `@devops.eng` | Smallest Compose target; env names only; no live deploy unless authorized | Deployment |

**Viewpoints used in this SAD:** Logical (components and responsibilities), Process/runtime (execution flow and state machine), Deployment (Compose topology), Data (PostgreSQL application schema + Central Memory + Vector KB + Temporal persistence split). Correspondence rule: instance id `ARLO-<id>` = Temporal Workflow Id = PostgreSQL `instances.arlo_id` = UI row key. Phase labels in UI/API/Workflow/DB must use the PRD vocabulary. Memory correspondence: `learned_patterns.created_by_arlo_id` references a completed instance; retrieval never mutates that instance’s HITL gate.

#### Logical Architecture

**Primary presentation.** ARLO is a control plane around a durable remediation Workflow. The UI never talks to Temporal or MCP directly. The Backend API is the only component that starts Workflows, sends Signals, and reads PostgreSQL for the dashboard. The Temporal Worker is the only component that runs Claude Agent SDK and MCP tools, and it does so **inside Activities**, never inside Workflow code.

![ARLO logical architecture](diagrams/arlo-logical-architecture.png)

Source: `diagrams/arlo-logical-architecture.mmd` (rendered with mermaid-cli).

**Element catalog (logical):**

| Element | Responsibility | Must not |
|---|---|---|
| Next.js UI | Spawn form, run grid, instance detail tabs (Proposal, Script, Test Logs, Audit Trail), Approve/Reject; poll for status and artifacts | Call Temporal, MCP, or Anthropic; hold HITL state as sole source of truth |
| FastAPI | Authenticate users; validate spawn; persist instance row; `start_workflow`; emit Signals; serve list/detail/audit; receive webhooks; health | Execute Claude/MCP; skip HITL; store secret values in artifacts |
| PostgreSQL (application) | Users; instance metadata; frozen proposal; approval/rejection records; **run artifacts** (discovery packs, scripts, test logs) keyed by `arlo_id`; **mirrored** chronological audit events for the dashboard | Replace Temporal as workflow durability store |
| Shared Operational Memory (`learned_patterns`) | Cross-instance, structured fixes (script_fix, version_endpoint, vendor_gotcha) keyed by `app_name` / `platform`; incremented on successful Validation | Auto-execute a stored payload; skip HITL for a later instance; persist on Reject / Failed |
| Vector KB (`kb_articles`) | Operator / org runbooks (markdown) with pgvector embeddings for semantic SOP retrieval | Treat KB text as an approved write plan; embed secrets |
| Temporal Server | Durable Workflow state, timers, Signals, Activity retries, worker task queues | Business-data reporting store for the grid (use PostgreSQL mirror) |
| `ArloRemediationWorkflow` | Phase transitions; wait on approval Signal; schedule Activities; enforce illegal-transition rules in code | Call LLM, MCP, or DB drivers (non-deterministic I/O) |
| Activities + Claude Agent SDK | Investigation reads + memory/KB grounding, proposal JSON, script draft/refactor, approved Jamf test-policy writes, validation reads; emit audit events; persist artifacts and patterns on Done | Run write tools without approval context; keep MCP/LLM sessions open across HITL sleep; give a specialist tools outside its segregation table |
| `PreToolUse` PEP | Deny any state-changing **vendor** tool if phase ≠ Executing or tool not on frozen approved list | Trust model-stated phase; treat `kb_search` as a write |
| MCP servers | Expose **only** PRD §3.4 authorized actions plus internal **read** `kb_search` | Expose wipe/retire/lock, credential dump, or arbitrary script |
| Internal `kb_search` MCP | Vector similarity over `kb_articles`; return top chunks for prompt grounding | Mutate `kb_articles` or `learned_patterns` from the investigator |

**Rationale / analysis.** PRD requires “agent sleeps” to be an orchestrated pause that survives process and UI restart and must not busy-loop LLM turns (PRD §4.1, §5). Temporal Workflows waiting on a Signal are **not scheduled** on a worker until the Signal (or another event) arrives; history is persisted by the Temporal cluster. Claude SDK and MCP are therefore bound to Activities so they start and stop with each phase. PostgreSQL exists because the dashboard must query historical runs, approver identity, and step logs without Temporal visibility-query gymnastics (PRD §3.5, UI-P0-02/04). Central Memory and the Vector KB live in the same database so Investigation can ground proposals on prior validated fixes and SOPs without sharing Claude sessions (PRD isolation + operator memory loop).

**Technical Architecture Decisions**:

| ID | Decision | Rationale | Trace |
|---|---|---|---|
| AD-1 | **Temporal.io** is the orchestration engine for each `ARLO-<id>` loop | Durable HITL sleep without occupying workers or LLM sessions; concurrent Workflows for FR-P0-09 | Operator SAD constraint; PRD §3.1 #5, §4.1, §5 |
| AD-2 | **Claude Agent SDK (Python)** runs **only inside Temporal Activities** | Adapter `claude-agent-sdk`; Python is `aamad.config.yml` `language.primary`; Workflows stay deterministic | PRD §3.2; config; adapter rule |
| AD-3 | **MCP** is the sole tool integration standard for Jira, ServiceNow, Jamf, Intune | PRD authorizes actions, not vendor SDK sprawl; least-privilege tool lists per phase | PRD §3.4; operator SAD constraint |
| AD-4 | **FastAPI (Python)** as Backend API | Same language as worker/SDK; serves UI, starts Workflows, Signals on approve, webhook receiver | Operator constraint (FastAPI **or** Node; Python wins per config); PRD §3.5 |
| AD-5 | **Next.js / React** (App Router) as Frontend | PRD dashboard is a control-plane UI, not a chat thread; operator stack | PRD §4.3, §6; `ui.theme: system`, `prefer_modals: false` |
| AD-6 | **PostgreSQL** for users, instance metadata, and mirrored audit logs | PRD durable store; dashboard source of truth; Temporal remains workflow source of truth | PRD §3.5; operator SAD constraint |
| AD-7 | HITL wake-up is a Temporal **Signal** (`approval_decision`); Workflow uses `wait_condition` | Signal wait completes the Workflow Task and frees the worker; no polling-mutate | PRD §4.1 sleep semantics; operator constraint |
| AD-8 | Product “session resume” = Temporal Workflow Id + PostgreSQL proposal/audit; Claude SDK sessions are **per-Activity and ephemeral** | Keeping an SDK session open during sleep would hold MCP/LLM resources; evidence pack + proposal hash are passed into later Activities | PRD §3.2 session resume; §5 no busy-loop |
| AD-9 | Dual enforcement: (1) write tools omitted from `allowed_tools` until approval; (2) `PreToolUse` deny + audit | OWASP Excessive Agency; FR-P0-10 | PRD §3.1, §3.2, FR-P0-10 |
| AD-10 | MCP transport: **HTTP/SSE** (or streamable HTTP) for remote servers; **stdio** for local stub processes | Capstone may lack live tenants; stubs must still obey HITL | PRD Assumptions (stubs); operator constraint |
| AD-11 | UI updates via **polling** (MVP); SSE/websocket optional later | PRD: polling acceptable; “real-time” means no blind full-page rewrite | UI-P0-03 |
| AD-12 | Intune “sync device status” is a **read-side refresh** inside Investigation/Validation Activities | PRD classification; move behind HITL only if Security reclassifies | PRD §3.1, Open Question 5 |
| AD-13 | **Shared Operational Memory** is table `learned_patterns` in PostgreSQL; retrieved in Investigation; appended/incremented only after successful Validation | Cross-instance learning without shared Claude sessions; persist is not an endpoint/ticket mutation and does not bypass the next instance’s HITL | Operator SAD update 2026-08-31; PRD §3.2 Memory (durable product state, not LLM memory) |
| AD-14 | **Vector KB** is `kb_articles` with `pgvector` `VECTOR(1536)`; exposed to Investigation as MCP tool `kb_search` | Ground proposals in SOPs (e.g. FileVault re-encryption) via semantic search; read-only during Investigation | Operator SAD update 2026-08-31; PRD FR-P0-02 / FR-P0-03 grounding |
| AD-15 | Memory retrieve is **automatic** (Activity injects matched patterns + `kb_search` results into Claude context); `kb_search` also remains in investigator `allowed_tools` for follow-up queries | Operator: inject on start of `ARLO-680`; tool remains available if ticket metadata is incomplete | Operator SAD update; adapter least-privilege reads |
| AD-16 | Four Claude Agent SDK specialists: `arlo_orchestrator`, `discovery_agent`, `script_writer_agent`, `jamf_ops_agent`. Tool lists are **segregated by `AgentDefinition.tools`**; the coordinator never grants a specialist a broader set than this table. | PRD §3.2–3.3 allows subagent isolation of read vs write; operator 2026-09-01 names the four roles and their tool bindings | Operator SAD update 2026-09-01; PRD §3.2–3.3, §3.4 Jamf write |
| AD-17 | **Run artifacts** live in PostgreSQL table `run_artifacts` keyed by `arlo_id`. Types: `discovery_pack`, `generated_script`, `test_execution_log`. FastAPI serves them to Next.js for `/runs/[arloId]` tabs. | PRD §3.5 “artifact links”; dashboard must show script + test logs without Temporal visibility queries | Operator SAD update 2026-09-01; PRD §3.5, §4.3 |
| AD-18 | After HITL Approve, Execution may loop `jamf_ops_agent` (Policy **1460**, event `arlo_test`) → persist stdout/stderr → `script_writer_agent` refactor → re-test, up to `ARLO_SCRIPT_TEST_MAX_ATTEMPTS` (default **3**). Frozen **action types and targets** do not change; script **body** may be revised. Exceeding the bound → `Failed`. | Operator-specified test-policy loop; keeps production-scope HITL (the human approved those Jamf write verbs and Policy 1460) while allowing bounded automated repair | Operator SAD update 2026-09-01; PRD §3.4 Jamf “apply approved … scripts”; FR-P0-06 halt-on-failure |

---

### 2. Multi-Agent System Specification

**Agent Architecture Requirements**:

Single product blueprint `arlo`, instantiated once per ticket as Workflow `ArloRemediationWorkflow` (workflow id `arlo-<n>` / display `ARLO-<n>`). Specialists are Claude Agent SDK `AgentDefinition` entries invoked from Activities via the Agent tool. Maximum **four** runtime roles (PRD §3.2–3.3; operator 2026-09-01 names):

| Agent id | PRD mapping | Role | Goal | When scheduled |
|---|---|---|---|---|
| `arlo_orchestrator` | PRD `arlo` coordinator | Enterprise IT & Endpoint Remediation Specialist | Own phase, budgets, audit narrative, specialist dispatch; never bypass HITL | Main runtime agent in every Activity |
| `discovery_agent` | PRD `arlo-investigator` | Read-Only Investigator | Ticket + asset + MDM + SOP evidence pack; **no mutations** | Investigation Activity only |
| `script_writer_agent` | PRD proposal specialist (script artifact) | Remediation Developer | Draft or refactor Zsh (macOS) / PowerShell (Windows) from OS requirements or test logs; **no vendor MCP** | Proposal Activity (initial draft); Execution test-loop (refactor only) |
| `jamf_ops_agent` | PRD `arlo-executor` (Apple / Jamf path) | Fleet Executor | Upload approved script, attach to test Policy **1460**, run event `arlo_test`; halt on unauthorized or failed mutation | Execution Activity + test-loop, **after** Signal + approval row |

Windows / Intune approved writes remain on `arlo_orchestrator` with Intune tools from the frozen list (no fifth specialist in MVP). Validation stays on the orchestrator with investigator **read** tools plus ticket writes iff those writes are on the frozen list; `learned_patterns` persist is Activity SQL, not a model-invoked tool.

**Collaboration pattern:** sequential lifecycle **per instance**; concurrent fan-out **across instances**. No hierarchical manager rewriting policy. Subagent delegation must use stricter or equal tool policy and **must not bypass HITL**. `script_writer_agent` may change script **text** inside the Execution test-loop; it must not add systems, action types, devices, or policy ids that were not on the frozen list.

#### Subagent Specialist Topology — Claude Agent SDK `AgentDefinition` specs

Implementation path: `worker/agents/*.py`. Keys in `ClaudeAgentOptions.agents` **must** match the agent ids below. Built-in SDK filesystem/shell tools stay **disabled** (`ClaudeAgentOptions.tools = []`). Policy **1460** / `sudo jamf policy -event arlo_test` is an **MCP tool** (`jamf_execute_test_policy`), never a Bash/shell grant.

| Field | `arlo_orchestrator` | `discovery_agent` | `script_writer_agent` | `jamf_ops_agent` |
|---|---|---|---|---|
| **`description`** | Coordinator: phase owner, specialist dispatcher, HITL guardian. | Read-only investigator for ticket, asset, MDM, and SOP context. | Remediation developer: Zsh and PowerShell author/refactorer. | Jamf fleet executor for approved script upload, Policy 1460 bind, and `arlo_test`. |
| **`model`** | `inherit` | `inherit` | `inherit` | `inherit` |
| **`tools` (qualified MCP)** | **None** (no vendor MCP). May invoke the three specialists via the Agent tool. | **Read-only:** `mcp__jira__jira_get_ticket`; `mcp__servicenow__snow_check_chg`; `mcp__servicenow__snow_read_asset`; `mcp__jamf__jamf_read_compliance`; `mcp__jamf__jamf_fetch_logs`; `mcp__intune__intune_read_compliance`; `mcp__intune__intune_sync_device`; `mcp__kb__kb_search`. | **Empty list.** No Jira/SNOW/Jamf/Intune/KB tools. Script text is model output persisted by the Activity. | **Jamf writes only:** `mcp__jamf__jamf_upload_script`; `mcp__jamf__jamf_policy_set_script`; `mcp__jamf__jamf_execute_test_policy`. Optional intersection with frozen `jamf_apply_profile` when that action is on the approval record. |
| **Forbidden tools** | Any vendor write. Must not run Policy 1460 itself. | Any write (`jira_post_comment`, `jamf_upload_script`, `jamf_policy_set_script`, `jamf_execute_test_policy`, `jamf_apply_profile`, Intune apply, SNOW create CHG, ticket transition/close). | All MCP tools. No shell, no file write, no Jamf upload. | All non-Jamf tools; Jamf **reads** (compliance/logs) stay on `discovery_agent`; Intune writes stay on the orchestrator. |
| **Inputs** | Activity phase, ticket key, evidence/proposal/approval context | Ticket id; injected `learned_patterns` + `kb_search` hits | Discovery pack (OS, app, gaps) **or** prior script + test stdout/stderr | Frozen action list; latest `generated_script` artifact; Policy id **1460**; event `arlo_test` |
| **Outputs** | Phase narrative; which specialist ran; no artifact body of its own | `discovery_pack` JSON artifact | `generated_script` artifact (`language` = `zsh` \| `powershell`) | `test_execution_log` artifact (`exit_code`, `stdout`, `stderr`, `policy_id`, `event`) |

**Prompt contracts (normative intent; exact strings live in `worker/agents/`):**

- **`arlo_orchestrator`:** You own the instance lifecycle. Dispatch `discovery_agent` for evidence, `script_writer_agent` for script draft/refactor, `jamf_ops_agent` only after an approval record exists. Never invent device state. Never grant a specialist extra tools.
- **`discovery_agent`:** Assemble ticket, asset, device compliance/log, and official runbook context. Ground every claim in a tool result. Never mutate.
- **`script_writer_agent`:** Write or refactor a single remediation script for the stated OS. Prefer Zsh on macOS and PowerShell on Windows. When given a non-zero test log, fix the failure; do not change undeclared scope (new devices, new policy ids). Return only the script and a short changelog.
- **`jamf_ops_agent`:** Apply exactly the frozen Jamf writes. Upload the persisted script, attach it to Policy 1460 (`jamf_policy_set_script`), execute `jamf_execute_test_policy` (event `arlo_test`). Stop on first failed or denied mutation. Do not call `sudo` or any shell; the MCP tool is the only execution path.

**Jamf write bindings (PRD §3.4 “Apply approved configuration profiles or scripts”):** Build-time tool names `jamf_upload_script`, `jamf_policy_set_script`, and `jamf_execute_test_policy` are **granular bindings** of that single authorized write, plus retained `jamf_apply_profile` for profile-id applies. They are not a license for arbitrary unsigned scripts, off-proposal devices, or production policies other than those enumerated on the approval record. Policy **1460** + event `arlo_test` are the operator-designated **isolated test policy** (env names `JAMF_TEST_POLICY_ID`, `JAMF_TEST_EVENT`). Production fleet policies still require those ids on the frozen list.

**Memory / session:** LLM / SDK conversational memory default **off** (PRD §3.2). Durable product state is Workflow + PostgreSQL (`instances`, proposal, approval, `audit_events`). **Central Memory** (`learned_patterns`) and **Vector KB** (`kb_articles`) are shared, durable stores — not per-instance Claude memory and not session fork. No session fork in MVP.

#### Runtime tool binding — `kb_search` (Investigation Activity)

Internal MCP tool (in-process MCP server preferred per adapter). **Read-only.** Available in Investigation (and optionally Proposal if evidence gaps remain). **Not** a vendor write; **not** registered for Execution except as a read if an executor needs an SOP citation (MVP: Investigation/Proposal only).

| Field | Contract |
|---|---|
| **Tool name** | `kb_search` |
| **When allowed** | Investigation Activity (`discovery_agent` `allowed_tools`); automatic pre-call by the Activity before the first model turn |
| **Inputs** | `{ "query": string, "category"?: string, "top_k"?: int }` |
| **`query`** | Required. Natural-language search (ticket summary, app + symptom, or follow-up). |
| **`category`** | Optional filter on `kb_articles.category` (e.g. `jamf_sop`, `intune_policy`, `compliance`). |
| **`top_k`** | Optional. Default **5**, max **10** (MVP). |
| **Behavior** | Embed `query` with the same 1536-d model used at index time. Vector similarity search (`ORDER BY embedding <=> query_embedding`) on `kb_articles`, optional `category` equality filter. Return top chunks. |
| **Output** | `{ "hits": [ { "id", "title", "category", "content_excerpt", "score" } ], "query", "top_k" }` — excerpts only in the tool payload (full `content` may be truncated to a token budget). |
| **Failure** | Embedding or DB unavailable → Diagnostic on the instance; continue investigation with declared KB gap; **do not** invent SOP text; **do not** skip HITL. |
| **Guardrails** | No writes to `kb_articles` from this tool. Secrets in `metadata_json` / content must already be redacted at ingest. Hits are **evidence**, not an approval record. |

**Task / Turn Orchestration**:

1. **Trigger (API, not an Activity):** FastAPI authenticates, validates ticket id, allocates `ARLO-<n>`, inserts `instances` row (`Investigating`), `start_workflow` with `{ arlo_id, ticket_system, ticket_key }`.
2. **Activity `investigate` (Retrieval Phase, `discovery_agent`):** Read ticket metadata (app / platform when present). **Automatically** (a) `SELECT` from `learned_patterns` where `app_name` or `platform` matches, and (b) call `kb_search` with a ticket-derived `query` (and `category` if known). Inject both result sets into Claude prompt context. Then Claude SDK with **read-only** MCP `allowed_tools` including `kb_search` for follow-up (`discovery_agent` only). Output: evidence pack JSON (ticket, assets, devices, matched patterns, KB hits, gaps). Persist a `run_artifacts` row `artifact_type=discovery_pack` plus audit steps for retrievals. On blocking **vendor** read failure: Diagnostic; Workflow → `Failed` (do not invent device state). KB/memory miss is a declared gap, not a fail-open.
3. **Activity `write_script` (`script_writer_agent`):** Input the discovery pack (OS / app / gaps). Output a Zsh or PowerShell script body. Persist `run_artifacts` `artifact_type=generated_script` (`attempt=0`). **No vendor MCP.** If the platform is neither macOS nor Windows, skip and record a gap.
4. **Activity `generate_proposal` (`arlo_orchestrator`):** Input evidence pack **including** injected patterns, KB chunks, and the latest script artifact id when present. Output: proposal document with ticket key, targeted identifiers, findings, **enumerated writes** (system, action type, target ids — including Jamf `upload_script` / `policy_set_script` / `execute_test_policy` when the Apple test-policy path applies), validation checks, residual risk, and citations of pattern ids / KB article ids / script artifact id when used. Persist proposal + `proposal_hash`. Status → `Awaiting Approval`. **No vendor MCP writes.**
5. **Workflow HITL wait:** `await workflow.wait_condition(lambda: self.decision is not None)` (see Process view). Worker released. MCP and Claude clients are **not** alive.
6. **Signal `approval_decision`:** `{ action: approve|reject|cancel, actor_id, at, proposal_hash, rationale? }`. API writes `approvals` row **before or in the same request as** Signal, using the frozen action list. Stale `proposal_hash` → 409, no Signal.
7. **Reject / Cancel:** no execution Activities; terminal status; ticket/endpoints unchanged by ARLO.
8. **Error-handling loop (Execution, only if the frozen list includes Jamf test-policy actions):** For `attempt` in `0 .. ARLO_SCRIPT_TEST_MAX_ATTEMPTS-1`: Activity `execute_jamf_test` (`jamf_ops_agent`) uploads the latest script, binds it to Policy **1460**, runs `jamf_execute_test_policy` (event `arlo_test`), persists `test_execution_log`. If `exit_code == 0`, exit the loop. Else Activity `write_script` in refactor mode (`script_writer_agent` receives stdout/stderr), persist a new `generated_script` (`attempt+1`), and re-test. Bound exceeded or policy deny → Workflow → `Failed`; do not apply off-list production policies.
9. **Activity `execute_approved`:** New Claude SDK session; `allowed_tools` = intersection of PRD write actions and frozen list (Intune / Jira / SNOW / remaining Jamf profile applies). Idempotent retries. Default halt remaining writes on first failure. CHG create only if on list. Jamf test-policy tools already consumed by step 8 are not re-run unless they remain and were not completed.
10. **Activity `validate_and_close` (Persist Phase on success):** Read compliance/asset. Close/transition only if on approved plan **and** validation criteria passed (PRD default: no close on partial). On **successful** validation of a **new** or reused fix: append a `learned_patterns` row or increment `success_count` / `last_verified_at` for the matching pattern so later instances (e.g. `ARLO-680`) inherit it immediately. Reject / Failed / Cancelled **must not** persist or increment. Success → `Done`.

**Expected outputs and data formats (MVP contracts):**

- Evidence pack and proposal: versioned JSON stored on `instances` (columns or jsonb). Proposal identity = `proposal_hash` (canonical JSON hash).
- Run artifacts: `run_artifacts` rows (`discovery_pack`, `generated_script`, `test_execution_log`) linked by `arlo_id`; see §4.
- Approval record: actor, timestamp, action, frozen action list copy, matching `proposal_hash`.
- Audit event: `{ at, arlo_id, phase, kind, summary, mcp_system?, action?, result?, policy_deny? }` append-only. Retrieval and persist kinds include `memory_retrieve`, `kb_search`, `pattern_persist`, `artifact_persist`, `script_test`, `script_refactor`.
- `learned_patterns` / `kb_search` hits: included in the evidence pack; pattern persist is Activity SQL, not a Temporal Signal.

**Error handling, retries, cancellation / timeout:**

| Class | Behavior |
|---|---|
| Activity failure (MCP/LLM transient) | Temporal retry policy with backoff; idempotency keys on writes (instance id + proposal_hash + action id) |
| Activity failure (policy deny, unauthorized tool) | Do not retry as success; audit deny; Workflow → `Failed` |
| Model provider down during Investigation | Remain `Investigating` or `Failed` with Diagnostic; **never** execute writes to catch up |
| Model provider down while `Awaiting Approval` | Stay asleep; Signal still valid later |
| Jira/SNOW down | PostgreSQL + Temporal remain source of truth for in-flight approvals |
| Operator Cancel | Signal `cancel`; if Activities running, request Temporal cancel; writes already issued are not silently rolled back (record in audit) |
| Turn/token budget exceeded | Halt Activity; Diagnostic; no fail-open writes |
| Policy 1460 `exit_code != 0` | Persist `test_execution_log`; invoke `script_writer_agent` refactor; re-test. After max attempts: Diagnostic + `Failed`; no additional vendor writes |

**Performance budgets (MVP defaults; configurable):**

- Per-instance investigation: max turns **24**, wall clock **15 min**, token cap documented in worker config.
- Per-instance execution: max turns **16**, wall clock **15 min**.
- Script test-loop: max **3** attempts (`ARLO_SCRIPT_TEST_MAX_ATTEMPTS`); each attempt is a new Activity / SDK session.
- `max concurrent runs` default **5** (PRD recommendation); hard demo bar **≥ 2**.
- HITL wait: **no** LLM turns; no Activity heartbeat required for the wait itself.

#### Runtime-Conditional Configuration — `claude-agent-sdk`

- **Coordinator:** main runtime agent in each Activity’s `ClaudeAgentOptions` is `arlo_orchestrator`. Specialists as `AgentDefinition` entries keyed `discovery_agent`, `script_writer_agent`, `jamf_ops_agent` (`worker/agents/`).
- **Hooks:** `PreToolUse` = PEP (deny writes unless `approval_record` in Activity context and tool name ∈ frozen list); `PostToolUse` = audit append (redact secrets). `SubagentStart` / `SubagentStop` logged.
- **`allowed_tools`:** Investigation = `discovery_agent` read set only **plus** `kb_search`. Proposal / `write_script` = **no** vendor tools (`script_writer_agent.tools = []`). Execution test-loop = `jamf_ops_agent` write set ∩ frozen list. Remaining Execution = approved write tools only. `discovery_agent` **never** includes vendor writes or pattern-persist tools. Pattern persist is Activity code after validation success, not a model-invoked write tool.
- **Session policy:** new `ClaudeSDKClient` per Activity invocation; close on Activity completion. Each test-loop attempt is a new session. Do not resume SDK session across HITL. Workflow Id is the durable session.
- **MCP:** pass MCP server configs into the SDK client for that Activity (HTTP/SSE and/or stdio — see §6). Validate server availability at Activity start; fail fast with Diagnostic. `jamf_execute_test_policy` is the only path that represents `sudo jamf policy -event arlo_test`.
- **Built-in SDK file/shell tools:** **not** enabled for MVP (PRD does not authorize filesystem/git). Least privilege: MCP authorized actions only.
- **Do not** generate CrewAI `config/agents.yaml` as the MVP runtime.

#### Temporal HITL: pausing without tying up resources

When the Workflow reaches the approval gate it **does not** sleep in Python `time.sleep`, hold a worker thread, or poll Claude.

1. Proposal Activity completes. Workflow records local state (`proposal_hash`) and enters:

   `await workflow.wait_condition(lambda: self._decision is not None)`

   after registering `@workflow.signal def approval_decision(...)`.

2. Temporal **completes the current Workflow Task** and appends history to the cluster store. The Workflow is **not** on a worker task queue until a new event exists.

3. The worker process is free to run **other** instances’ Activities (FR-P0-09). No Claude SDK client, no MCP stdio/HTTP session, no Anthropic connection is held for the sleeping instance.

4. Human Approve/Reject in Next.js → FastAPI persists the approval/rejection row → `signal_workflow("approval_decision", payload)`. Optional: Jira/ServiceNow webhook with the same payload shape also Signals (P1/auto-spawn is separate; webhook-to-Signal is the wake mechanism).

5. Temporal schedules a new Workflow Task. The worker **replays** deterministic history, restores `self._decision` from the Signal event, `wait_condition` returns, and Execution Activity is scheduled **only if** `action == approve` and hashes match.

Timers for auto-approve are **not** registered (PRD: no auto-approve). A Cancel Signal is the only other wake path besides Approve/Reject.

---

### 3. Frontend Architecture Specification

**Technology Stack** (from PRD + operator constraint):

| Choice | MVP |
|---|---|
| Framework | Next.js (App Router) + React |
| Language | TypeScript (`coding_standards.type_checking: true`; frontend exception to Python-primary backend) |
| Styling | Minimal system theme (`ui.theme: system`, `visual_style: minimal`); CSS modules or equivalent — no mandatory vendor UI kit |
| State | Server Components where possible; client poll hook for grid/detail |
| Modals | Prefer in-page panels (`prefer_modals: false`) |

**Application Structure**:

| Route | Purpose |
|---|---|
| `/` | Run grid (active + historical); spawn control |
| `/runs/[arloId]` | Instance detail: status, Approve/Reject, **tabs** Proposal / Script / Test Logs / Audit Trail |
| `/login` | Authenticated app users (no anonymous Approve) |

**API client boundary:** a single `lib/api` module (typed client) calls FastAPI. Frontend epic must not embed Temporal/MCP/Anthropic SDKs. Integration epic wires base URL and auth cookies/headers.

**Components (indicative):** `RunGrid`, `SpawnPanel`, `StatusBadge` (text labels, not color-only), `ProposalPanel`, `ScriptPanel`, `TestLogPanel`, `ApprovalActions`, `AuditTimeline`, `BannerSleeping`, `RunDetailTabs`. Persistent banner on Awaiting Approval: agent is sleeping; **no endpoint or ticket changes until you approve.** Copy near spawn: same guarantee. Proposal/audit should surface cited `learned_patterns` ids and `kb_articles` titles when present (Approve transparency; Open Question 21).

**Instance detail tabs (operator 2026-09-01; Next.js fetch contract):**

| Tab | Data source | Client call (poll with status while non-terminal) |
|---|---|---|
| **Proposal** | `instances.proposal_json` + `proposal_hash` | `GET {API}/api/v1/instances/{arloId}` → `proposal` |
| **Script** | Latest (then prior versions of) `run_artifacts` where `artifact_type=generated_script` | `GET {API}/api/v1/instances/{arloId}/artifacts?type=generated_script` — render `content_text` + `metadata_json.language` / `attempt` |
| **Test Logs** | `run_artifacts` where `artifact_type=test_execution_log` (newest first) | `GET {API}/api/v1/instances/{arloId}/artifacts?type=test_execution_log` — render `metadata_json.exit_code`, `stdout`, `stderr`, `policy_id`, `event` |
| **Audit Trail** | `audit_events` | Existing `GET {API}/api/v1/instances/{arloId}/audit` |

`API` is `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`). The Next.js App Router page `/runs/[arloId]` must not query Temporal or PostgreSQL directly. Optional convenience: `GET /instances/{arloId}` may also return `latest_artifacts` `{ discovery_pack, generated_script, test_execution_log }` so the first paint does not require a second round-trip. Empty Script / Test Logs tabs show an explicit empty state (script is drafted during Investigating; logs appear only after Approve + test-loop).

**Responsive / a11y:** desktop-width first; mobile not MVP. Keyboard-operable Approve/Reject. Status vocabulary exact: **Investigating**, **Awaiting Approval**, **Executing**, **Done**, plus **Rejected**, **Failed**, **Cancelled**.

**Interface Requirements**:

- Primary surface is the **control-plane dashboard**, not a chat thread (chat-inside-instance is P1 placeholder).
- Loading: spawn returns `< 3s` to a visible row (PRD §5); grid shows last known status while polling.
- Errors: in-page for invalid ticket id (no instance created); instance-level Diagnostic for MCP/LLM failures; never show success on policy deny.
- Future Work placeholders (visible, non-functional): webhook auto-spawn, KEV badges, request-changes, audit export.

---

### 4. Backend Architecture Specification

**API Architecture**:

Base path `/api/v1`. JSON. Auth required except `/health` and `/ready`.

| Method | Path | Purpose |
|---|---|---|
| POST | `/instances` | Spawn: `{ ticket_system: jira\|servicenow, ticket_id }` → `{ arlo_id, status: "Investigating" }` |
| GET | `/instances` | Grid: query `status`, pagination |
| GET | `/instances/{arlo_id}` | Detail: mapping, status, timestamps, proposal, approval summary, optional `latest_artifacts` |
| GET | `/instances/{arlo_id}/artifacts` | Run artifacts for UI tabs; query `type` = `discovery_pack` \| `generated_script` \| `test_execution_log` |
| GET | `/instances/{arlo_id}/artifacts/{artifact_id}` | Single artifact body |
| GET | `/instances/{arlo_id}/audit` | Append-only events, chronological |
| POST | `/instances/{arlo_id}/approve` | `{ proposal_hash }` → persist approval + Temporal Signal |
| POST | `/instances/{arlo_id}/reject` | `{ proposal_hash, reason? }` → persist + Signal |
| POST | `/instances/{arlo_id}/cancel` | Signal cancel if not terminal |
| POST | `/webhooks/jira` | Verify signature; map to Signal and/or P1 auto-spawn (P1 spawn not required to demo lifecycle) |
| POST | `/webhooks/servicenow` | Same pattern |
| GET | `/health` | Liveness |
| GET | `/ready` | PostgreSQL + Temporal connectivity |

**Request/response notes:**

- Spawn without ticket id → 400; no row.
- Duplicate active mapping to same ticket: **warn or 409** (PRD Open Question 3 — default **409 conflict** until product amends).
- Approve with mismatched `proposal_hash` → 409; no Signal.
- Approve disabled unless proposal + audit readable (enforced by returning both on GET detail; UI hides actions unless status is Awaiting Approval).

**Error envelope:** `{ "error": { "code": "...", "message": "...", "arlo_id": "..." } }` with stable codes (`validation_error`, `conflict`, `not_found`, `unauthenticated`, `policy_deny`, `upstream_unavailable`).

**Rate limiting (MVP):** coarse per-user spawn cap (e.g. align with max concurrent runs); not a CDN WAF.

**Streaming:** MVP list/detail are request/response. Do not require LLM token streaming to the browser. Optional later: SSE audit tail.

**Data Architecture**:

PostgreSQL is in MVP (PRD durable store + operator constraint). Temporal persistence is **separate** (Temporal’s own store via the Compose Temporal service). Enable the **`pgvector`** extension on the application database for the Vector KB.

Three logical schemas in one Postgres instance (same `DATABASE_URL`; schemas may be `app`, `memory`, `kb` or a single `public` schema in MVP):

1. **Application control plane** — users, instances, approvals, audit_events, **run_artifacts**  
2. **Shared Operational Memory** — `learned_patterns`  
3. **Vector Knowledge Base** — `kb_articles`

**Logical tables (application):**

- `users` — id, username, password hash or IdP subject, created_at  
- `instances` — arlo_id PK, ticket_system, ticket_key, status, proposal_json, proposal_hash, workflow_id, created_at, updated_at, created_by  
- `approvals` — id, arlo_id, action, actor_id, at, proposal_hash, frozen_actions_json, rationale  
- `audit_events` — id identity, arlo_id, at, phase, kind, summary, payload_json (redacted), policy_deny bool  
- `run_artifacts` — id, arlo_id, artifact_type, attempt, content_text, content_json, metadata_json, created_by_agent, created_at  

No silent updates of past `audit_events`. Artifact rows are **append-only** (a refactor inserts a new `generated_script` with a higher `attempt`; prior versions remain for the Script tab history). Instance status is updated by Activities and by API on Signal acknowledgement; Workflow remains authority for “has execution been allowed.”

**Table: `run_artifacts` (instance-scoped dashboard artifacts)**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `arlo_id` | VARCHAR | FK → `instances.arlo_id` (correspondence key) |
| `artifact_type` | VARCHAR | `discovery_pack` \| `generated_script` \| `test_execution_log` |
| `attempt` | INT | `0` for the pre-HITL draft; incremented on each test-loop refactor / test run |
| `content_text` | TEXT | Script body or concatenated stdout/stderr; null for JSON-only packs |
| `content_json` | JSONB | Discovery pack, structured test result `{ exit_code, stdout, stderr, policy_id, event, command }` |
| `metadata_json` | JSONB | `language` (`zsh` \| `powershell`), `platform`, `filename`, `policy_id`, `event`, `exit_code`, `script_artifact_id`; **no secrets** |
| `created_by_agent` | VARCHAR | `discovery_agent` \| `script_writer_agent` \| `jamf_ops_agent` \| `arlo_orchestrator` |
| `created_at` | TIMESTAMP | Insert time |

**Indexes (MVP):** `(arlo_id, artifact_type, created_at DESC)`, `(arlo_id, artifact_type, attempt)`.

**UI mapping:** Script tab = `generated_script` rows; Test Logs tab = `test_execution_log` rows; Proposal tab does **not** duplicate the full script (it may cite `script_artifact_id`). Discovery packs are available via the artifacts API for diagnostics; they are not a required fifth tab.

**Table: `learned_patterns` (Shared Operational Memory)**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `app_name` | VARCHAR | e.g. `node`, `iterm2` |
| `platform` | VARCHAR | e.g. `macOS`, `Windows` |
| `pattern_type` | VARCHAR | e.g. `script_fix`, `version_endpoint`, `vendor_gotcha` |
| `problem_description` | TEXT | Human-readable problem, e.g. “Jamf runs root scripts with clean PATH, missing /opt/homebrew/bin” |
| `solution_payload` | JSONB | Executable snippet or path-resolution logic — **evidence for a later proposal**, not a license to skip HITL |
| `created_by_arlo_id` | VARCHAR | Originating instance, e.g. `ARLO-675` |
| `success_count` | INT | Default **1** on insert; increment on later successful validations of the same pattern |
| `created_at` | TIMESTAMP | Insert time |
| `last_verified_at` | TIMESTAMP | Last successful Validation that confirmed the pattern |

**Indexes (MVP):** `(app_name)`, `(platform)`, `(app_name, platform, pattern_type)`. Natural-key match for increment: `app_name` + `platform` + `pattern_type` + canonical hash of `problem_description` (or equivalent); if no match, **append** a new row. Do not increment on Failed / Rejected / Cancelled.

**Table / extension: `kb_articles` (Vector KB, `pgvector`)**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `title` | VARCHAR | e.g. “DocuSign FileVault Re-encryption SOP” |
| `category` | VARCHAR | e.g. `jamf_sop`, `intune_policy`, `compliance` |
| `content` | TEXT | Full markdown runbook |
| `embedding` | VECTOR(1536) | Embedding for semantic search (OpenAI-compatible 1536-d; Anthropic gateway if it exposes the same dimension) |
| `metadata_json` | JSONB | Source, version, owners — no secrets |

**Indexes (MVP):** ivfflat or hnsw on `embedding` (cosine / L2 per Build choice); btree on `category`. Ingest/re-embed is a setup or admin path, **not** an Investigation write tool.

**Write vs read authority:**

| Store | Investigation | Execution | Validation success |
|---|---|---|---|
| Vendor MCP (Jira/SNOW/Jamf/Intune) | Reads only (`discovery_agent`) | Approved writes only (`jamf_ops_agent` / orchestrator) | Validation reads; ticket writes iff approved |
| `run_artifacts` | INSERT `discovery_pack`; INSERT initial `generated_script` | INSERT `test_execution_log`; INSERT refactored `generated_script` | No artifact delete |
| `learned_patterns` | SELECT + inject | No persist | INSERT or increment |
| `kb_articles` | `kb_search` only | Not required | No article write from the agent |

**Runtime Integration Layer**:

- FastAPI uses Temporal Python SDK: `client.start_workflow(ArloRemediationWorkflow.run, args, id=workflow_id, task_queue="arlo-activities")`.
- Worker process (same repo, separate entrypoint) registers Workflow + Activities; Activities construct `ClaudeSDKClient` with phase-specific `allowed_tools`, `AgentDefinition` map from `worker/agents/`, MCP servers, hooks, turn/token caps.
- Agent configuration: code + env (model name, max turns, MCP endpoints, `JAMF_TEST_POLICY_ID`, `JAMF_TEST_EVENT`, `ARLO_SCRIPT_TEST_MAX_ATTEMPTS`) — not CrewAI YAML.
- Prompt Trace / execution diagnostics: redact and write under `project-context/2.build/logs` during Build; production-like runs also append `audit_events`. Secrets never in Prompt Trace.

**Authentication & Secrets** (names only):

| Name | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Claude Agent SDK |
| `ANTHROPIC_BASE_URL` | Optional org gateway |
| `DATABASE_URL` | PostgreSQL |
| `TEMPORAL_ADDRESS` | Temporal frontend gRPC |
| `ARLO_SESSION_SECRET` | FastAPI session/JWT signing |
| `JIRA_MCP_URL` / `JIRA_MCP_TOKEN` | Remote Jira MCP (HTTP/SSE) |
| `SNOW_MCP_URL` / `SNOW_MCP_TOKEN` | ServiceNow MCP |
| `JAMF_MCP_URL` / `JAMF_MCP_TOKEN` | Jamf MCP |
| `JAMF_TEST_POLICY_ID` | Isolated test policy id (default **1460**) |
| `JAMF_TEST_EVENT` | Isolated test event (default `arlo_test`) |
| `ARLO_SCRIPT_TEST_MAX_ATTEMPTS` | Test-loop bound (default **3**) |
| `INTUNE_MCP_URL` / `INTUNE_MCP_TOKEN` | Intune MCP |
| `JIRA_WEBHOOK_SECRET` | Webhook HMAC (when enabled) |
| `SNOW_WEBHOOK_SECRET` | Webhook HMAC (when enabled) |
| `EMBEDDING_API_KEY` | Embedding provider for `kb_articles` / `kb_search` (1536-d) |
| `EMBEDDING_BASE_URL` | Optional org embedding gateway |
| `EMBEDDING_MODEL` | Model id that produces **1536** dimensions |

Stdio stub mode uses process command env (e.g. `JIRA_MCP_STDIO_CMD`) instead of URL/token. Never commit values. `.env.example` is a Build/setup deliverable. Do not read or copy values from a local `.env` into artifacts.

---

### 5. DevOps & Deployment Architecture

**CI/CD** (minimal MVP; generated in Deliver, not run live from this SAD): lint, unit test, integration test, frontend build. Set `AAMAD_TARGET_RUNTIME=claude-agent-sdk` in CI so adapter-registry cannot default to `crewai`.

**Hosting:** smallest AAMAD-appropriate target — **Docker Compose** on a laptop/dev host:

- `frontend` — Next.js (e.g. port 3000)  
- `api` — FastAPI (e.g. port 8000); health `/health`  
- `postgres` — image with **`pgvector`** (or `CREATE EXTENSION vector` on startup)  
- `temporal` + Temporal UI (dev)  
- `worker` — Python Temporal worker (Claude SDK + MCP clients + internal `kb_search` MCP)  

No multi-region, no Kubernetes, no live production deploy without explicit operator authorization.

**IaC / advanced monitoring:** Future Work.

**Observability:** structured logs (instance id, workflow id, phase); health/readiness; Temporal Web for Workflow history during demo. APM deferred. Product audit log is the operator-facing observability surface.

---

### 6. Data Flow & Integration Architecture

#### Process / runtime view — execution flow

Happy path: operator spawn → **Retrieval** (patterns + `kb_search`) → `discovery_agent` investigate → persist discovery pack → `script_writer_agent` draft → propose → **Signal wait** → approve → **test-loop** (`jamf_ops_agent` Policy 1460 / `arlo_test` → persist logs → refactor on non-zero → re-test) → remaining approved writes → validate → **Persist** `learned_patterns` → Done.

![ARLO execution sequence](diagrams/arlo-execution-sequence.png)

Source: `diagrams/arlo-execution-sequence.mmd` (rendered with mermaid-cli).

Webhook path (same Signal, different ingress): Jira/ServiceNow → `POST /webhooks/*` → verify secret → persist decision if it is an approval payload → `signal_workflow`. Auto-**spawn** from ticket-created webhooks remains **P1**.

#### MCP connection model

MCP is how Claude tools reach enterprise systems. The Worker is the MCP **client**; servers are not embedded in Next.js or FastAPI.

| Mode | Transport | When to use | Lifecycle |
|---|---|---|---|
| Remote | **HTTP + SSE** (or MCP streamable HTTP as implemented by the SDK) | Shared/dev tenant MCP gateways for Jira, ServiceNow, Jamf, Intune | Open inside Activity; close when Activity ends |
| Local stubs | **stdio** child processes | Capstone fixtures when live tenants are unavailable | Spawn per Activity (or short-lived pool scoped to Activity); never leave stdio servers running as a substitute for HITL |
| Internal `kb_search` | **In-process MCP** (adapter default) or stdio | Vector KB over `kb_articles` | Open inside Investigation/Proposal Activity; close when Activity ends; no persist tools |

**Rules:**

- ARLO may only invoke PRD §3.4 vendor actions plus internal **`kb_search`**; servers should expose that surface (deny-by-default).
- Investigation Activities get `discovery_agent` read tools only (vendor reads + `kb_search`); `write_script` gets **no** MCP tools; Execution test-loop gets `jamf_ops_agent` write subset ∩ frozen list; remaining Execution Activities get the approved write subset.
- Fail closed if a required MCP server is unauthorized or unavailable — Diagnostic, do not skip HITL, do not fake successful writes.
- Intune sync remains classified as read-side refresh in Investigation/Validation.
- Unauthorized (wipe, lost-mode, credential dump, arbitrary script, off-proposal device, Bash/`sudo` on the SDK agent) must not be registered in `allowed_tools`. `jamf_execute_test_policy` is the only representation of `sudo jamf policy -event arlo_test`.

#### Error-handling loop — Policy 1460 / `arlo_test` (Execution)

This loop is **post-HITL**. The human approved the Jamf write verbs and the test-policy targets (Policy **1460**, event `arlo_test`) on the proposal. Script **bytes** may change; systems, action types, policy id, event name, and device scope may not.

```
attempt := 0
latest_script := latest generated_script for this arlo_id
while attempt < ARLO_SCRIPT_TEST_MAX_ATTEMPTS:
    jamf_ops_agent:
        jamf_upload_script(latest_script)
        jamf_policy_set_script(policy_id=1460, script_id)
        result := jamf_execute_test_policy(policy_id=1460, event=arlo_test)
        persist run_artifacts.test_execution_log (exit_code, stdout, stderr)
    if result.exit_code == 0:
        break
    attempt := attempt + 1
    if attempt >= ARLO_SCRIPT_TEST_MAX_ATTEMPTS:
        Diagnostic; Workflow → Failed; stop
    script_writer_agent:
        refactor(latest_script, stdout, stderr)   # no MCP tools
        persist run_artifacts.generated_script (new attempt)
        latest_script := that row
```

Each iteration is a **new Temporal Activity** and a **new** `ClaudeSDKClient` (SAD AD-8). Temporal retries still apply to transient MCP/LLM errors **inside** an attempt; a non-zero Jamf exit is **not** a transient error and must not be retried as success. After a passing test, `execute_approved` may apply remaining frozen writes (Jira comment/transition, SNOW CHG, Intune, `jamf_apply_profile`). A failing test never authorizes those remaining writes.

#### State machine (illegal transitions are product bugs)

![ARLO instance state machine](diagrams/arlo-state-machine.png)

Source: `diagrams/arlo-state-machine.mmd` (rendered with mermaid-cli).

UI labels: Investigating includes Trigger through proposal generation **and the Retrieval Phase** (`learned_patterns` SELECT + `kb_search`); Awaiting Approval is the Signal wait; Executing covers approved writes and validation; **Done** includes the Persist Phase (append/increment `learned_patterns`). Rejected / Failed / Cancelled are terminal and **must not** persist memory.

**Correspondence:** UI status = `instances.status` = Workflow-reported phase. Execution Activity is unreachable without a Signal + matching approval row. PEP still denies writes if the model requests an off-list tool. A retrieved pattern is **not** an approval record for this instance.

#### Cross-instance memory propagation

Two-way loop (operator examples `ARLO-675` persist → `ARLO-680` retrieve):

1. **Retrieval Phase (Investigation).** When a new instance starts, the Investigation Activity extracts `app_name` / `platform` (and keywords) from ticket metadata, queries `learned_patterns` for matches, and calls `kb_search`. Results are injected into Claude context **before** proposal generation. Sibling Claude sessions stay isolated; only the Postgres rows are shared.
2. **Persist Phase (Validation → Done).** After `ARLO-675` (or any instance) successfully validates a new or reused fix, the Validation Activity inserts a `learned_patterns` row or increments `success_count` and `last_verified_at`. Subsequent Investigation Activities see the row immediately — no Workflow Signal to other instances is required.
3. **HITL unchanged.** Inheritance is **grounding only**. `ARLO-680` still proposes, sleeps, and waits for a human. `solution_payload` must appear on that instance’s enumerated action list before any vendor write.

**Error propagation:** Activity raises → Temporal retry or Workflow failure handler → `instances.status = Failed` + audit Diagnostic → UI shows Failed with last successful action identified (PRD §6). Policy deny → audit `policy_deny` + not treated as success (FR-P0-10). Policy 1460 non-zero exit → Test Logs tab + optional Script tab new version; after the attempt bound, same Failed path.

---

### 7. Performance & Scalability Specifications

| Target | MVP |
|---|---|
| Spawn → row visible | **< 3s** excluding first-time MCP auth (PRD §5) |
| First investigation audit artifacts | Begin within **1 minute** under nominal LLM/API conditions; Diagnostic if vendors stall |
| Concurrency | Demonstrate **≥ 2** isolated instances in different phases; configurable cap default **5** |
| HITL sleep | **Zero** LLM turns; worker not blocked |
| Dashboard freshness | Poll interval on the order of **2–5s** while a run is non-terminal |

**Scaling path (deferred):** queue spawn when at cap (P1); Temporal worker replicas; Temporal Cloud. Horizontal app scale is not required for capstone. Cost driver is tokens × concurrent Activities, not cluster size (PRD §3.6).

**Token / cost controls:** per-Activity turn and token caps; max concurrent Workflows; no investigation loop while Awaiting Approval.

---

### 8. Security & Compliance Architecture

**AuthN/AuthZ (MVP):**

- Authenticated application users (session cookie or signed token). **No anonymous Approve.**
- Approver identity stored on `approvals.actor_id` (attributable).
- Role split (ticket assignee vs MDM admin vs change manager) is a **PRD Open Question** — default: any authenticated ARLO user may Approve until product amends. Record in Open Questions.
- Webhooks: HMAC secret; never unauthenticated Signal.

**Enforcement layers for mutations:**

1. Temporal: Execution Activity not scheduled without Approve Signal.  
2. SDK: write tools not in `allowed_tools` before approval context.  
3. `PreToolUse` PEP: deny + audit.  
4. MCP server should also reject out-of-catalog actions (defense in depth; product still owns fail-closed).  
5. `learned_patterns` persist is an internal SQL write after Validation success — **not** a substitute for HITL on a later ticket.  
6. `kb_search` is read-only; KB ingest is admin/setup, not an agent write tool.

**Encryption and validation:** TLS to remote MCP and Anthropic; secrets only in env; parameterized SQL; validate ticket id and enums; canonical-JSON hash for proposals.

**Data protection:** ticket text, device logs, asset data, runbooks, and `solution_payload` stay in PostgreSQL and vendor systems; redact secrets in UI, Jira comments, CHG text, audit payload, Prompt Trace, `metadata_json`, and pattern payloads. No training-data exfil by ARLO. Embeddings are of redacted content only.

**Compliance:** capstone is not a declared EU AI Act high-risk deployment; HITL + audit designed for oversight review. `security.require_security_assessment: true` — `@security.eng` → `project-context/2.build/security.md` required before Deliver. ServiceNow CHG create is tracking, not a license to skip ARLO HITL.

---

### 9. Testing & Quality Assurance Specifications

`testing.require_unit_tests` and `require_integration_tests` are on. Map tests to PRD acceptance criteria.

| Layer | Expectations |
|---|---|
| Unit | Proposal hash stability; illegal status transitions; PEP deny matrix; API validation; `learned_patterns` increment vs insert; `kb_search` input defaults; specialist `AgentDefinition.tools` segregation; `run_artifacts` append-only; test-loop bound |
| Integration | FastAPI + PostgreSQL + pgvector; Temporal test env (time-skipping); spawn → Signal → execute path with **MCP stubs**; retrieve-after-persist across two instance ids |
| HITL / QA bypass | Write tools invoked in Investigating must fail and audit (FR-P0-04, FR-P0-10); unapproved mutations = **zero**; retrieved `solution_payload` must not execute without Approve |
| Concurrency | Two Workflows, different phases, no crossed mappings/audit (FR-P0-09); memory rows are shared read, not shared Claude state |
| Smoke | Fixture ticket → Awaiting Approval → Approve → Done (or Rejected) on dashboard |
| Runtime adapter | Hooks fire; `allowed_tools` per phase; Diagnostic on missing MCP |
| Security | `security.md` before Deliver; no secrets in fixtures/traces |

Stubs must not report write success that skipped the gate.

---

### 10. MVP Launch & Feedback Strategy

**Pilot criteria:** local Compose; ≥2 concurrent named instances; one Approve path and one Reject path; audit shows reads before HITL and writes only after; operator copy visible.

**Success metrics (from PRD §7):** time to Awaiting Approval; time Approve → Done; approve/reject/cancel mix; unapproved mutations = 0; HITL bypass blocked 100% in QA; concurrent ≥ 2; no secrets in UI/tickets/CHGs/traces.

**GTM:** N/A (capstone). Operator “launch” is Deliver `user-guide.md` + runbook.

**Iteration after first deploy:** P1 webhook auto-spawn and request-changes; tighten Approve ACL; live MCP vs stubs; Intune sync reclassification if Security requires; KB ingest UX and pattern allow-listing if Open Questions 18–19 land.

---

## Implementation Guidance for AI Development Agents

1. Foundation setup per `setup.md` epic: Python env, Next.js app, PostgreSQL **with pgvector**, Temporal Compose, `.env.example` (including `EMBEDDING_*` names), `AAMAD_TARGET_RUNTIME=claude-agent-sdk`.
2. Frontend MVP UI without backend wiring: grid, spawn panel, detail, statuses, audit placeholder, Approve/Reject disabled until API exists.
3. Backend: FastAPI contracts, PostgreSQL schema including `learned_patterns` + `kb_articles` / pgvector + `run_artifacts`, Temporal Workflow/Activities, Claude Agent SDK specialists in `worker/agents/`, MCP client config (`kb_search` in Investigation; Jamf test-policy tools only after HITL), PEP hooks — no CrewAI YAML.
4. Integration epic wires FE ↔ BE (auth, poll, approve Signal).
5. QA: unit, integration, HITL bypass, dual-instance smoke.
6. `@security.eng` assessment; then Deliver packages deploy/CI/runbook/user-guide only — no live deploy unless authorized.

---

## Architecture Validation Checklist

- [x] PRD requirements mapped to architectural components (instances, HITL Signal wait, MCP phase split, dashboard + audit, Central Memory + Vector KB)
- [x] Agents designed for the domain and selected runtime (`claude-agent-sdk` `arlo_orchestrator` + `discovery_agent` / `script_writer_agent` / `jamf_ops_agent`)
- [x] Frontend and backend contracts agree on schemas / polling (no LLM stream required)
- [x] Secrets via env vars only
- [x] MVP vs Future Work boundaries explicit
- [x] Resolved AAMAD_TARGET_RUNTIME: claude-agent-sdk recorded in Audit

---

## Sources

1. `project-context/1.define/prd.md` (2026-08-31) — product-authoritative: persona, HITL, MCP authorized actions, lifecycle, dashboard, NFRs, Open Questions.  
2. Operator instruction (2026-08-31) for this SAD: Temporal.io durable loops and Signal wait; Claude SDK in Activities; MCP (Jamf, Intune, ServiceNow, Jira) HTTP/SSE or stdio; FastAPI or Node; Next.js/React; PostgreSQL; Logical Architecture; execution-flow and state-machine Mermaid.  
2b. Operator instruction (2026-08-31) SAD update: Central Memory (`learned_patterns`) and Vector KB (`kb_articles` / pgvector / `kb_search`); retrieval in Investigation; persist on Validation success; diagram updates.  
2c. Operator instruction (2026-09-01) SAD update: Subagent Specialist Topology (`arlo_orchestrator`, `discovery_agent`, `script_writer_agent`, `jamf_ops_agent`); `run_artifacts` + `/runs/[arloId]` tab fetch contract; Policy 1460 / `arlo_test` error-handling loop.  
3. `project-context/1.define/mrd.md` (2026-08-31) — transferable only: HITL-as-architecture, named concurrent instances, dashboard, `claude-agent-sdk` hooks/MCP/session, OWASP Excessive Agency. **Not** used for AppSec/git MVP architecture.  
4. `aamad.config.yml` — `runtime.target: claude-agent-sdk`, `language.primary: python`, `libraries.approved: [claude-agent-sdk]`, UI system/minimal, `prefer_modals: false`, `security.require_security_assessment: true`, unit+integration tests, user guide.  
5. `.cursor/templates/sad-template.md`, `.cursor/agents/system-arch.md`, `.cursor/rules/aamad-core.mdc`, `.cursor/rules/adapter-registry.mdc`, `.cursor/rules/adapter-claude-agent-sdk.mdc`, `AGENTS.md` (AAMAD 0.7.5).  
6. User stories: none present.  
7. Temporal Signal / `wait_condition` worker-eviction behavior: Temporal Python SDK Workflow patterns (HITL wait does not occupy a worker while idle). Implementation version pinned in Build `setup.md` / `backend.md`.

## Assumptions

- PRD supersedes MRD domain; this SAD does not restore git/PR/SAST components.
- Resolved AAMAD_TARGET_RUNTIME: claude-agent-sdk. Config `runtime.target` matches. Operator exported `AAMAD_TARGET_RUNTIME=claude-agent-sdk` in the project terminal (2026-08-31); that export is session-local and is **not** inherited by new shells or this agent unless re-exported or set in Cursor/CI.
- Backend language is **Python FastAPI + Temporal Python SDK + claude-agent-sdk**; Node.js/TypeScript API was the unused operator alternative.
- Frontend TypeScript is required by Next.js despite `language.secondary: []`.
- Capstone Compose Temporal (dev) is sufficient; Temporal Cloud is not required.
- MCP **server implementations** are out of scope for this SAD beyond transport and authorized-action binding (PRD §3.4). Stubs via stdio are acceptable if they fail closed.
- Default duplicate-ticket policy is **reject second active spawn (409)** until Open Question 3 is resolved.
- Any authenticated user may Approve in MVP until Open Question 2 is resolved.
- Claude SDK session resume across HITL is **not** used; Temporal + PostgreSQL satisfy PRD durable session.
- Polling satisfies UI-P0-03 for MVP.
- Approver identity is the authenticated ARLO user id, not a Jira account, unless later integrated.
- Idempotency key for writes = `arlo_id` + `proposal_hash` + action identifier; Activities check-then-act against vendor read APIs where feasible (e.g. existing CHG).
- Central Memory and Vector KB are **operator architectural constraints**, not new PRD functional IDs. They do not authorize vendor writes. LLM memory remains off.
- Embedding dimension is **1536** as specified. Default embedding path is OpenAI-compatible; an Anthropic/org gateway is used only if it emits the same dimension.
- `kb_articles` ingest is setup/admin (seed SOPs), not an agent mutation. `learned_patterns` persist is Activity SQL after Validation success.
- Natural key for increment: `app_name` + `platform` + `pattern_type` + hash of `problem_description` until product defines fuzzy merge.
- KB/memory unavailability is a declared evidence gap, not fail-open and not a skip of HITL.
- Operator 2026-09-01 specialist names refine PRD `arlo` / `arlo-investigator` / proposal specialist / `arlo-executor`; they do not add a fifth product role.
- `jamf_upload_script`, `jamf_policy_set_script`, and `jamf_execute_test_policy` bind PRD §3.4 “Apply approved configuration profiles or scripts.” They are not new product verbs; `@product-mgr` may still list them as separate PRD rows for catalog clarity (Open Question 22).
- Policy **1460** and event `arlo_test` are operator-designated isolated test-policy identifiers (overridable via env **names** `JAMF_TEST_POLICY_ID` / `JAMF_TEST_EVENT`). The SDK agent is never given Bash/`sudo`.
- The Policy 1460 loop runs **after** Approve so HITL still covers the Jamf write verbs and targets. Script-body revision inside the bound is in-scope; new systems, devices, or policy ids are not.
- `run_artifacts` is the PRD §3.5 “artifact links” store. Next.js reads FastAPI only.

## Open Questions

Carried from PRD where they affect architecture, plus SAD-specific items:

1. Jira Cloud vs Server/DC and ServiceNow prod vs subprod for fixtures (MCP URL/auth shape).  
2. Who may Approve (any user vs assignee vs MDM vs change manager) — ACL in FastAPI.  
3. Duplicate spawn on an active ticket — SAD default 409; confirm.  
4. Jira comment heartbeat pre-HITL — PRD default no; do not add a write tool for it.  
5. Intune device sync: confirm read-side vs mutation with `@security.eng`.  
6. Validation failure vs close-on-partial — PRD default do not close.  
7. Numeric `ARLO-<n>` vs encoding ticket key in the name (workflow id scheme).  
8. Final max concurrent instances and monthly LLM budget.  
9. Live MCP servers vs contract stubs for demo.  
10. Whether `@product-mgr` should produce user stories after this SAD.  
11. Trademark “ARLO” (from MRD).  
12. EU AI Act if demo uses EU personal device data.  
13. Webhook-originated **approval** (vs dashboard-only): operator asked the API to receive webhooks to Signal; product P0 actor remains the dashboard. Confirm Jira/SNOW can emit an approval event ARLO should trust.  
14. Temporal history size: if a single instance’s Activity retries explode history, continue-as-new policy — deferred unless observed.  
15. Sticky Workflow cache vs always-evict on Signal wait — implementation detail; product requirement is “worker not blocked.”  
16. Node.js backend alternative: closed for MVP unless operator overrides config language.  
17. Embedding provider (OpenAI vs Anthropic/org gateway) and exact `EMBEDDING_MODEL` that yields 1536 dimensions.  
18. Who may ingest/edit `kb_articles` (admin API vs seed SQL only).  
19. Whether `solution_payload` scripts must be allow-listed identifiers only (safer) vs stored snippet text.  
20. Fuzzy vs exact match when incrementing `learned_patterns.success_count`.  
21. Whether dashboard MVP must list matched patterns / KB citations on instance detail (recommended for Approve transparency; not in original UI-P0 list).  
22. Whether `@product-mgr` should split PRD §3.4 Jamf write into explicit `upload_script` / `policy_set_script` / `execute_test_policy` rows (SAD binds them as granular tools of the existing write).  
23. Whether a failing Policy 1460 test should return the instance to **Awaiting Approval** (request-changes, P1) instead of `Failed` after the attempt bound.  
24. Whether Windows/Intune should gain a symmetric `intune_ops_agent` (deferred; would be a fifth role unless it replaces `jamf_ops_agent` on that path).

## Audit

- **Timestamp:** 2026-08-31T19:28:00Z (operator local 2026-08-31 ~12:28 PDT)  
- **Persona id:** `system-arch`  
- **Action:** `create-sad --mvp`  
- **Output path:** `project-context/1.define/sad.md`  
- **Resolved AAMAD_TARGET_RUNTIME:** claude-agent-sdk via `aamad.config.yml` `runtime.target`. Operator export `AAMAD_TARGET_RUNTIME=claude-agent-sdk` confirmed in the project terminal (2026-08-31, exit 0). Agent/new shells do not inherit that session export unless it is persisted (shell profile, Cursor env, or CI).  
- **Config loaded:** `aamad.config.yml` (python, claude-agent-sdk, UI minimal/system, prefer_modals false, security assessment required, unit+integration tests, user guide)  
- **Inputs read:** `.cursor/agents/system-arch.md`, `.cursor/templates/sad-template.md`, `project-context/1.define/prd.md`, `project-context/1.define/mrd.md` (transferable excerpts), `aamad.config.yml`, adapter-registry and `adapter-claude-agent-sdk` rules, operator stack constraints  
- **Prompt Trace:** omitted. Define-phase architecture synthesis; no runtime agent execution against Jira/ServiceNow/Jamf/Intune; no secret-bearing prompts. Rationale: not a high-risk executable run; citations live in Sources.  
- **Model / temperature / max_tokens:** Cursor Grok 4.6 interactive session; temperature/max_tokens not independently set by this persona (IDE-controlled).  
- **Write method:** temp-write `sad.md.tmp` then atomic replace to `sad.md`.  
- **Prohibited actions honored:** no new product requirements beyond PRD + recorded operator stack constraints; no application code; no pipelines; no third-party system integration; AppSec/git not restored; secrets as env **names** only.  
- **Self-check (required template headings):** Context & Instructions; Input Requirements; §1 MVP Architecture Philosophy & Principles (including Logical Architecture); §2 Multi-Agent System Specification (including claude-agent-sdk subsection); §3 Frontend; §4 Backend; §5 DevOps; §6 Data Flow & Integration (execution flow + MCP + state machine); §7 Performance; §8 Security; §9 Testing; §10 Launch; Implementation Guidance; Architecture Validation Checklist; Sources; Assumptions; Open Questions; Audit.  
- **Mermaid:** logical architecture flowchart; sequence diagram (UI ↔ API ↔ Temporal ↔ Worker/Claude ↔ MCP); state machine. Rendered via `mmdc` 11.16.0 to `project-context/1.define/diagrams/*.png`.  
- **Tool usage:** Read (persona, PRD, template, config, adapter, MRD excerpts); Glob; Grep; Shell (`AAMAD_TARGET_RUNTIME`, UTC clock); Write temp; atomic replace.

- **Timestamp:** 2026-08-31T23:29:39Z (operator local 2026-08-31 ~16:29 PDT)  
- **Persona id:** `system-arch`  
- **Action:** `update-sad` (Central Memory + Vector KB)  
- **Resolved AAMAD_TARGET_RUNTIME:** claude-agent-sdk  
- **Inputs read:** `.cursor/agents/system-arch.md`, existing `sad.md`, PRD memory/MCP excerpts, operator schema and flow specification  
- **Changes:** §1 logical flowchart + AD-13/14/15; §2 investigator/`kb_search` contract + Retrieval/Persist orchestration; §4 `learned_patterns` and `kb_articles` schemas; §5 pgvector; §6 sequence, state machine, cross-instance memory loop; security/testing/assumptions/open questions  
- **Prompt Trace:** omitted (Define-phase doc update; no vendor execution; no `.env` values read).  
- **Write method:** in-place section updates to `sad.md` (template headings preserved).  
- **Prohibited actions honored:** no application code; no PRD rewrite; HITL not weakened; secrets as env names only.

- **Timestamp:** 2026-09-01T23:49:16Z (operator local 2026-09-01 ~16:49 PDT)  
- **Persona id:** `system-arch`  
- **Action:** `update-sad` (Subagent Specialist Topology + Artifact Storage Model + Policy 1460 error-handling loop)  
- **Output path:** `project-context/1.define/sad.md`  
- **Resolved AAMAD_TARGET_RUNTIME:** claude-agent-sdk via `aamad.config.yml` `runtime.target` (`AAMAD_TARGET_RUNTIME` unset in this shell; adapter-registry would otherwise default to `crewai` — config wins when env is absent).  
- **Config loaded:** `aamad.config.yml`  
- **Inputs read:** `.cursor/agents/system-arch.md`, existing `sad.md`, PRD §3.2–3.5 / §4.3, `aamad.config.yml`, adapter-claude-agent-sdk, operator instruction for four `AgentDefinition` specialists, `run_artifacts`, `/runs/[arloId]` tabs, Policy 1460 / `arlo_test` loop  
- **Changes:** §1 AD-16/17/18 + logical catalog; §2 specialist `AgentDefinition` specs and tool segregation; §3 detail-tab fetch contract; §4 `run_artifacts` + artifact APIs; §6 post-HITL test-loop; testing/sources/assumptions/open questions  
- **Prompt Trace:** omitted (Define-phase doc update; no vendor execution; no `.env` values read).  
- **Model / temperature / max_tokens:** Cursor Grok 4.6 interactive session; temperature/max_tokens not independently set by this persona (IDE-controlled).  
- **Write method:** in-place section updates to `sad.md` (template headings preserved). Sequence `.mmd` updated; PNG re-render skipped (`mmdc` missing chrome-headless-shell).  
- **Prohibited actions honored:** no application code in this persona step; no new product requirements beyond PRD + recorded operator constraints; HITL not removed from Jamf writes; secrets as env **names** only; Policy 1460 mapped to MCP not shell.  
- **Self-check (required template headings):** Context & Instructions; Input Requirements; §1–§10; Implementation Guidance; Architecture Validation Checklist; Sources; Assumptions; Open Questions; Audit.  
