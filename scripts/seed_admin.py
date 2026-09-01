#!/usr/bin/env python3
"""Provision the local admin user (SAD §8). Dev/capstone only.

Usage (from repo root, with DATABASE_URL in `.env`):

    python scripts/seed_admin.py

Reads `ARLO_ADMIN_USERNAME` / `ARLO_ADMIN_PASSWORD`. Password is required;
never printed. Idempotent: existing username is updated to the new hash.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from backend.app.config import settings
from backend.app.db.migrate import run_upgrade_head
from backend.app.db.session import session_scope
from backend.app.services.users import upsert_local_user


async def seed_admin(*, username: str, password: str) -> str:
    if not username or not password:
        raise SystemExit("ARLO_ADMIN_USERNAME and ARLO_ADMIN_PASSWORD must both be set")

    async with session_scope() as session:
        user = await upsert_local_user(session, username=username, password=password)
        return str(user.id)


def main() -> None:
    run_upgrade_head()
    user_id = asyncio.run(
        seed_admin(username=settings.arlo_admin_username, password=settings.arlo_admin_password)
    )
    print(f"admin user ready username={settings.arlo_admin_username} id={user_id}")


if __name__ == "__main__":
    main()
