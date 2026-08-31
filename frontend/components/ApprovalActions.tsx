import { canApprove, isResettable } from "../lib/fsm";
import type { RunPhase } from "../lib/types";
import styles from "../styles/dashboard.module.css";

export function ApprovalActions({
  phase,
  proposalVisible,
  busy,
  onApprove,
  onReject,
  onReset,
}: {
  phase: RunPhase;
  proposalVisible: boolean;
  busy: boolean;
  onApprove: () => void;
  onReject: () => void;
  onReset: () => void;
}) {
  const approveEnabled = canApprove(phase) && proposalVisible && !busy;
  const showHitl = canApprove(phase);
  const showReset = isResettable(phase);

  if (!showHitl && !showReset) {
    return null;
  }

  return (
    <div className={styles.actions}>
      {showHitl ? (
        <>
          <button
            type="button"
            className={styles.buttonPrimary}
            onClick={onApprove}
            disabled={!approveEnabled}
          >
            Approve Remediation
          </button>
          <button
            type="button"
            className={styles.buttonDanger}
            onClick={onReject}
            disabled={!approveEnabled}
          >
            Reject
          </button>
        </>
      ) : null}
      {showReset ? (
        <button type="button" className={styles.button} onClick={onReset} disabled={busy}>
          Reset
        </button>
      ) : null}
    </div>
  );
}
