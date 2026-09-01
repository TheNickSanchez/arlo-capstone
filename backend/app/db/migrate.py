"""Run Alembic upgrades from the API process (SAD §4; migrations on startup).

Alembic itself is synchronous (`psycopg`). Callers that already hold an event
loop (FastAPI lifespan) must wrap `run_upgrade_head` in `asyncio.to_thread`.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from backend.app.config import settings

logger = logging.getLogger("arlo.db.migrate")

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ALEMBIC_INI = _REPO_ROOT / "backend" / "alembic.ini"


def run_upgrade_head() -> None:
    """Apply all pending revisions (`alembic upgrade head`). Idempotent."""
    from alembic import command
    from alembic.config import Config

    os.environ["DATABASE_URL"] = settings.database_url
    config = Config(str(_ALEMBIC_INI))
    logger.info("alembic upgrade head ini=%s", _ALEMBIC_INI)
    command.upgrade(config, "head")
