import type { AuditEvent, ProposalPayload, RunPhase, TicketSystem } from "./types";

export const MOCK_ACTOR = "demo-operator";

export type InternalRun = {
  arloId: string;
  ticketId: string;
  ticketSystem: TicketSystem;
  phase: RunPhase;
  createdAt: string;
  lastUpdated: string;
  lastAdvanceAt: number;
  approved: boolean;
  proposal?: ProposalPayload;
  audit: AuditEvent[];
  errorMessage?: string;
};

export function nowIso(): string {
  return new Date().toISOString();
}

export function appendAudit(
  run: InternalRun,
  event: Omit<AuditEvent, "at" | "arloId" | "phase"> & { phase?: RunPhase },
): void {
  run.audit.push({
    at: nowIso(),
    arloId: run.arloId,
    phase: event.phase ?? run.phase,
    kind: event.kind,
    summary: event.summary,
    mcpSystem: event.mcpSystem,
    action: event.action,
    result: event.result,
    policyDeny: event.policyDeny,
  });
}

export function buildProposal(run: InternalRun): ProposalPayload {
  const jamfTarget = `device-${run.arloId.replace("ARLO-", "")}`;
  return {
    proposalHash: `prop-${run.arloId}-v1`,
    ticketKey: run.ticketId,
    targetedAssets: [jamfTarget, `ci-${run.ticketId.toLowerCase()}`],
    findings: [
      `Ticket ${run.ticketId} describes endpoint non-compliance.`,
      "Jamf compliance read: FileVault is disabled on the mapped Mac.",
      "ServiceNow: no duplicate open CHG found for this CI.",
    ],
    writeActions: [
      {
        system: "jamf",
        actionType: "apply_configuration_profile",
        targetIds: ["profile-filevault-enforce", jamfTarget],
      },
      {
        system: "servicenow",
        actionType: "create_change_request",
        targetIds: [`CHG-track-${run.arloId}`],
      },
      {
        system: "jira",
        actionType: "post_discovery_summary",
        targetIds: [run.ticketId],
      },
      {
        system: "jira",
        actionType: "transition_and_close",
        targetIds: [run.ticketId],
      },
    ],
    validationChecks: [
      "Re-read Jamf compliance: FileVault enabled.",
      "Close the ticket only if validation passes.",
    ],
    residualRisk: "Device may prompt the user; no wipe/lock/retire is in this plan.",
    diffSummary:
      "+ Jamf profile FileVault-Enforce on mapped device\n" +
      "+ ServiceNow tracking CHG (create after approval)\n" +
      `+ Jira summary + close on ${run.ticketId}\n` +
      "  endpoints and ticket unchanged until approval",
  };
}

function seedRun(
  runs: Map<string, InternalRun>,
  partial: {
    arloId: string;
    ticketId: string;
    ticketSystem: TicketSystem;
    phase: RunPhase;
    hoursAgo: number;
  },
): void {
  const created = new Date(Date.now() - partial.hoursAgo * 3600 * 1000);
  const run: InternalRun = {
    arloId: partial.arloId,
    ticketId: partial.ticketId,
    ticketSystem: partial.ticketSystem,
    phase: partial.phase,
    createdAt: created.toISOString(),
    lastUpdated: new Date(created.getTime() + 12 * 60 * 1000).toISOString(),
    lastAdvanceAt: Date.now(),
    approved: partial.phase === "done",
    audit: [],
  };
  if (partial.phase !== "investigating") {
    run.proposal = buildProposal(run);
  }
  appendAudit(run, {
    kind: "spawn",
    summary: `Mapped ${run.arloId} to ${run.ticketSystem} ticket ${run.ticketId}.`,
    phase: "investigating",
  });
  if (run.proposal) {
    appendAudit(run, {
      kind: "proposal_persisted",
      summary: `Proposal ${run.proposal.proposalHash} stored. Agent sleeping.`,
      phase: "awaiting_approval",
    });
  }
  if (partial.phase === "done") {
    appendAudit(run, {
      kind: "hitl_approve",
      summary: `Approved by ${MOCK_ACTOR}.`,
      phase: "awaiting_approval",
    });
    appendAudit(run, {
      kind: "mcp_write",
      summary: "Applied approved Jamf FileVault profile.",
      mcpSystem: "jamf",
      action: "apply_configuration_profile",
      result: "success",
      phase: "executing",
    });
    appendAudit(run, {
      kind: "validation",
      summary: "FileVault enabled. Ticket closed per approved plan.",
      result: "success",
      phase: "done",
    });
  }
  if (partial.phase === "rejected") {
    appendAudit(run, {
      kind: "hitl_reject",
      summary: `Rejected by ${MOCK_ACTOR}. No endpoint or ticket writes.`,
      phase: "rejected",
    });
  }
  runs.set(run.arloId, run);
}

export function seedHistoricalRuns(runs: Map<string, InternalRun>): void {
  if (runs.size > 0) {
    return;
  }
  seedRun(runs, {
    arloId: "ARLO-673",
    ticketId: "JIRA-88",
    ticketSystem: "jira",
    phase: "done",
    hoursAgo: 26,
  });
  seedRun(runs, {
    arloId: "ARLO-674",
    ticketId: "INC0010041",
    ticketSystem: "servicenow",
    phase: "rejected",
    hoursAgo: 8,
  });
}
