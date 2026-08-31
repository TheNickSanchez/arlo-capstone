# Market Research Document: ARLO (Automated Remediation Loop Orchestrator)

**Document type:** AAMAD Deep Research / Market Research Document (MRD)  
**Product:** ARLO — Automated Remediation Loop Orchestrator  
**Phase:** 1 Define  
**Owner persona:** `@product-mgr` (`product-mgr`)  
**Date:** 2026-08-31

## Context & Instructions

This MRD evaluates the commercial and operational case for a production-ready multi-agent system that orchestrates concurrent, human-gated vulnerability remediations from Jira tickets. Findings are evidence-based. The selected runtime (`AAMAD_TARGET_RUNTIME`) is an implementation choice for the generated MVP, not the AAMAD methodology itself. Operator selection (2026-08-31): **`claude-agent-sdk`**, recorded in `aamad.config.yml` (`runtime.target`). Env `AAMAD_TARGET_RUNTIME` still preferred when set; keep it aligned with config so later personas do not inherit the adapter-registry `crewai` default.

Stakeholder-provided domain inputs (not independently invented):

- **Problem:** Application Security and DevOps teams face hundreds of Jira vulnerability remediation tickets. Manual remediations are slow; fully autonomous AI patching is too risky for production code without human guardrails. Single-agent scripts cannot handle multiple concurrent tickets efficiently.
- **Users:** DevSecOps Engineers, Security Analysts, Engineering Managers checking progress across dozens of active remediations.
- **Limitations of alternatives:** Pure static scanners (no automated fix), simple scripts without state tracking, or single-agent runtimes that block on human input and lack concurrent-run visibility.
- **Differentiators:** Dynamic agent spawning (one blueprint, infinite running instances named like `ARLO-675`), mandatory Human-in-the-Loop (HITL) approval gates **before code modification**, and a unified execution dashboard with decision history.

## Research Query Structure

**Primary Focus:** Multi-agent vulnerability remediation orchestrator for DevSecOps teams that spawn concurrent, ticket-bound agent instances from Jira work items, enforce architectural HITL before any code write, and expose a unified dashboard of run state and decision history.

**Example (template analog):** "Customer Support AI Agent System for SaaS companies" → this research analog is "HITL multi-agent AppSec remediation orchestrator for Jira-centric DevSecOps teams."

**Selected Runtime** (optional for research; required later in Build): **`claude-agent-sdk`** (operator-confirmed 2026-08-31; `aamad.config.yml` `runtime.target`). Candidate fit ranking that led to this choice: `cursor-sdk` ≈ `claude-agent-sdk` > `crewai`. Runtime remains an implementation choice, not the product definition. Align SAD/backend with `.cursor/rules/adapter-claude-agent-sdk.mdc` (`AgentDefinition`, `ClaudeSDKClient`, `PreToolUse`/`PostToolUse` HITL hooks, least-privilege `allowed_tools`, subagent isolation).

---

## Executive Summary

**Market Opportunity.** Vulnerability exploitation is now the leading initial-access vector in the Verizon 2026 Data Breach Investigations Report (DBIR), accounting for 31% of breaches (up from 20% the prior year) across ~31,000 incidents and ~22,000 confirmed breaches. Only 26% of CISA Known Exploited Vulnerabilities (KEV) were fully remediated in 2025, down from 38%, while median time-to-full-resolution rose from 32 to 43 days. Veracode’s 2026 State of Software Security (SoSS) reports security debt (findings older than one year) at 82% of organizations (up from 74% in 2025 and 71% in 2024), with critical security debt at 60%. The application-security market is large but estimates conflict ($14.6B–$26.9B for 2025 depending on firm); the closer adjacent TAM is Application Security Posture Management (ASPM) at USD 686.8 million in 2025, projected to USD 2.28 billion by 2030 (27.2% CAGR). DevSecOps platforms sit in a ~USD 9–11 billion 2026 band with ~13–22% CAGR. ARLO does not compete as another scanner. It addresses the **fix-capacity gap**: detection has outrun remediation, Jira backlogs routinely reach hundreds to ~1,000 tickets, and AI coding agents are entering the loop without concurrent-run governance.

**Technical Feasibility.** AI-assisted remediation is already shipping (GitHub Copilot Autofix, Snyk Agent Fix, Semgrep Autofix, Veracode Fix, Pixee, Atlassian Jira Coding Agent). Those products prove that LLM-generated patches can reduce cycle time (GitHub: 28 minutes vs 1.5 hours median on PR-time alerts; Atlassian: 11.9 → 6 days and ~51–52% of merged vuln issues agent-assisted). They do **not** prove that fully autonomous writes to production-bound code are safe. A 2025 SWE-bench study found standalone LLM patches introduced 185 new vulnerabilities versus 20 from developers across 20,000+ GitHub issues (~9×). OWASP LLM Top 10 (LLM06:2025 / LLM03:2026 Excessive Agency) and EU AI Act Article 14 both require human oversight that cannot be prompt-only. ARLO’s architecture — one blueprint, many named instances, pre-write HITL, and a decision-history dashboard — is therefore the feasible path: automate investigation and proposal at concurrency, gate mutation, and make every decision auditable. Implementation complexity is medium-high (Jira + SCM + scanner context + durable run state + least-privilege tools), with high success probability for an MVP that proposes diffs/PRs and never writes until approved.

**Recommended Approach.** Position ARLO as a **scanner-agnostic, Jira-native remediation control plane**, not as SAST/SCA. MVP scope: ingest Jira vuln tickets; spawn a named agent instance per ticket (`ARLO-<key>`); run investigation and proposed-fix generation concurrently; block all code-modifying tools until a human approves; persist decision history on a unified dashboard. Do not auto-merge. Do not claim novelty merely for “AI writes a patch” (crowded product and patent landscape). Differentiate on concurrent instance orchestration, architectural HITL, and manager-grade observability. Runtime lock: **`claude-agent-sdk`** — coordinator plus specialized `AgentDefinition` subagents, `PreToolUse` as the architectural HITL PEP for write tools, explicit turn/token budgets per instance, traces under `project-context/2.build/logs`. Required secret **names** for Build: `ANTHROPIC_API_KEY` (and optional org gateway/base URL); never commit values.

---

## Detailed Findings by Dimension

### 1. Market Analysis & Opportunity Assessment

#### Key Insights

