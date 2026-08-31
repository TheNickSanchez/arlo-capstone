/**
 * Typed FastAPI client boundary (SAD §3).
 * MVP UI uses mock `lib/services.ts`. Wire HTTP here in @integration.eng.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
