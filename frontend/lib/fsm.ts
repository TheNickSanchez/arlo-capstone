import type { RunPhase, RunStatusLabel } from "./types";

export const LIVE_FSM_PHASES: RunPhase[] = [
  "idle",
  "investigating",
  "awaiting_approval",
  "executing",
  "done",
  "error",
];

const PHASE_LABELS: Record<RunPhase, RunStatusLabel> = {
  idle: "Idle",
  investigating: "Investigating",
  awaiting_approval: "Awaiting Approval",
  executing: "Executing",
  done: "Done",
  error: "Failed",
  rejected: "Rejected",
  cancelled: "Cancelled",
};

export type PillTone = "gray" | "blue" | "yellow" | "green" | "red";

const PHASE_TONE: Record<RunPhase, PillTone> = {
  idle: "gray",
  investigating: "blue",
  awaiting_approval: "yellow",
  executing: "blue",
  done: "green",
  error: "red",
  rejected: "red",
  cancelled: "gray",
};

export function phaseLabel(phase: RunPhase): RunStatusLabel {
  return PHASE_LABELS[phase];
}

export function phaseTone(phase: RunPhase): PillTone {
  return PHASE_TONE[phase];
}

const ACTIVE_FLEET_PHASES: RunPhase[] = [
  "investigating",
  "awaiting_approval",
  "executing",
];

const RUN_HISTORY_PHASES: RunPhase[] = ["done", "rejected", "error", "cancelled"];

export function isActiveFleetPhase(phase: RunPhase): boolean {
  return ACTIVE_FLEET_PHASES.includes(phase);
}

/** Terminal rows for Run History. `error` is the Failed label in the UI. */
export function isHistoryPhase(phase: RunPhase): boolean {
  return RUN_HISTORY_PHASES.includes(phase);
}

export function isTerminal(phase: RunPhase): boolean {
  return isHistoryPhase(phase);
}

export function isResettable(phase: RunPhase): boolean {
  return isTerminal(phase);
}

export function canApprove(phase: RunPhase): boolean {
  return phase === "awaiting_approval";
}

/** Next phase for mock telemetry. HITL blocks awaiting_approval until approve. */
export function nextMockPhase(phase: RunPhase, approved: boolean): RunPhase | null {
  switch (phase) {
    case "idle":
      return "investigating";
    case "investigating":
      return "awaiting_approval";
    case "awaiting_approval":
      return approved ? "executing" : null;
    case "executing":
      return "done";
    default:
      return null;
  }
}
