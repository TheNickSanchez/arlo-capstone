import type { ReactNode } from "react";
import { AppShell } from "../components/AppShell";
import "./globals.css";

export const metadata = {
  title: "ARLO",
  description: "Automated Remediation Loop Orchestrator",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
