from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import timedelta

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from project.database.crud import UserRepository, verify_password
from project.database.models import User
from project.services.audit import AuditService


class AuthTooManyAttempts(Exception):
    pass


@dataclass(slots=True)
class AuthService:
    session: AsyncSession
    redis: Redis

    async def _check_rate_limit(self, tg_id: int) -> None:
        key = f"auth:attempts:{tg_id}"
        attempts = await self.redis.incr(key)
        if attempts == 1:
            await self.redis.expire(key, int(timedelta(minutes=5).total_seconds()))
        if attempts > 10:
            raise AuthTooManyAttempts

    async def bind_by_password(self, tg_id: int, username: str | None, password: str) -> User | None:
        await self._check_rate_limit(tg_id)
        repo = UserRepository(self.session)
        candidates = await repo.list_unbound_active()
        for u in candidates:
            if verify_password(password, u.password_hash):
                await repo.bind_telegram(u, tg_id=tg_id, username=username)
                token = secrets.token_urlsafe(32)
                await self.redis.setex(f"auth:session:{tg_id}", int(timedelta(days=30).total_seconds()), token)
                await AuditService(self.session).log(
                    actor_user_id=u.id,
                    action="auth_bound",
                    entity_type="user",
                    entity_id=str(u.id),
                    metadata={"tg_id": tg_id, "username": username or ""},
                )
                return u
        return None