1. **The bottleneck moved from find to fix.** Verizon 2026 DBIR: exploitation is the #1 breach vector at 31% (+55% relative vs 20% prior year); KEV full-remediation rate fell 38% → 26%; median full resolution 32 → 43 days; organizations had 50% more critical vulns to patch (median). Edgescan 2026: average MTTR for high/critical **application and API** flaws in 2025 was **54.81 days** (range <1 to 267 days). Qualys 2026 Enterprise Patch & Remediation Benchmark: complex enterprise apps (Java, .NET, Citrix) average **5 months 10 days** MTTR. Veracode 2026 SoSS: 82% of orgs carry year-plus security debt; critical debt 60%; high-risk flaws +36% YoY; industry average critical-fix half-life cited at **243 days**, with a recommended target of <90 days (30 days in some regulated industries).

2. **Ticket volume is an operations problem, not a scanner problem.** Atlassian reports ~1,000 SCA-driven issues per month internally, 30–60 minutes of developer time each, median 11.9 days to resolve before agent assistance. Persistent describes a US comms provider with ~1,000 Jira vulnerability tickets, many stale, and ~10 minutes per ticket just to create records. ArmorCode cites traditional MTTR of ~240 days when triage and routing stay manual. Stakeholder input that teams “face hundreds of tickets” is consistent with published mid-market/enterprise operating reality.

3. **AI is widening both the attack and the assist surface.** FIRST/Atlassian guidance for 2026: CVE disclosures expected to exceed 50,000 and may approach six figures. NIST (April 2026) enriched ~42,000 CVEs in 2025 (+45% vs any prior year) and still could not keep up; NVD moved to risk-based enrichment (KEV, federal software, EO 14028 critical software), leaving a large share of CVEs unenriched. IBM 2025 Cost of a Data Breach: global average **USD 4.44 million**; extensive AI/automation in security operations associated with **USD 1.9 million** lower breach cost and ~80 fewer lifecycle days. Shadow AI added ~USD 670,000 to average breach cost — a warning that ungoverened agents create new loss, not just savings.

4. **Willingness to pay sits in DevSecOps/ASPM budgets, not in net-new “agent runtime” line items.** ASPM (Frost & Sullivan via GII, 2025 base): USD 686.8M → USD 2.28B by 2030, 27.2% CAGR, driven by tool sprawl, alert fatigue, and DevSecOps/CNAPP consolidation. DevSecOps: Mordor USD 10.88B (2026) → USD 29.52B (2031), 22.1% CAGR; Grand View USD 8.84B (2024) → USD 20.24B (2030), 13.2% CAGR. Buyers already pay Snyk, GitHub Advanced Security, Checkmarx, Veracode, Semgrep, and Jira Cloud. ARLO’s commercial wedge is **orchestration + HITL + concurrency visibility** on top of those sunk costs.

5. **Competitive white space is concurrency + governance, not “AI can suggest a fix.”** Direct competitors (Copilot Autofix, Snyk Agent Fix, Semgrep Autofix, Veracode Fix, Pixee, SonarQube AI CodeFix, Jira Coding Agent) are mostly scanner-tied and/or SCM-tied, and they optimize for a single finding → one PR. Indirect competitors are scanners with Jira tickets and no fix loop, or a developer running one Cursor/Claude session that blocks the operator. No widely documented incumbent offers: (a) one blueprint infinitely instantiated per Jira key, (b) **mandatory pre-write** HITL (not merely pre-merge), and (c) a portfolio dashboard of concurrent runs and decision history for engineering managers.

#### Data Points

| Metric | Value | Year / as-of | Source |
|---|---|---|---|
| Breach share from vuln exploitation | 31% (was 20%) | 2026 DBIR (2025 data) | Verizon |
| Confirmed breaches in DBIR dataset | ~22,000 (incidents ~31,000) | 2026 DBIR | Verizon / SecurityWeek |
| KEV fully remediated | 26% (was 38%) | 2025 | Verizon 2026 DBIR |
| Median KEV full resolution | 43 days (was 32) | 2025 | Verizon 2026 DBIR |
| App/API high-critical MTTR | 54.81 days | 2025 | Edgescan 2026 |
| Complex-app MTTR | 5 months 10 days | 2025/26 benchmark | Qualys |
| Security debt prevalence | 71% → 74% → 82% | 2024–2026 | Veracode SoSS |
| Critical security debt | 46% → 50% → 60% | 2024–2026 | Veracode SoSS |
| Recommended vs actual critical half-life | <90 days vs 243 days avg | 2026 SoSS | Veracode |
| AppSec market (conflicting) | USD 14.56B / 16.52B / 26.9B (2025); MnM USD 41.16B (2026) | 2025–2026 | MRFR, Research and Markets, Market.us, MarketsandMarkets |
| ASPM TAM | USD 686.8M (2025) → USD 2.28B (2030), 27.2% CAGR | 2025–2030 | Frost & Sullivan / GII |
| DevSecOps TAM | ~USD 8.9–10.9B (2025/26); 13–22% CAGR bands | 2025–2031 | Mordor, Grand View, TBRC |
| Global avg breach cost | USD 4.44M (US USD 10.22M) | 2025 | IBM |
| AI/automation security-ops savings | USD 1.9M; ~80 days shorter lifecycle | 2025 | IBM |
| Atlassian SCA inflow | ~1,000 issues/month; 30–60 min each; 11.9 day median | ~2025–2026 | Atlassian whitepaper |
| Atlassian agent outcome | 51–52% merged vulns agent-assisted; cycle time ~50% (11.9→6 days) | 2026 | Atlassian |
| GitHub Autofix (PR-time) | 28 min vs 1.5 h median (3×); XSS 7×; SQLi 12× | May–Jul 2024 beta | GitHub Blog |
| Snyk Agent Fix (vendor bench) | Opus 4.6 + Snyk Intelligence 85.4% secure-and-functional (~150 samples) | 2026 | Snyk |
| Pixee claimed production merge rate | 76% | 2024–2025 | Pixee |
| NIST NVD 2025 enrichment | ~42,000 CVEs (+45%); 263% CVE submission growth 2020–2025 | 2026-04 | NIST |
| LLM new-vuln rate vs humans | 185 vs 20 new vulns (20k+ issues) | 2025 preprint | arXiv 2507.02976 |

