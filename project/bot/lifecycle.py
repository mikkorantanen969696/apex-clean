from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from project.config.settings import Settings
from project.database.crud import UserRepository, generate_password
from project.database.engine import build_engine, build_session_factory
from project.database.models import UserRole

logger = logging.getLogger(__name__)


async def on_startup(settings: Settings) -> None:
    engine = build_engine(settings.database_url)
    session_factory = build_session_factory(engine)

    async with session_factory() as session:  # type: AsyncSession
        repo = UserRepository(session)
        admin = await repo.get_by_tg_id(settings.admin_tg_id)
        if admin:
            return

        password = generate_password(12)
        created = await repo.create_user(full_name="Admin", role=UserRole.ADMIN, password=password, username=None)
        await repo.bind_telegram(created, settings.admin_tg_id, username=None)
        await session.commit()
        logger.info("Bootstrapped ADMIN user for tg_id=%s", settings.admin_tg_id)
