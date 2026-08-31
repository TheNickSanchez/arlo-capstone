import { phaseLabel, phaseTone, type PillTone } from "../lib/fsm";
import type { RunPhase } from "../lib/types";
import styles from "../styles/dashboard.module.css";

const TONE_CLASS: Record<PillTone, string> = {
  gray: styles.toneGray,
  blue: styles.toneBlue,
  yellow: styles.toneYellow,
  green: styles.toneGreen,
  red: styles.toneRed,
};

export function StatusBadge({ phase }: { phase: RunPhase }) {
  const label = phaseLabel(phase);
  const tone = phaseTone(phase);
  return (
    <span className={`${styles.pill} ${TONE_CLASS[tone]}`} title={label}>
      <span className={styles.dot} aria-hidden="true" />
      {label}
    </span>
  );
}
