"use client";

import Link from "next/link";
import { canApprove } from "../lib/fsm";
import type { RunStatus } from "../lib/types";
import buttons from "../styles/dashboard.module.css";
import styles from "../styles/fleet.module.css";
import { StatusBadge } from "./StatusBadge";

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString();
}

export function FleetActionBanner({
  awaitingIds,
  onReview,
}: {
  awaitingIds: string[];
  onReview: (arloId: string) => void;
}) {
  const firstId = awaitingIds[0];
  if (!firstId) {
    return null;
  }
  const countLabel =
    awaitingIds.length === 1
      ? `${firstId} is awaiting approval.`
      : `${awaitingIds.length} runs are awaiting approval (${awaitingIds.join(", ")}).`;

  return (
    <div className={styles.actionBanner} role="status">
      <p>
        <strong>Action required.</strong> {countLabel} No endpoint or ticket changes
        until you approve.
      </p>
      <button
        type="button"
        className={buttons.buttonPrimary}
        onClick={() => onReview(firstId)}
      >
        Review Proposal
      </button>
    </div>
  );
}

export function RunGrid({
  runs,
  selectedId,
  onSelect,
  onReviewProposal,
  caption,
  emptyMessage,
}: {
  runs: RunStatus[];
  selectedId: string | null;
  onSelect: (arloId: string) => void;
  onReviewProposal?: (arloId: string) => void;
  caption: string;
  emptyMessage: string;
}) {
  if (runs.length === 0) {
    return <p className={styles.emptyState}>{emptyMessage}</p>;
  }

  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <caption className="visually-hidden">{caption}</caption>
        <thead>
          <tr>
            <th scope="col">Instance</th>
            <th scope="col">Ticket</th>
            <th scope="col">Status</th>
            <th scope="col">Created</th>
            <th scope="col">Last updated</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.arloId} aria-selected={run.arloId === selectedId}>
              <td>
                <button
                  type="button"
                  className={styles.rowButton}
                  onClick={() => onSelect(run.arloId)}
                  aria-current={run.arloId === selectedId ? "true" : undefined}
                >
                  {run.arloId}
                </button>
              </td>
              <td>
                {run.ticketSystem}: {run.ticketId}
              </td>
              <td>
                <StatusBadge phase={run.phase} />
              </td>
              <td>{formatTimestamp(run.createdAt)}</td>
              <td>{formatTimestamp(run.lastUpdated)}</td>
              <td>
                <div className={styles.rowActions}>
                  <Link href={`/runs/${run.arloId}`}>Open detail</Link>
                  {onReviewProposal && canApprove(run.phase) ? (
                    <button
                      type="button"
                      className={buttons.button}
                      onClick={() => onReviewProposal(run.arloId)}
                    >
                      Review Proposal
                    </button>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
