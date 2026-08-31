import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "ARLO",
  description: "Automated Remediation Loop Orchestrator",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
