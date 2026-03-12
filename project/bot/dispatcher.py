from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from project.bot.handlers.admin import router as admin_router
from project.bot.handlers.cleaner import router as cleaner_router
from project.bot.handlers.common import router as common_router
from project.bot.handlers.manager import router as manager_router
from project.bot.middlewares.db import DbSessionMiddleware
from project.bot.middlewares.redis import RedisMiddleware
from project.bot.middlewares.user import UserMiddleware
from project.config.settings import Settings
from project.database.engine import build_engine, build_session_factory


def build_dispatcher(settings: Settings) -> tuple[Dispatcher, Bot]:
    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    storage = RedisStorage(redis=redis)

    dp = Dispatcher(storage=storage)

    engine = build_engine(settings.database_url)
    session_factory = build_session_factory(engine)

    dp.update.middleware(DbSessionMiddleware(session_factory=session_factory))
    dp.update.middleware(RedisMiddleware(redis=redis))
    dp.update.middleware(UserMiddleware(admin_tg_id=settings.admin_tg_id, redis=redis))

    dp.include_router(common_router)
    dp.include_router(admin_router)
    dp.include_router(manager_router)
    dp.include_router(cleaner_router)

    return dp, bot
