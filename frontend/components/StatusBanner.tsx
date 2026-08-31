import { phaseLabel } from "../lib/fsm";
import type { RunPhase } from "../lib/types";
import styles from "../styles/dashboard.module.css";
import { StatusBadge } from "./StatusBadge";

function formatTimestamp(iso: string | null): string {
  if (!iso) {
    return "—";
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString();
}

export function StatusBanner({
  phase,
  lastUpdated,
  arloId,
}: {
  phase: RunPhase;
  lastUpdated: string | null;
  arloId: string | null;
}) {
  const label = phaseLabel(phase);
  const title = arloId ? `${arloId} — ${label}` : `No active run — ${label}`;

  return (
    <div className={styles.banner} aria-live="polite">
      <div className={styles.bannerCopy}>
        <h2>{title}</h2>
        <p className={styles.meta}>Last updated: {formatTimestamp(lastUpdated)}</p>
      </div>
      <StatusBadge phase={phase} />
    </div>
  );
}

export function BannerSleeping() {
  return (
    <div className={styles.sleepBanner} role="status">
      <p>
        <strong>Agent is sleeping.</strong> No endpoint or ticket changes until you
        approve. Closing this page does not skip the gate.
      </p>
    </div>
  );
}
