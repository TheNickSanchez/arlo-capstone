"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { MOCK_APPROVER_ID } from "../lib/services";
import styles from "../styles/dashboard.module.css";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className={styles.page}>
      <a className={styles.skipLink} href="#main">
        Skip to main content
      </a>
      <header className={styles.header}>
        <div className={styles.brand}>
          <h1>ARLO</h1>
          <p className={styles.tagline}>Automated Remediation Loop Orchestrator</p>
        </div>
        <nav className={styles.nav} aria-label="Primary">
          <Link href="/">Dashboard</Link>
          <Link href="/login">Sign in</Link>
          <span className={styles.actor}>Mock operator: {MOCK_APPROVER_ID}</span>
        </nav>
      </header>
      <main id="main">{children}</main>
    </div>
  );
}