**Conflicting information.** AppSec market-size figures differ by ~2–3× across firms (definitions mix testing tools, WAF/RASP, services, and platforms). Treat **order of magnitude (tens of billions)** as robust and **specific dollar TAM** as non-authoritative. Use ASPM + DevSecOps as the planning envelope for ARLO. Vendor autofix success rates (Snyk 85.4%, Pixee 76%) are not comparable: different corpora, languages, and “success” definitions (secure-and-functional on a lab set vs production merge). GitHub’s 28-minute figure is PR-time alerts in GHAS, not backlog Jira tickets — do not use it as ARLO’s expected MTTR.

#### Source Citations

Verizon 2026 DBIR; Veracode 2026 SoSS; Edgescan 2026 Vulnerability Statistics Report; Qualys 2026 Enterprise Patch & Remediation Benchmark; IBM Cost of a Data Breach 2025; Frost & Sullivan ASPM 2025–2030 (GII); Mordor / Grand View / TBRC DevSecOps reports; MarketsandMarkets / Research and Markets / Market.us / MRFR AppSec reports; NIST NVD operations update (2026-04); Atlassian AI-powered vulnerability resolution whitepaper; GitHub Copilot Autofix GA blog (2024-08); Snyk Agent Fix benchmark (2026); Pixee Veracode-alternatives analysis; arXiv:2507.02976.

#### Implications

- **Design:** Optimize for backlog drain and concurrent in-flight work, not for “one chat session.” Ticket-keyed instance names (`ARLO-675`) should be first-class IDs in UI, logs, and Jira comments.
- **Business:** Sell (or justify internally) against **hours reclaimed + SLA/KEV compliance + reduced window of exposure**, using IBM and Verizon as executive language. Do not lead with “we are an LLM.”
- **MVP scope:** Jira as system of record; do not rebuild scanning. Partner/integrate with existing SAST/SCA output already on the ticket.
- **Capstone vs commercial:** Even if ARLO remains a capstone/internal tool, the same metrics (MTTR, % HITL-approved vs rejected, concurrent runs, decision-audit completeness) are the success contract for PRD.

---

### 2. Technical Feasibility & Requirements Analysis

#### Key Insights

1. **Multi-agent is justified; a single blocking agent is not.** Stakeholder constraint: hundreds of tickets and dozens of simultaneous remediations. Sequential single-agent loops serialize HITL and hide sibling progress. Industry patterns that match: isolated subagents with their own context/tool permissions (Claude Agent SDK); concurrent coding-agent invocations from Jira Automation (Atlassian, 2026: Copilot, Cursor, and Claude as first-class actions); CrewAI hierarchical/async crews for role graphs. ARLO’s “one blueprint, N instances” is a **fan-out of identical specialists**, not a researcher-writer-reviewer sequential crew.

2. **Runtime adapter fit** (operator selected **`claude-agent-sdk`**).

| Adapter | Fit to ARLO differentiators | Risks |
|---|---|---|
| `cursor-sdk` (not selected) | Strong for coding-agent instances, TypeScript contracts, Cursor-native repo edits, and Jira→Cursor automation already shipping at Atlassian | Node/TS stack vs config `language.primary: python`; IDE-cloud coupling; cost/session limits |
| **`claude-agent-sdk` (selected)** | Strong for PreToolUse/PostToolUse hooks (architectural HITL), subagent isolation, MCP, session resume/fork, turn budgets | Anthropic-centric; must still build dashboard and Jira orchestration outside the SDK |
| `crewai` (not selected) | Strong for declarative YAML agents/tasks and sequential/hierarchical process; fast to scaffold | Weaker native story for “infinite named instances” and per-instance HITL interrupt; sequential process fights concurrency unless explicitly designed with `kickoff_for_each` and documented merge keys |

3. **Integration surface for MVP is bounded.** Required: Jira Cloud REST (issue get/search/comment/transition); git host (GitHub/GitLab/Bitbucket) for branch + draft PR; optional scanner metadata already on the ticket (Snyk, CodeQL, Semgrep, etc.). Do not require a new scanner. Persist run state (instance id, ticket key, phase, pending approval, decision log) in a local/project store for the MVP — no multi-tenant SaaS in capstone scope unless PRD later expands.

4. **Technical risks are dominated by unsafe tool use and non-durable HITL.** OWASP Excessive Agency: least-privilege tools, complete mediation **outside** the model, user approval for high-impact actions. SWE-bench evidence: more files / more generated lines / weaker issue context → more introduced vulns. Mitigation: read-only tools until approval; write tools disabled by policy engine; max files/lines thresholds; require ticket reproduction context before proposal. Durability: if the operator closes the session, the pending gate and decision history must survive (checkpoint / session id).

5. **Infrastructure for MVP is laptop/cloud-agent plus API keys, not a cluster.** Cost drivers: LLM tokens × concurrent instances × retries. Controls: per-instance turn/token budgets, max concurrent runs, retry idempotency. Production later: queue, webhooks from Jira, secrets manager, audit log sink. NIST SSDF (SP 800-218) and SP 800-218A (AI profile) map to logging, vulnerability response, and autonomy-boundary threat modeling — relevant even for a capstone if the system can write code.

#### Data Points

- Claude Agent SDK: hooks at tool-call boundaries; subagents with isolated context, tools, and model (2026 framework comparisons).
- CrewAI 1.14.x (mid-2026): role/goal/backstory, sequential and hierarchical process, Flow DSL, pluggable memory; production score typically below LangGraph for HITL/checkpointing.
- Atlassian Jira Coding Agent in automations: creates a **draft PR**, does not merge; restricted mode; jobId/repoUrl smart values — a reference interaction contract.
- LLM introduced 9× more new vulnerabilities than developers on SWE-bench-scale issues; agentic frameworks also introduced vulns, worst when autonomy was highest (arXiv:2507.02976).
- Snyk: security-context injection (35,000+ expert fixes) lifted Opus 4.6 from 74.6% → 85.4% on their ~150-sample bench — evidence that **grounding in finding metadata** matters as much as model choice.

#### Source Citations

AAMAD adapter registry (crewai / claude-agent-sdk / cursor-sdk); AgentsCamp / Appinventiv / Alice Labs 2026 framework comparisons; Atlassian Jira Coding Agent automation docs; OWASP LLM Top 10 2025 PDF; NIST SP 800-218 / 218A mappings; arXiv:2507.02976; Snyk Agent Fix benchmark; Cordum HITL production patterns (2026).

