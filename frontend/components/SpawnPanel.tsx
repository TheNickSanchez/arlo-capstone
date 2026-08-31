"use client";

import { useState, type FormEvent } from "react";
import type { TicketSystem } from "../lib/types";
import styles from "../styles/dashboard.module.css";

export function SpawnPanel({
  busy,
  error,
  onSpawn,
}: {
  busy: boolean;
  error: string | null;
  onSpawn: (ticketId: string, ticketSystem: TicketSystem) => Promise<void>;
}) {
  const [ticketId, setTicketId] = useState("JIRA-102");
  const [ticketSystem, setTicketSystem] = useState<TicketSystem>("jira");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSpawn(ticketId, ticketSystem);
  }

  return (
    <section className={styles.panel} aria-labelledby="inputs-heading">
      <h2 id="inputs-heading">Inputs</h2>
      <p className={styles.hint}>
        Map a new ARLO instance to an existing Jira or ServiceNow ticket. Investigation
        is read-only until a human approves the proposal.
      </p>
      <form className={styles.formGrid} onSubmit={handleSubmit}>
        <fieldset className={styles.fieldset}>
          <legend>Ticket system</legend>
          <div className={styles.radioRow}>
            <label>
              <input
                type="radio"
                name="ticketSystem"
                value="jira"
                checked={ticketSystem === "jira"}
                onChange={() => setTicketSystem("jira")}
              />
              Jira
            </label>
            <label>
              <input
                type="radio"
                name="ticketSystem"
                value="servicenow"
                checked={ticketSystem === "servicenow"}
                onChange={() => setTicketSystem("servicenow")}
              />
              ServiceNow
            </label>
          </div>
        </fieldset>
        <label className={styles.label} htmlFor="ticket-id">
          Ticket ID
          <input
            id="ticket-id"
            className={styles.input}
            name="ticketId"
            value={ticketId}
            onChange={(event) => setTicketId(event.target.value)}
            placeholder="JIRA-102"
            autoComplete="off"
            required
          />
        </label>
        <div className={styles.actions}>
          <button className={styles.buttonPrimary} type="submit" disabled={busy}>
            {busy ? "Starting…" : "Run ARLO"}
          </button>
        </div>
        {error ? (
          <p className={styles.error} role="alert">
            {error}
          </p>
        ) : null}
      </form>
      <p className={styles.guarantee}>
        <strong>No endpoint or ticket mutation until you approve.</strong>
      </p>
    </section>
  );
}
