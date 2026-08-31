"use client";

import Link from "next/link";
import { useRunWorkspace } from "../hooks/useArloRun";
import styles from "../styles/dashboard.module.css";
import { ApprovalActions } from "./ApprovalActions";
import { AuditTimeline, ProposalPanel } from "./ResultsView";
import { BannerSleeping, StatusBanner } from "./StatusBanner";

export function RunDetailView({ arloId }: { arloId: string }) {
  const workspace = useRunWorkspace(arloId);
  const phase = workspace.status?.phase ?? "idle";

  return (
    <div className={styles.sections}>
      <p className={styles.back}>
        <Link href="/">← Back to dashboard</Link>
      </p>
      <section className={styles.panel} aria-labelledby="run-heading">
        <h2 id="run-heading">Run</h2>
        <StatusBanner
          phase={workspace.status?.phase ?? "idle"}
          lastUpdated={workspace.status?.lastUpdated ?? null}
          arloId={arloId}
        />
        {phase === "awaiting_approval" ? <BannerSleeping /> : null}
        {workspace.error ? (
          <p className={styles.error} role="alert">
            {workspace.error}
          </p>
        ) : null}
        <div className={styles.runControls}>
          <ApprovalActions
            phase={phase}
            proposalVisible={Boolean(workspace.proposal)}
            busy={workspace.busy}
            onApprove={() => void workspace.approve()}
            onReject={() => void workspace.reject()}
            onReset={() => {
              window.location.assign("/");
            }}
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
    </div>
  );
}