#### Implications

- PRD must require a **policy engine outside the LLM** that refuses write/PR tools until an approval record exists for that instance.
- SAD should treat each `ARLO-<ticket>` as an isolated runtime session with its own budget, logs, and HITL queue entry.
- Runtime is locked to **`claude-agent-sdk`**. SAD maps `ARLO-<ticket>` to isolated SDK sessions/subagents with `PreToolUse` denying write tools until HITL clearance; do not generate CrewAI `config/agents.yaml` as the MVP runtime.

---

### 3. User Experience & Workflow Analysis

#### Key Insights

1. **Three personas, three jobs-to-be-done.**

| Persona | Primary job | Pain | UX implication |
|---|---|---|---|
| DevSecOps Engineer | Drain the Jira vuln queue without babysitting one agent | Manual patching; scripts that lose state; one session blocks the rest | Spawn-many, glanceable instance list, resume after approval |
| Security Analyst | Decide whether a proposed change is safe and in policy | Alert fatigue; missing context; fear of rubber-stamping AI | Diff + rationale + scanner/CWE/KEV context + Approve / Reject / Request-changes **before write** |
| Engineering Manager | See progress across dozens of remediations | No portfolio view; unknown who approved what | Dashboard: in-flight, waiting-on-human, succeeded, failed, rejected; decision history exportable |

2. **End-to-end journey (MVP).** Jira ticket created or labeled as vuln → ARLO (or Jira automation) spawns `ARLO-<KEY>` → agent reads ticket + repo context (read-only) → produces investigation summary and proposed patch → **HITL gate** → on approve, agent may write branch / open draft PR and comment on Jira → on reject, log reason, no write → dashboard and Jira reflect state. Humans remain responsible for merge.

3. **Automation vs HITL split.** Automate: triage, duplicate/stale detection, context assembly, patch **proposal**, status comments, evidence packing. Never fully automate: code modification, force-push, merge to default branch, production deploy, secret/credential use beyond declared env. Atlassian’s own agent loops keep engineers validating before merge; ARLO is stricter by gating **before code modification**, which is the stated differentiator and aligns with OWASP “require user approval” for high-impact actions.

4. **Adoption barriers.** Trust (will it silently edit main?); cognitive load if every ticket needs a long review; tool sprawl (another dashboard); AI policy / EU AI Act oversight evidence; token cost at concurrency. Enablers: named instances matching Jira keys; immutable decision log; default-deny writes; time-to-first-proposal measured in minutes; manager view that looks like a sprint board, not a chat dump.

5. **Success metrics (measurable).** Mean time ticket-created → HITL-ready proposal; mean time approval → draft PR; % proposals approved vs rejected vs timed-out; concurrent in-flight instances; HITL bypass attempts blocked (must be zero); decision-log completeness (100% of write attempts have an approval record); no unapproved file writes in QA. Leading industry KPIs to **report against**, not blindly copy: Edgescan 54.81-day MTTR, Verizon 43-day KEV median, Veracode <90-day critical half-life, Atlassian 6-day agent-assisted cycle.

#### Data Points

- GitHub: developers resolved Autofix-supported PR alerts 3× faster (28 min vs 1.5 h) in 2024 beta — shows **proposal-in-PR** UX works when the developer stays in GitHub.
- Atlassian: HITL after draft PR; 50% cycle-time cut; ~52% of merged security vulns agent-assisted.
- Persistent: 50 hours/month reclaimed on ticket hygiene alone; 100 tickets created in <5 minutes vs 3–4 hours.
- Cordum / PwC-McKinsey figures as cited in 2026 HITL pattern writing: high share of firms with agents in production and majority reporting risky autonomous behavior — treat as directional industry narrative, not ARLO-primary evidence.
- EU AI Act Article 14: high-risk systems need interfaces so humans can monitor, interpret, override, and stop the system (HITL / HOTL / HIC taxonomy).

#### Source Citations

Stakeholder problem statement; Atlassian whitepaper + Inside Atlassian agent blogs (2026); GitHub Copilot Autofix blog; Persistent case study; OWASP LLM06:2025; Taylor & Francis EU AI Act human-oversight analysis; Cordum HITL patterns.

#### Implications

- UI is **not** a single chat thread. MVP UI: (1) queue/dashboard of instances, (2) instance detail with timeline + pending approval card + diff, (3) decision history filterable by ticket, actor, outcome.
- Chat-style interaction may exist **inside** an instance for “request changes,” but the manager path must not require opening 40 chats.
- Copy in UI should say “proposal pending approval — no files will be changed until you approve.”

---

### 4. Production & Operations Requirements

#### Key Insights

1. **Deployment for capstone/MVP:** single service or local orchestrator + frontend, aligned with AAMAD smallest-target guidance. Hosting later: container or compose; health check on orchestrator; no live deploy without operator authorization (Deliver-phase rule).

2. **Observability is a product feature, not only ops.** Required telemetry: instance lifecycle (spawn, tool calls, HITL wait, approve/reject, complete, fail, cancel); token/turn usage; latency per phase; error class (Jira auth, git auth, model, policy deny). Persist under a project log path in Build (`project-context/2.build/logs` per adapter rules). Redact secrets from traces.

3. **Security and compliance.** Secrets only in env (`.env.example` names, never values). Least privilege: Jira scope limited to project/issue comment+transition as needed; git token limited to feature branches; no production kube credentials in MVP. OWASP Excessive Agency + complete mediation. NIST SSDF RV (vulnerability response) practices for the **product’s own** code. EU AI Act oversight if ARLO is later classified high-risk (Open Question). CISA BOD 26-04 / FedRAMP VDR timelines (Dec 2026) increase demand for auditable remediation evidence in regulated clouds — a future positioning hook, not MVP scope.

4. **Maintenance.** Blueprint versioning (the one agent definition all instances clone); prompt/tool-policy changes must not rewrite historical decision logs. Pin model/runtime versions in Audit of build artifacts.

5. **Cost structure (order-of-magnitude, not a quote).** Dominant opex: LLM inference × concurrent instances. Atlassian-scale thought experiment: 1,000 SCA issues/month × (investigation + one retry) is the planning load; even a 20% spawn rate (200 runs) can dominate a student/capstone API budget without caps. IBM shows security automation can save USD 1.9M at enterprise breach-cost scale — that ROI is **buyer language**, not ARLO’s P&L.

