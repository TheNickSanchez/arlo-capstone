import type { AuditEvent, ProposalPayload } from "../lib/types";
import { phaseLabel } from "../lib/fsm";
import styles from "../styles/dashboard.module.css";

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString();
}

export function ProposalPanel({ proposal }: { proposal: ProposalPayload | null }) {
  if (!proposal) {
    return <p className={styles.empty}>Proposal appears when investigation completes.</p>;
  }

  return (
    <div className={styles.proposalGrid}>
      <p className={styles.meta}>
        Proposal hash <code>{proposal.proposalHash}</code> · ticket {proposal.ticketKey}
      </p>
      <div>
        <h3>Findings</h3>
        <ul className={styles.list}>
          {proposal.findings.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
      <div>
        <h3>Enumerated write actions</h3>
        <ul className={styles.list}>
          {proposal.writeActions.map((action) => (
            <li key={`${action.system}-${action.actionType}`}>
              {action.system}: {action.actionType} ({action.targetIds.join(", ")})
            </li>
          ))}
        </ul>
      </div>
      <div>
        <h3>Validation</h3>
        <ul className={styles.list}>
          {proposal.validationChecks.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
      <p>
        <strong>Residual risk:</strong> {proposal.residualRisk}
      </p>
      <div>
        <h3>Diff summary</h3>
        <pre className={styles.pre}>{proposal.diffSummary}</pre>
      </div>
    </div>
  );
}

export function AuditTimeline({ events }: { events: AuditEvent[] }) {
  if (events.length === 0) {
    return <p className={styles.empty}>Audit events appear as the run progresses.</p>;
  }

  return (
    <ol className={styles.audit}>
      {events.map((event, index) => (
        <li
          key={`${event.at}-${event.kind}-${index}`}
          className={styles.auditItem}
        >
          <div className={styles.auditMeta}>
            {formatTimestamp(event.at)} · {phaseLabel(event.phase)} · {event.kind}
            {event.mcpSystem ? ` · ${event.mcpSystem}` : ""}
            {event.action ? ` · ${event.action}` : ""}
            {event.result ? ` · ${event.result}` : ""}
          </div>
          <div>{event.summary}</div>
          {event.policyDeny ? (
            <div className={styles.deny}>Policy deny — write was not treated as success.</div>
          ) : null}
        </li>
      ))}
    </ol>
  );
}
