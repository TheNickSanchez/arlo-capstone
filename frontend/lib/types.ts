/**
 * Frontend contracts for the ARLO Endpoint Remediation Workflow.
 * Keep in sync with `frontend-functional-spec.md` (root).
 * HTTP wiring lives in `lib/api.ts` and is owned by @integration.eng.
 */

export type TicketSystem = "jira" | "servicenow";

/** Live FSM plus PRD terminal statuses used in Run History. */
export type RunPhase =
  | "idle"
  | "investigating"
  | "awaiting_approval"
  | "executing"
  | "done"
  | "error"
  | "rejected"
  | "cancelled";

export type RunStatusLabel =
  | "Idle"
  | "Investigating"
  | "Awaiting Approval"
  | "Executing"
  | "Done"
  | "Failed"
  | "Rejected"
  | "Cancelled";

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

export interface ProposalWriteAction {
  system: "jira" | "servicenow" | "jamf" | "intune";
  actionType: string;
  targetIds: string[];
}

export interface ProposalPayload {
  proposalHash: string;
  ticketKey: string;
  targetedAssets: string[];
  findings: string[];
  writeActions: ProposalWriteAction[];
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

export class MockServiceError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "MockServiceError";
    this.code = code;
  }
}
