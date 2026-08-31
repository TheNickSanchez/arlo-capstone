"""FastAPI entrypoint (SAD §4). Business routes belong to @backend.eng.

Expected process: uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
Liveness: GET /health  |  Readiness: GET /ready (postgres + Temporal) — implement in *develop-be.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from backend.app.routers import approvals, instances, webhooks

app = FastAPI(title="ARLO API", version="0.0.0-scaffold")
app.include_router(instances.router)
app.include_router(approvals.router)
app.include_router(webhooks.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness only. Do not check dependencies here (SAD §4)."""
    return {"status": "ok", "service": "arlo-api"}


@app.get("/ready")
def ready() -> JSONResponse:
    """Readiness is unimplemented until @backend.eng wires PostgreSQL + Temporal."""
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "upstream_unavailable",
                "message": "readiness not implemented (scaffold)",
            }
        },
    )