6. **Business continuity.** If the model provider is down: queue instances, do not skip HITL on retry. If Jira is down: local state remains source of truth for in-flight approvals. Never “fail open” into write tools.

#### Data Points

- IBM 2025: 241-day mean identify+contain (9-year low); AI/automation correlated with faster, cheaper breaches.
- NIST NVD 2026: KEV enrichment target **one business day** — operators will expect remediation tooling to treat KEV tickets as highest priority in the dashboard.
- CISA BOD 26-04 (Jun 2026) + FedRAMP VDR/VER mandatory 2026-12-07 for in-scope CSPs: risk-based (KEV, exposure, automatability), not CVSS-only.
- Qualys TRU: KEV volume 6.5× with worsening Day-7/Day-30 still-open rates — manual remediation has hit a ceiling.

#### Source Citations

IBM 2025 CoDB; NIST NVD 2026-04; CISA BOD 26-04 / FedRAMP notice 0014; Qualys TRU “Broken Physics of Remediation”; AAMAD delivery-workflow and adapter logging rules; OWASP LLM Top 10.

#### Implications

- Dashboard should surface KEV / high-severity SLAs as sort keys.
- Failure policy: halt writes on missing approval, missing tools, or budget overrun; record Diagnostic.
- Capstone cost control: max concurrent instances and max turns are product requirements, not afterthoughts.

---

### 5. Innovation & Differentiation Analysis

#### Key Insights

1. **Unique value proposition (evidence-backed, stakeholder-aligned).** ARLO is a **remediation loop orchestrator**: clone one hardened blueprint into many ticket-named running instances; require architectural HITL before any code modification; show all loops and their decision history in one dashboard. Incumbents automate **a fix**. ARLO automates **the fleet of guarded fix loops**.

2. **Feature gap vs named competitors.**

| Capability | Scanners (SAST/SCA) | Copilot Autofix / Snyk / Semgrep / Veracode Fix | Jira Coding Agent | Single Cursor/Claude chat | **ARLO (target)** |
|---|---|---|---|---|---|
| Find vulns | Yes | Tied to own engine | No (consumes tickets) | No | No (out of MVP scope) |
| Open Jira tickets | Often | Varies | Native | Manual | Consume/update |
| Concurrent instances from one blueprint | N/A | Per-alert jobs, limited fleet UX | Automation rules | No (blocks) | **Yes (`ARLO-675`)** |
| HITL before **code write** | N/A | Often writes suggestion/PR first | Draft PR, human merge | Operator is the loop | **Mandatory gate** |
| Portfolio dashboard + decision history | Scanner dashboards | Alert lists | Jira board (weak agent-ops) | None | **First-class** |
| Scanner-agnostic | No | Mostly no | Yes if ticket exists | Yes | **Yes** |

3. **Emerging tech to adopt, not reinvent.** MCP for Jira/git; subagent isolation; tool hooks as policy PEP; SARIF-on-ticket if present; KEV/EPSS as sort signals (read-only). Do not build a foundation model.

4. **Patent / IP landscape (non-legal, indicative).** Recent USPTO-class disclosures cover: tokenized historical remediations with user approval (US 12,536,298); autonomous AI bots executing host remediation scripts (US 12,694,124); generative models proposing patch strategies (US 12,664,288); LLM-generated remediation action descriptions from NVD/vendor pages (US 12,670,263); generative remediator initiating cloud remediation actions (US 12,095,786). **Freedom-to-operate is an Open Question.** Practical implication: do not market “we invented AI patching.” Market orchestration, naming/isolation of instances, pre-write mediation, and audit UX. No patent filings are recommended for a capstone without counsel.

5. **Future trends.** CVE volume and unenriched NVD records push teams toward KEV-first and ticket-context-first workflows. Agentic coding (Gartner: 40% of enterprise apps with task-specific agents by end of period cited in 2026 roundups) will make **ungoverned concurrent agents** a management problem — ARLO’s dashboard is the counterweight. Partnerships: Atlassian (Jira/Automation/Rovo), SCM hosts, and scanner vendors via ticket fields/SARIF — not exclusive lock-in.

6. **Monetization (if productized post-capstone).** Seat + consumption (per instance-run) aligns with Copilot credits / Semgrep AI credits. Enterprise: SAML, audit export, max-concurrency packs. Capstone: N/A commercially; still define a **value metric** (hours saved, MTTR delta, approval latency) for the PRD.

#### Data Points

- Gartner recognized ASPM as a category in 2023; AST Magic Quadrant (Oct 2025) now treats AI-assisted remediation as vision criteria — ARLO is adjacent, not an AST vendor.
- Semgrep Autofix public beta 2026: PRs with first-party fixes + upgrade guidance; +95% agreement cited on AI triage (vendor figure).
- Veracode Fix historically bound to Veracode findings; Fix for SCA early access Mar 2026 (Pixee competitive analysis) — multi-scanner gap remains.
- Agentic AI market 2026 estimates ~USD 9–19B depending on methodology (wide disagreement; cite as range only).

#### Source Citations

Stakeholder differentiators; Corgea auto-remediation 2026 comparison; Pixee Veracode alternatives; Semgrep Autofix 2026 blog; Gartner AST MQ coverage (vendor republication 2025-10); USPTO patent titles listed above (indicative); Simpliaxis 2026 agent market roundup; Arnica ASPM CISO guide (Gartner ASPM 2023).

#### Implications

- PRD language: “orchestrator with HITL and observability,” never “autonomous patcher.”
- Competitive bake-off for QA: same Jira fixture vs a single-agent baseline (time-to-N-proposals, HITL bypass tests, dashboard completeness).

---

## Critical Decision Points

### Go/No-Go Factors

**Go if all of the following hold:**

1. Jira remains the system of record for vuln work (stakeholder-confirmed).
2. HITL is **architecturally enforced** before any code-modifying tool (non-negotiable).
3. MVP can demonstrate **≥2 concurrent** named instances without shared mutable session state.
4. Decision history is complete for every approval, rejection, and policy deny.
5. No requirement in MVP to replace Snyk/CodeQL/Semgrep as a scanner.

**No-go / halt if:** operator requires fully autonomous writes to default branches; Jira is not available; secrets would need to be embedded in artifacts; or success is defined only as “AI merged to main without review.”

### Technical Architecture Choices

