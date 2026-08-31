"use client";

import { useState } from "react";
import { useRunList, useRunWorkspace } from "../hooks/useArloRun";
import { isActiveFleetPhase, isHistoryPhase } from "../lib/fsm";
import type { TicketSystem } from "../lib/types";
import styles from "../styles/dashboard.module.css";
import { ApprovalActions } from "./ApprovalActions";
import { FutureWorkStubs } from "./FutureWorkStubs";
import { AuditTimeline, ProposalPanel } from "./ResultsView";
import { FleetActionBanner, RunGrid } from "./RunGrid";
import { SpawnPanel } from "./SpawnPanel";
import { BannerSleeping, StatusBanner } from "./StatusBanner";

export function Dashboard() {
  const { runs, refresh } = useRunList();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const workspace = useRunWorkspace(selectedId);
  const phase = workspace.status?.phase ?? "idle";
  const [spawnError, setSpawnError] = useState<string | null>(null);
  const runError = selectedId ? workspace.error : null;

  async function handleSpawn(ticketId: string, ticketSystem: TicketSystem) {
    setSpawnError(null);
    workspace.setError(null);
    const result = await workspace.spawn(ticketId, ticketSystem);
    if (result.arloId) {
      setSelectedId(result.arloId);
      await refresh();
      return;
    }
    setSpawnError(result.error ?? "Could not start the run.");
  }

  function handleReset() {
    setSelectedId(null);
    workspace.setError(null);
  }

  function handleReviewProposal(arloId: string) {
    setSelectedId(arloId);
    window.requestAnimationFrame(() => {
      document.getElementById("results-heading")?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });
  }

  const activeRuns = runs.filter((run) => isActiveFleetPhase(run.phase));
  const historyRuns = runs.filter((run) => isHistoryPhase(run.phase));
  const awaitingIds = activeRuns
    .filter((run) => run.phase === "awaiting_approval")
    .map((run) => run.arloId);

  return (
    <div className={styles.sections}>
      <SpawnPanel busy={workspace.busy} error={spawnError} onSpawn={handleSpawn} />

      <section className={styles.panel} aria-labelledby="agents-heading">
        <h2 id="agents-heading">Active Agents</h2>
        <p className={styles.hint}>
          In-flight instances only: Investigating, Awaiting Approval, and Executing.
          Select a row to focus it in Run and Results.
        </p>
        <FleetActionBanner awaitingIds={awaitingIds} onReview={handleReviewProposal} />
        <RunGrid
          runs={activeRuns}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onReviewProposal={handleReviewProposal}
          caption="Active ARLO agents"
          emptyMessage="No active agents in flight."
        />
      </section>

      <section className={styles.panel} aria-labelledby="run-heading">
        <h2 id="run-heading">Run</h2>
        <StatusBanner
          phase={phase}
          lastUpdated={workspace.status?.lastUpdated ?? null}
          arloId={workspace.status?.arloId ?? selectedId}
        />
        {phase === "awaiting_approval" ? <BannerSleeping /> : null}
        {runError ? (
          <p className={styles.error} role="alert">
            {runError}
          </p>
        ) : null}
        <div className={styles.runControls}>
          <ApprovalActions
            phase={phase}
            proposalVisible={Boolean(workspace.proposal)}
            busy={workspace.busy}
            onApprove={() => void workspace.approve()}
            onReject={() => void workspace.reject()}
            onReset={handleReset}
          />
        </div>
      </section>

      <section className={styles.panel} aria-labelledby="results-heading">
        <h2 id="results-heading">Results</h2>
        <h3>Proposal</h3>
        <ProposalPanel proposal={workspace.proposal} />
        <h3>Audit</h3>
        <AuditTimeline events={workspace.audit} />
      </section>

      <section className={styles.panel} aria-labelledby="history-heading">
        <h2 id="history-heading">Run History</h2>
        <p className={styles.hint}>
          Completed, rejected, failed, and cancelled runs remain listed. Select a row
          to inspect Results, or open detail.
        </p>
        <RunGrid
          runs={historyRuns}
          selectedId={selectedId}
          onSelect={setSelectedId}
          caption="Historical ARLO runs"
          emptyMessage="No completed runs yet."
        />
      </section>

      <FutureWorkStubs />
    </div>
  );
}
