/** Typed FastAPI client boundary (SAD §3). Wire calls in @integration.eng. */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