- **Orchestration:** blueprint → N isolated instances keyed by Jira issue key.
- **Policy:** pre-execution gate on write/PR/push tools; read tools allowed in investigate phase.
- **Runtime:** **`claude-agent-sdk`** (operator-locked). SAD/backend must use coordinator + `AgentDefinition` specialists, `PreToolUse`/`PostToolUse` for HITL and audit, isolated subagents (or equivalent session-per-ticket) for `ARLO-<key>` instances, least-privilege `allowed_tools`, and explicit turn/token budgets. Do not scaffold CrewAI YAML as the MVP runtime.
- **Output of an approved run:** branch + draft PR + Jira comment; merge remains human.
- **State:** durable instance record (status, timestamps, actor, rationale, artifact links).

### Market Positioning

- **Category:** HITL multi-agent remediation orchestration (ASPM-adjacent), not AST.
- **Beachhead:** DevSecOps teams already drowning in Jira vuln tickets (hundreds to ~1,000), with scanners in place.
- **Message:** “Drain the queue without unsupervised patches. One blueprint. Many guarded loops. Full decision history.”
- **Anti-message:** “Fully autonomous production patching.”

### Resource Requirements

- **Capstone team (AAMAD):** Define (`@product-mgr` → `@system.arch`) then Build (PM, FE, BE, integration, QA, security) then Deliver. HITL and dashboard are frontend+backend+integration, not a backend-only crew.
- **Timeline implication:** Module-style build (config → API → UI → e2e) matches AAMAD development-workflow; concurrent-run tests belong in QA, not as an afterthought.
- **Budget:** LLM spend proportional to max concurrency; set a hard cap in PRD NFRs. Enterprise ROI narrative can cite IBM USD 1.9M automation savings and Atlassian thousands of hours — not as ARLO’s own audited result.

---

## Risk Assessment Matrix

### High Risk

| Risk | Why it matters | Mitigation |
|---|---|---|
| Ungoverned writes / HITL bypass | SWE-bench 9× new vulns; OWASP Excessive Agency; stakeholder explicit ban on unsupervised production edits | Policy engine outside model; write tools absent until approval token; QA must attempt bypass |
| Introduced vulnerabilities in “fixes” | Same study; vendor benches are not production | Human review of diff; optional re-scan comment; never auto-merge |
| Secret leakage in traces/PRs | Adapter rules forbid secrets in artifacts | `.env.example` only; redact Prompt Trace; no tokens in Jira comments |
| Concurrent-state corruption | Core differentiator fails if instances share memory/files unsafely | Isolated worktrees/branches per issue key; no shared writable workspace |

### Medium Risk

| Risk | Why it matters | Mitigation |
|---|---|---|
| Runtime mismatch (`crewai` default vs fan-out need) | Unset env could still override or confuse later personas | Config locked to `claude-agent-sdk`; set `AAMAD_TARGET_RUNTIME=claude-agent-sdk` in Build/CI |
| HITL becomes the new bottleneck | 1,000 tickets × slow reviewers | Batch dashboard; SLA timers; do not silently auto-approve to “help” |
| Scanner-specific assumptions | Veracode-style lock-in is a competitor weakness we should not copy | Ticket-text + attached metadata only in MVP |
| Cost overrun at concurrency | Token × N instances | Max concurrent runs, max turns, kill switch |
| Patent/FTO | Crowded generative-remediation claims | Capstone: no IP assertions; commercial: counsel |
| Market-size conflict | Over-claiming TAM | Use ASPM/DevSecOps bands; avoid a single AppSec $ figure |

### Low Risk

| Risk | Why it matters | Mitigation |
|---|---|---|
| Dashboard visual polish | Manager persona still needs a list/filter MVP | Minimal UI per example config; defer theming |
| Chat-only users expecting Copilot-in-IDE | Different job-to-be-done | Position as control plane; IDE remains optional |
| CVE/NVD metadata gaps | Unenriched CVEs | Rely on ticket body + KEV flag if present; do not require NVD completeness |

---

## Actionable Recommendations

### Immediate Next Steps (within 48 hours)

1. Stakeholder confirm: Jira Cloud vs Server/DC; git host; whether HITL is pre-write (this MRD) or pre-merge (Atlassian-like). Default for PRD: **pre-write**, per supplied differentiator.
2. Runtime is set: `aamad.config.yml` `runtime.target: claude-agent-sdk`. Optionally export `AAMAD_TARGET_RUNTIME=claude-agent-sdk` in the operator shell/CI so env wins over any stale default.
3. `@product-mgr` `*create-prd` from this MRD (and `*elicit-requirements` if system-description is still missing).
4. Keep `language.primary: python` unless the operator later chooses TypeScript for the Claude Agent SDK.

### Short-term Priorities (next 30 days)

1. PRD + user stories for: spawn instance, HITL gate, dashboard, Jira comment loop, draft PR after approval.
2. SAD: instance isolation, policy PEP, data stores, adapter-conditional runtime.
3. NFR: max concurrency, turn/token budgets, “zero unapproved writes” as a QA gate.
4. Competitive test fixtures: 3 parallel Jira keys (`ARLO-675` analog) for QA.

### Long-term Strategy (6–12 months)

1. KEV-first prioritization and SLA badges on the dashboard.
2. Scanner-agnostic SARIF/ticket enrichment; optional post-fix re-scan webhook.
3. Graduated autonomy **only** for classes with proven low-risk (e.g. lockfile bump) and still logged — never as MVP.
4. If productized: consumption pricing, audit export for BOD 26-04 / SSDF evidence, partnership with Jira Automation (Cursor/Claude/Copilot already on that bus).

---

## Sources

