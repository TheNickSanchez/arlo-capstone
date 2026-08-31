"use client";

import { useCallback, useEffect, useState } from "react";
import { isTerminal } from "../lib/fsm";
import {
  approveRun,
  getProposal,
  getRunStatus,
  listAuditEvents,
  listRuns,
  listRunsSync,
  peekRun,
  rejectRun,
  startRun,
} from "../lib/services";
import { MockServiceError, type AuditEvent, type ProposalPayload, type RunStatus } from "../lib/types";

const POLL_MS = 2500;

function asErrorMessage(err: unknown): string {
  if (err instanceof MockServiceError) {
    return err.message;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return "Unexpected mock service error.";
}

export function useRunList() {
  const [runs, setRuns] = useState<RunStatus[]>(() => listRunsSync());
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const current = await listRuns();
      await Promise.all(
        current
          .filter((run) => !isTerminal(run.phase) && run.phase !== "idle")
          .map((run) => getRunStatus(run.arloId)),
      );
      setRuns(await listRuns());
      setError(null);
    } catch (err) {
      setError(asErrorMessage(err));
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => {
      void refresh();
    }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [refresh]);

  return { runs, error, refresh };
}

export function useRunWorkspace(arloId: string | null) {
  const initial = arloId ? peekRun(arloId) : null;
  const [status, setStatus] = useState<RunStatus | null>(initial?.status ?? null);
  const [proposal, setProposal] = useState<ProposalPayload | null>(initial?.proposal ?? null);
  const [audit, setAudit] = useState<AuditEvent[]>(initial?.audit ?? []);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    if (!arloId) {
      setStatus(null);
      setProposal(null);
      setAudit([]);
      return;
    }
    try {
      const nextStatus = await getRunStatus(arloId);
      const [nextProposal, nextAudit] = await Promise.all([
        getProposal(arloId),
        listAuditEvents(arloId),
      ]);
      setStatus(nextStatus);
      setProposal(nextProposal);
      setAudit(nextAudit);
      setError(null);
    } catch (err) {
      setError(asErrorMessage(err));
    }
  }, [arloId]);

  useEffect(() => {
    const snapshot = arloId ? peekRun(arloId) : null;
    setStatus(snapshot?.status ?? null);
    setProposal(snapshot?.proposal ?? null);
    setAudit(snapshot?.audit ?? []);
    void refresh();
    if (!arloId) {
      return;
    }
    const timer = window.setInterval(() => {
      void refresh();
    }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [arloId, refresh]);

  const spawn = useCallback(async (ticketId: string, ticketSystem: string) => {
    setBusy(true);
    setError(null);
    try {
      const result = await startRun(ticketId, ticketSystem);
      return { arloId: result.arlo_id, error: null };
    } catch (err) {
      const message = asErrorMessage(err);
      setError(message);
      return { arloId: null, error: message };
    } finally {
      setBusy(false);
    }
  }, []);

  const approve = useCallback(async () => {
    if (!arloId || !proposal) {
      return;
    }
    setBusy(true);
    try {
      await approveRun(arloId, proposal.proposalHash);
      await refresh();
    } catch (err) {
      setError(asErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }, [arloId, proposal, refresh]);

  const reject = useCallback(async () => {
    if (!arloId || !proposal) {
      return;
    }
    setBusy(true);
    try {
      await rejectRun(arloId, proposal.proposalHash);
      await refresh();
    } catch (err) {
      setError(asErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }, [arloId, proposal, refresh]);

  return { status, proposal, audit, error, busy, spawn, approve, reject, setError };
}

export { asErrorMessage };
