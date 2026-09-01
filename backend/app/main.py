"""FastAPI entrypoint (SAD §4).

Process: uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
Liveness: GET /health  |  Readiness: GET /ready (PostgreSQL + Temporal)
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.v1 import api_router
from backend.app.config import settings
from backend.app.db.migrate import run_upgrade_head
from backend.app.db.session import check_database_ready
from backend.app.error_handlers import register_exception_handlers
from backend.app.temporal_client import check_temporal_ready

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("arlo.api")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Run Alembic on startup so local uvicorn and Compose share the same schema."""
    logger.info("running database migrations")
    await asyncio.to_thread(run_upgrade_head)
    yield


app = FastAPI(title="ARLO API", version="1.0.0", lifespan=lifespan)

# UI never talks to Temporal/MCP/Anthropic directly (SAD §3). Credentials are
# required because auth uses an httpOnly session cookie.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness only. Do not check dependencies here (SAD §4)."""
    return {"status": "ok", "service": "arlo-api"}


@app.get("/ready")
async def ready() -> JSONResponse:
    """Readiness: PostgreSQL + Temporal connectivity (SAD §4)."""
    db_ok = await check_database_ready()
    temporal_ok = await check_temporal_ready()
    if db_ok and temporal_ok:
        return JSONResponse(
            status_code=200,
            content={"status": "ok", "database": "up", "temporal": "up"},
        )
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "upstream_unavailable",
                "message": "one or more dependencies are not ready",
                "arlo_id": None,
            },
            "database": "up" if db_ok else "down",
            "temporal": "up" if temporal_ok else "down",
        },
    )
