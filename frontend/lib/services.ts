/**
 * Mock service layer for the ARLO dashboard.
 * No network, Temporal, MCP, or Anthropic calls.
 * @integration.eng will replace these with `lib/api.ts` FastAPI clients.
 */

import { nextMockPhase } from "./fsm";
import {
  MOCK_ACTOR,
  appendAudit,
  buildProposal,
  nowIso,
  seedHistoricalRuns,
  type InternalRun,
} from "./mock-data";
import { MockServiceError, type AuditEvent, type ProposalPayload, type RunPhase, type RunStatus, type TicketSystem } from "./types";

const ADVANCE_INTERVAL_MS = 2000;
const MOCK_LATENCY_MS = 60;

const runs = new Map<string, InternalRun>();
let nextSeq = 675;

function delay(ms = MOCK_LATENCY_MS): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function parseTicketSystem(value: string): TicketSystem {
  if (value === "jira" || value === "servicenow") {
    return value;
  }
  throw new MockServiceError(
    "validation_error",
    "Ticket system must be Jira or ServiceNow.",
  );
}

function validateTicketId(ticketId: string): string {
  const trimmed = ticketId.trim();
  if (!trimmed) {
    throw new MockServiceError("validation_error", "Enter a ticket ID before running ARLO.");
  }
  if (trimmed.length < 3) {
    throw new MockServiceError("validation_error", "Ticket ID is too short.");
  }
  return trimmed;
}

function toStatus(run: InternalRun): RunStatus {
  return {
    arloId: run.arloId,
    ticketId: run.ticketId,
    ticketSystem: run.ticketSystem,
    phase: run.phase,
    lastUpdated: run.lastUpdated,
    createdAt: run.createdAt,
    proposalHash: run.proposal?.proposalHash,
    errorMessage: run.errorMessage,
  };
}

function ensureSeeded(): void {
  seedHistoricalRuns(runs);
}

function requireRun(arloId: string): InternalRun {
  ensureSeeded();
  const run = runs.get(arloId);
  if (!run) {
    throw new MockServiceError("not_found", `No run found for ${arloId}.`);
  }
  return run;
}

function maybeAdvance(run: InternalRun): void {
  if (run.phase === "idle") {
    return;
  }
  const next = nextMockPhase(run.phase, run.approved);
  if (!next) {
    return;
  }
  const elapsed = Date.now() - run.lastAdvanceAt;
  if (elapsed < ADVANCE_INTERVAL_MS) {
    return;
  }
  applyPhase(run, next);
}

function applyPhase(run: InternalRun, next: RunPhase): void {
  run.phase = next;
  run.lastAdvanceAt = Date.now();
  run.lastUpdated = nowIso();

  if (next === "awaiting_approval") {
    run.proposal = buildProposal(run);
    appendAudit(run, {
      kind: "mcp_read",
      summary: `Read ${run.ticketSystem} ticket ${run.ticketId}.`,
      mcpSystem: run.ticketSystem,
      action: "read_ticket_context",
      result: "success",
      phase: "investigating",
    });
    appendAudit(run, {
      kind: "mcp_read",
      summary: "Read Jamf compliance and recent device logs.",
      mcpSystem: "jamf",
      action: "read_device_compliance",
      result: "success",
      phase: "investigating",
    });
    appendAudit(run, {
      kind: "proposal_persisted",
      summary: `Proposal ${run.proposal.proposalHash} stored. Agent sleeping — no mutations until approval.`,
    });
    appendAudit(run, {
      kind: "hitl_sleep",
      summary: "Durable approval gate. Worker is idle; no MCP or model session is held.",
    });
  }

  if (next === "executing") {
    appendAudit(run, {
      kind: "mcp_write",
      summary: "Applying approved Jamf configuration profile.",
      mcpSystem: "jamf",
      action: "apply_configuration_profile",
      result: "success",
    });
    appendAudit(run, {
      kind: "mcp_write",
      summary: "Creating ServiceNow tracking change request.",
      mcpSystem: "servicenow",
      action: "create_change_request",
      result: "success",
    });
  }

  if (next === "done") {
    appendAudit(run, {
      kind: "mcp_read",
      summary: "Validation read: FileVault is enabled.",
      mcpSystem: "jamf",
      action: "read_device_compliance",
      result: "success",
    });
    appendAudit(run, {
      kind: "mcp_write",
      summary: `Closed ${run.ticketId} per the approved plan.`,
      mcpSystem: run.ticketSystem === "jira" ? "jira" : "servicenow",
      action: "close_ticket",
      result: "success",
    });
    appendAudit(run, {
      kind: "run_complete",
      summary: `${run.arloId} reached Done.`,
    });
  }
}

