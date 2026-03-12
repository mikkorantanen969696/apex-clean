from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from project.database.crud import UserRepository


class UserMiddleware(BaseMiddleware):
    def __init__(self, admin_tg_id: int, redis: Redis):
        self.admin_tg_id = admin_tg_id
        self.redis = redis

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        session: AsyncSession = data["session"]
        tg_user = getattr(event, "from_user", None)
        if tg_user is not None:
            repo = UserRepository(session)
            user = await repo.get_by_tg_id(tg_user.id)
            data["user"] = user
            data["tg_user"] = tg_user
        return await handler(event, data)
