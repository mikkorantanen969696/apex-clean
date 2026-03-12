from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from project.database.models import ActionLog


@dataclass(slots=True)
class AuditService:
    session: AsyncSession

    async def log(self, actor_user_id: int | None, action: str, entity_type: str, entity_id: str, metadata: dict) -> None:
        self.session.add(
            ActionLog(
                actor_user_id=actor_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                metadata=metadata,
            )
        )
        await self.session.flush()
