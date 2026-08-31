import Link from "next/link";
import styles from "../../styles/dashboard.module.css";

export default function LoginPage() {
  return (
    <section className={styles.panel} aria-labelledby="login-heading">
      <h2 id="login-heading">Sign in</h2>
      <p className={styles.hint}>
        Authenticated operators are required before Approve (SAD §8). Session cookies or
        signed tokens are wired by @integration.eng. This page is a visible stub.
      </p>
      <form className={styles.formGrid} aria-disabled="true">
        <label className={styles.label} htmlFor="username">
          Username
          <input
            id="username"
            className={styles.input}
            name="username"
            autoComplete="username"
            disabled
          />
        </label>
        <label className={styles.label} htmlFor="password">
          Password
          <input
            id="password"
            className={styles.input}
            name="password"
            type="password"
            autoComplete="current-password"
            disabled
          />
        </label>
        <div className={styles.actions}>
          <button className={styles.buttonPrimary} type="button" disabled>
            Sign in
          </button>
        </div>
      </form>
      <p className={styles.hintSpaced}>
        Mock dashboard uses operator identity <code>demo-operator</code>.{" "}
        <Link href="/">Return to dashboard</Link>
      </p>
    </section>
  );
}