1. Verizon, *2026 Data Breach Investigations Report* (2025 data; exploitation 31%; KEV remediation 26%; median 43 days). https://www.verizon.com/business/resources/reports/dbir/  
2. Verizon News, “Vulnerability exploitation top breach entry point, 2026 industry-wide DBIR finds.” https://www.verizon.com/about/news/breach-industry-wide-dbir-finds  
3. SecurityWeek, “Verizon DBIR 2026: Vulnerability Exploitation Overtakes Credential Theft” (31% of ~22,000 breaches; ~31,000 incidents). https://www.securityweek.com/verizon-dbir-2026-vulnerability-exploitation-overtakes-credential-theft-as-top-breach-vector/  
4. Tenable, “Key takeaways from the Verizon DBIR (2026).” https://www.tenable.com/blog/key-findings-from-the-verizon-dbir-2026  
5. Veracode, *2026 State of Software Security Report* (82% / 60% debt; 243-day half-life context). https://www.veracode.com/wp-content/uploads/2026-State-of-Software-Security-Report.pdf  
6. Veracode Blog, “The Security Debt Crisis” (71%→74%→82%). https://www.veracode.com/blog/security-debt-crisis/  
7. Veracode Blog, “Erasing Security Debt with an App Risk Remediation Platform” (<90 vs 243 days). https://www.veracode.com/blog/app-risk-remediation-platform-security-debt/  
8. Edgescan, *2026 Vulnerability Statistics Report* (54.81-day app/API MTTR). https://www.edgescan.com/what-the-2026-vulnerability-statistics-report-tells-us-about-the-state-of-security/  
9. Qualys, “Enterprise Patch & Remediation Benchmark 2026” (5 months 10 days). https://blog.qualys.com/qualys-insights/2026/04/20/enterprise-patch-remediation-benchmark-2026  
10. Qualys TRU, *The Broken Physics of Remediation* (KEV volume 6.5×; AWE vs MTTR). https://assets.qualys.com/m/4fa63b802726a2c8/original/Qualys-TRU-The-Broken-Physics-of-Remediation.pdf  
11. IBM, *Cost of a Data Breach Report 2025* (USD 4.44M; USD 1.9M AI/automation savings; 241-day lifecycle). https://www.ibm.com/think/x-force/2025-cost-of-a-data-breach-navigating-ai  
12. Help Net Security, IBM 2025 summary (US USD 10.22M). https://www.helpnetsecurity.com/2025/08/04/ibm-cost-data-breach-report-2025/  
13. Frost & Sullivan via GII, *ASPM Market, Global, 2025–2030* (USD 686.8M → 2,284.5M, 27.2% CAGR). https://www.giiresearch.com/report/fs1909957-application-security-posture-management-aspm.html  
14. Mordor Intelligence, DevSecOps market (USD 10.88B 2026 → 29.52B 2031, 22.10% CAGR). https://www.mordorintelligence.com/industry-reports/devsecops-market  
15. Grand View Research, DevSecOps (USD 8,841.8M 2024 → 20,243.9M 2030, 13.2% CAGR). https://www.grandviewresearch.com/industry-analysis/development-security-operation-market-report  
16. The Business Research Company, DevSecOps 2026–2030 (USD 9.06B 2025; 23.6% CAGR to USD 27.12B 2030). https://www.thebusinessresearchcompany.com/report/devsecops-global-market-report  
17. MarketsandMarkets, Application Security (USD 41.16B 2026 → 66.03B 2031, 9.9% CAGR), PR 2026-03-13. https://www.prnewswire.com/news-releases/application-security-market-worth-66-03-billion-by-2031--marketsandmarkets-302713211.html  
18. Research and Markets, Application Security Market Report 2026 (USD 16.52B 2025 → 20.75B 2026, 25.6% CAGR). https://www.researchandmarkets.com/reports/5767263/application-security-market-report  
19. Market.us, Application Security (USD 26.9B 2025; 10.4% CAGR; vuln mgmt 33.8% share). https://market.us/report/application-security-market/  
20. Market Research Future, Application Security (USD 14.56B 2025 figure in report summary). https://www.marketresearchfuture.com/reports/application-security-market-3624  
21. NIST, “NIST Updates NVD Operations to Address Record CVE Growth,” 2026-04 (~42,000 enriched in 2025; KEV 1-business-day goal). https://www.nist.gov/news-events/news/2026/04/nist-updates-nvd-operations-address-record-cve-growth  
22. Cloud Security Alliance research note on NVD risk-based triage (263% CVE growth 2020–2025; ~29,000 Not Scheduled). https://labs.cloudsecurityalliance.org/research/csa-research-note-nist-nvd-enrichment-overhaul-20260429-csa/  
23. Atlassian, *Engineering leader’s guide to AI-powered vulnerability resolution* (~1,000 SCA/month; 52% agent-assisted; 11.9→6 days). https://www.atlassian.com/whitepapers/ai-vulnerability-resolution  
24. Atlassian, “From prompts to orchestration: Scale AI coding agent impact with Jira Automation” (Copilot, Cursor, Claude). https://www.atlassian.com/blog/development/scale-agent-impact-with-jira-automation  
25. Atlassian Support, “Work with Jira Coding Agent in automations” (draft PR, no direct merge). https://support.atlassian.com/jira-software-cloud/docs/work-with-jira-coding-agent-in-automations/  
26. GitHub Blog, “Found means fixed: Secure code more than three times faster with Copilot Autofix” (28 min vs 1.5 h; May–Jul 2024 beta). https://github.blog/news-insights/product-news/secure-code-more-than-three-times-faster-with-copilot-autofix/  
27. Snyk, Agent Fix remediation benchmark (85.4% with Snyk Intelligence, ~150 samples, 2026). https://snyk.io/blog/snyk-agent-fix-remediation-benchmark/  
28. Semgrep, “Accelerate and Automate Remediation with Semgrep Autofix” (public beta, 2026). https://semgrep.dev/blog/2026/semgrep-autofix-public-beta/  
29. Pixee, “9 Veracode Alternatives, Scored on the Fix Gap They Leave” (76% merge rate claim; scanner-agnostic gap). https://www.pixee.ai/blog/veracode-alternatives  
30. Corgea, “Best Automated Remediation and AI Code Review Tools in 2026.” https://corgea.com/learn/auto-remediation-tools  
31. Hossain, T. et al., “Are AI-Generated Fixes Secure? Analyzing LLM and Agent Patches on SWE-bench,” arXiv:2507.02976, 2025. https://arxiv.org/abs/2507.02976  
32. OWASP, *Top 10 for Large Language Model Applications 2025* (LLM06 Excessive Agency; HITL). https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf  
33. OWASP LLM06:2025 Excessive Agency. https://owasp.org/www-project-top-10-for-large-language-model-applications/2_0_vulns/LLM06_ExcessiveAgency  
34. Ebers, M., “‘Human oversight’ in the EU Artificial Intelligence Act,” *Law, Innovation and Technology* (HITL/HOTL/HIC; Article 14). https://www.tandfonline.com/doi/full/10.1080/17579961.2023.2245683  
35. FedRAMP, Response to CISA BOD 26-04 (VDR/VER dates 2026-12-07). https://www.fedramp.gov/notices/0014/  
36. Persistent, vulnerability-management automation case (~1,000 Jira tickets; 50 hours/month). https://www.persistent.com/client-success/persistent-reclaims-50-hours-monthly-and-lifts-sla-by-30-for-us-comms-provider/  
37. ArmorCode, application security remediation workflow (240-day traditional MTTR narrative). https://www.armorcode.com/blog/application-security-vulnerabilities-testing-remediation  
38. USPTO-class patents (indicative, not FTO): US 12,536,298; US 12,694,124; US 12,664,288; US 12,670,263; US 12,095,786 (generative/automated vulnerability remediation families).  
39. AAMAD v0.7.5: `AGENTS.md`, `.cursor/templates/mrd-template.md`, `.cursor/rules/adapter-registry.mdc`, `.cursor/agents/product-mgr.md`, `aamad.config.example.yml`.  
40. Stakeholder inputs in the `*create-mrd` request (problem, users, limitations, differentiators) — primary product-context source.

