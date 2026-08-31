import styles from "../styles/dashboard.module.css";

export function FutureWorkStubs() {
  return (
    <section className={styles.panel} aria-labelledby="future-heading">
      <h2 id="future-heading">Future work (not in MVP)</h2>
      <p className={styles.hint}>
        Visible placeholders only. These controls are disabled until a later epic.
      </p>
      <div className={styles.stubs}>
        <button type="button" className={styles.stub} disabled>
          Webhook auto-spawn
        </button>
        <button type="button" className={styles.stub} disabled>
          KEV / SLA badges
        </button>
        <button type="button" className={styles.stub} disabled>
          Request changes
        </button>
        <button type="button" className={styles.stub} disabled>
          Export audit
        </button>
        <button type="button" className={styles.stub} disabled>
          Chat inside instance
        </button>
      </div>
    </section>
  );
}
