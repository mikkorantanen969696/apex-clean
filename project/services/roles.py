from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from aiogram.types import CallbackQuery, Message

from project.database.models import UserRole


def require_role(role: UserRole):
    def decorator(handler: Callable[..., Awaitable[Any]]):
        @wraps(handler)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("user")
            if user is None or user.role != role:
                for a in args:
                    if isinstance(a, CallbackQuery):
                        await a.answer("Недостаточно прав.", show_alert=True)
                        return None
                    if isinstance(a, Message):
                        await a.answer("Недостаточно прав.")
                        return None
                return None
            return await handler(*args, **kwargs)

        return wrapper

    return decorator