## Assumptions

- ARLO is researched as a **market-facing product concept** because the operator requested an MRD; it may still be delivered as a capstone/internal MVP. Commercial pricing is therefore directional, not a go-to-market commitment.
- HITL means **approval before code modification**, not only before merge, matching stakeholder wording. If stakeholders later choose Atlassian-style draft-PR-then-review, PRD must revise this assumption.
- Jira is Cloud-class REST-integrable; git is a hosted SCM that supports branches and draft/unpublished PRs.
- ARLO will not perform original SAST/SCA in MVP; tickets already carry enough text/metadata to start investigation.
- `aamad.config.yml` is present: `runtime.target: claude-agent-sdk`, `language.primary: python`, `libraries.approved` includes `claude-agent-sdk`, `security.require_security_assessment: true`.
- Operator resolved runtime to Claude Agent SDK; HITL implementation is expected via SDK hooks (`PreToolUse`) plus a policy engine outside the model — hooks alone are not a substitute if the model can ignore a prompt, but they are the adapter-native enforcement point.
- Market-size figures are vendor/analyst estimates with conflicting methodologies; ASPM + DevSecOps used as planning envelope.
- GitHub Autofix 2024 beta metrics are older than the 18-month preference window as of 2026-08-31; retained because they remain GitHub’s canonical published speed claim and are cross-checked against 2026 Atlassian/Snyk/Semgrep data.
- Vendor success rates (Snyk, Pixee, Semgrep triage agreement) are marketing/bench figures, not independent audits.
- Patent list is a landscape signal only; not legal advice and not exhaustive.
- AAMAD runtime adapters constrain Phase 2 implementation, not the product category.

## Open Questions

1. ~~Confirm `AAMAD_TARGET_RUNTIME`~~ **Resolved 2026-08-31:** `claude-agent-sdk` (`aamad.config.yml`). Export `AAMAD_TARGET_RUNTIME=claude-agent-sdk` in Build/CI shells so env and config cannot diverge.
2. Language stack: default **Python** (`aamad.config.yml` `language.primary`) aligned with `pip install claude-agent-sdk`. Confirm if TypeScript SDK is preferred instead.
3. HITL granularity: approve entire proposed diff vs file-level vs command-level? MVP recommendation: **entire proposed change-set** for one ticket.
4. Who is the approver — assignee, security role, or any project member? Affects Jira ACL design.
5. In-scope SCM(s) and whether ARLO clones repos locally vs cloud-agent workspaces.
6. Should KEV/EPSS be first-class filters in MVP or deferred?
7. Is this capstone internal-only (skip later commercial sections in PRD) or a demo intended to look productized?
8. Max concurrent instances and monthly LLM budget?
9. Jira project/issue types and required labels/fields for “this is a vuln remediation ticket”?
10. Freedom-to-operate / trademark “ARLO” — not researched.
11. EU AI Act applicability if demonstrated in the EU or on EU personal data.
12. Whether post-approval auto-open of draft PRs is in MVP or comments-only until Integration epic.

## Audit

- **Timestamp:** 2026-08-31T19:14:00Z (operator local 2026-08-31 12:14 PDT)
- **Persona id:** `product-mgr`
- **Action:** `create-mrd`
- **Output path:** `project-context/1.define/mrd.md`
- **Resolved `AAMAD_TARGET_RUNTIME` (at create-mrd):** unset; adapter-registry default `crewai` with warning (superseded by follow-up below).
- **Config loaded (at create-mrd):** `aamad.config.yml` not present; `aamad.config.example.yml` reviewed.
- **Inputs read:** `.cursor/agents/product-mgr.md`, `.cursor/templates/mrd-template.md`, `AGENTS.md`, `CHECKLIST.md`, `README.md` (AAMAD), adapter-registry rule, stakeholder domain inputs in the user request.
- **Prompt Trace:** omitted. This artifact is Define-phase research synthesis with no runtime agent execution, no production system access, and no secret-bearing prompts. Trace omission rationale: not a high-risk executable run; citations live in Sources.
- **Model / temperature / max_tokens:** Cursor Grok 4.6 interactive session; temperature/max_tokens not independently set by this persona (IDE-controlled). Research used live web search/fetch on 2026-08-31.
- **Write method:** temp-write `mrd.md.tmp` then atomic replace to `mrd.md`.
- **Prohibited actions honored:** no application code, no SAD/SFS/Build/Deliver edits, no invented requirements without Assumptions/Open Questions.

### Audit — runtime lock (follow-up)

- **Timestamp:** 2026-08-31T19:19:00Z (operator local 2026-08-31 12:19 PDT)
- **Persona id:** `product-mgr`
- **Action:** operator runtime selection recorded (not a named `*create-mrd` replay)
- **Resolved `AAMAD_TARGET_RUNTIME`:** `claude-agent-sdk` via `aamad.config.yml` `runtime.target`
- **Config loaded:** `aamad.config.yml` (python, `libraries.approved: [claude-agent-sdk]`, `security.require_security_assessment: true`)
- **Note:** Shell env `AAMAD_TARGET_RUNTIME` is session-local; personas that prefer env over config should export `AAMAD_TARGET_RUNTIME=claude-agent-sdk` in Build/CI. Adapter rule: `.cursor/rules/adapter-claude-agent-sdk.mdc`.
- **Prompt Trace:** omitted (config/artifact update only; no model execution against production).