ensureSeeded();

export async function startRun(
  ticketId: string,
  ticketSystem: string,
): Promise<{ arlo_id: string }> {
  await delay();
  const system = parseTicketSystem(ticketSystem);
  const key = validateTicketId(ticketId);

  for (const run of runs.values()) {
    if (
      run.ticketId.toLowerCase() === key.toLowerCase() &&
      run.ticketSystem === system &&
      run.phase !== "done" &&
      run.phase !== "error" &&
      run.phase !== "rejected" &&
      run.phase !== "cancelled" &&
      run.phase !== "idle"
    ) {
      throw new MockServiceError(
        "conflict",
        `${run.arloId} is already active for ${key}. Duplicate spawn is blocked.`,
      );
    }
  }

  const arloId = `ARLO-${nextSeq}`;
  nextSeq += 1;
  const createdAt = nowIso();
  const run: InternalRun = {
    arloId,
    ticketId: key,
    ticketSystem: system,
    phase: "investigating",
    createdAt,
    lastUpdated: createdAt,
    lastAdvanceAt: Date.now(),
    approved: false,
    audit: [],
  };
  appendAudit(run, {
    kind: "spawn",
    summary: `Spawned ${arloId} mapped 1:1 to ${system} ticket ${key}. Investigation is read-only.`,
  });
  appendAudit(run, {
    kind: "mcp_read",
    summary: "Starting read-only investigation (Jira/SNOW, Jamf, Intune as applicable).",
    result: "success",
  });
  runs.set(arloId, run);
  return { arlo_id: arloId };
}

export async function getRunStatus(arloId: string): Promise<RunStatus> {
  await delay(20);
  const run = requireRun(arloId);
  maybeAdvance(run);
  return toStatus(run);
}

export async function approveRun(
  arloId: string,
  proposalHash: string,
): Promise<RunStatus> {
  await delay();
  const run = requireRun(arloId);
  if (run.phase !== "awaiting_approval") {
    throw new MockServiceError(
      "conflict",
      "Approve is only available while the run is Awaiting Approval.",
    );
  }
  if (!run.proposal) {
    throw new MockServiceError("conflict", "Proposal is not visible yet. Approve is disabled.");
  }
  if (run.proposal.proposalHash !== proposalHash) {
    throw new MockServiceError(
      "conflict",
      "Stale proposal hash. Refresh the proposal before approving.",
    );
  }
  run.approved = true;
  appendAudit(run, {
    kind: "hitl_approve",
    summary: `Approved by ${MOCK_ACTOR}. Frozen action list hash ${proposalHash}.`,
  });
  applyPhase(run, "executing");
  return toStatus(run);
}

export async function rejectRun(arloId: string, proposalHash: string): Promise<RunStatus> {
  await delay();
  const run = requireRun(arloId);
  if (run.phase !== "awaiting_approval") {
    throw new MockServiceError(
      "conflict",
      "Reject is only available while the run is Awaiting Approval.",
    );
  }
  if (run.proposal && run.proposal.proposalHash !== proposalHash) {
    throw new MockServiceError("conflict", "Stale proposal hash. Refresh before rejecting.");
  }
  run.phase = "rejected";
  run.lastUpdated = nowIso();
  appendAudit(run, {
    kind: "hitl_reject",
    summary: `Rejected by ${MOCK_ACTOR}. No endpoint or ticket writes were issued.`,
  });
  return toStatus(run);
}

export async function getProposal(arloId: string): Promise<ProposalPayload | null> {
  await delay(10);
  const run = requireRun(arloId);
  return run.proposal ?? null;
}

export async function listAuditEvents(arloId: string): Promise<AuditEvent[]> {
  await delay(10);
  const run = requireRun(arloId);
  return [...run.audit];
}

export async function listRuns(): Promise<RunStatus[]> {
  await delay(10);
  return listRunsSync();
}

export function listRunsSync(): RunStatus[] {
  ensureSeeded();
  return [...runs.values()]
    .map(toStatus)
    .sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1));
}

export function peekRun(arloId: string): {
  status: RunStatus;
  proposal: ProposalPayload | null;
  audit: AuditEvent[];
} | null {
  ensureSeeded();
  const run = runs.get(arloId);
  if (!run) {
    return null;
  }
  return {
    status: toStatus(run),
    proposal: run.proposal ?? null,
    audit: [...run.audit],
  };
}

export const MOCK_APPROVER_ID = MOCK_ACTOR;
