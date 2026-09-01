"""`ARLO-<n>` id allocation (SAD §1 correspondence rule; Open Question 7: numeric ids).

Backed by a Postgres sequence (`arlo_instance_seq`, created in the first Alembic
revision) so concurrent spawns never collide, without holding a row lock.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.ids import format_arlo_id


async def next_arlo_id(session: AsyncSession) -> str:
    result = await session.execute(text("SELECT nextval('arlo_instance_seq')"))
    n = result.scalar_one()
    return format_arlo_id(int(n))
