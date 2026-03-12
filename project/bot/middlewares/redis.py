from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from redis.asyncio import Redis


class RedisMiddleware(BaseMiddleware):
    def __init__(self, redis: Redis):
        self.redis = redis

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        data["redis"] = self.redis
        return await handler(event, data)
