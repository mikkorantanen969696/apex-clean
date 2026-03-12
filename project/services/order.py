from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from project.bot.keyboards.inline import order_accept_keyboard
from project.config.settings import Settings
from project.database.crud import CityRepository, CityTopicRepository, CleanerCityRepository, OrderRepository
from project.database.models import Order, OrderPhoto, OrderStatus, PhotoKind, User
from project.services.audit import AuditService
from project.services.storage import StorageService


class OrderAlreadyTaken(Exception):
    pass


@dataclass(slots=True)
class OrderService:
    session: AsyncSession
    bot: Bot | None = None
    storage: StorageService | None = None

    async def create_and_publish(
        self,
        manager: User,
        city_id: int,
        address: str,
        cleaning_type: str,
        scheduled_time: datetime,
        description: str,
        price: float,
        client_name: str,
        client_phone: str,
    ) -> Order:
        repo = OrderRepository(self.session)
        order = await repo.create_order(
            city_id=city_id,
            address=address,
            cleaning_type=cleaning_type,
            scheduled_time=scheduled_time,
            description=description,
            price=price,
            client_name=client_name,
            client_phone=client_phone,
            manager_id=manager.id,
        )

        if self.bot is None:
            await AuditService(self.session).log(
                actor_user_id=manager.id,
                action="order_created",
                entity_type="order",
                entity_id=str(order.id),
                metadata={"city_id": city_id},
            )
            return order

        settings = Settings()
        topic_repo = CityTopicRepository(self.session)
        topic = await topic_repo.get_for_city(city_id=city_id, supergroup_id=settings.supergroup_id)
        if topic is None:
            raise ValueError("City topic not configured. Use admin to set thread_id for this city.")

        city_repo = CityRepository(self.session)
        city = await city_repo.get(city_id)

        text = (
            f"<b>Заявка #{order.id}</b>\n"
            f"Город: {city.name}\n"
            f"Адрес: {address}\n"
            f"Время: {scheduled_time:%Y-%m-%d %H:%M}\n"
            f"Тип: {cleaning_type}\n"
            f"Цена: {price}\n"
            f"Описание: {description}\n"
        )

        msg = await self.bot.send_message(
            chat_id=settings.supergroup_id,
            message_thread_id=topic.thread_id,
            text=text,
            reply_markup=order_accept_keyboard(order.id),
        )

        order.status = OrderStatus.PUBLISHED
        order.published_supergroup_id = settings.supergroup_id
        order.published_thread_id = topic.thread_id
        order.published_message_id = msg.message_id
        await self.session.flush()
        await AuditService(self.session).log(
            actor_user_id=manager.id,
            action="order_published",
            entity_type="order",
            entity_id=str(order.id),
            metadata={"supergroup_id": settings.supergroup_id, "thread_id": topic.thread_id},
        )
        return order

    async def list_manager_orders(self, manager_id: int) -> list[Order]:
        repo = OrderRepository(self.session)
        return await repo.list_for_manager(manager_id)

    async def list_cleaner_active(self, cleaner_id: int, limit: int = 20) -> list[Order]:
        res = await self.session.execute(
            select(Order)
            .where(
                Order.cleaner_id == cleaner_id,
                Order.status.not_in([OrderStatus.COMPLETED, OrderStatus.CANCELLED]),
            )
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        return list(res.scalars().all())

    async def accept_order(self, order_id: int, cleaner: User) -> Order:
        res = await self.session.execute(
            select(Order)
            .options(selectinload(Order.manager))
            .where(Order.id == order_id)
            .with_for_update()
        )
        order = res.scalar_one()
        if order.status != OrderStatus.PUBLISHED or order.cleaner_id is not None:
            raise OrderAlreadyTaken

        cc_repo = CleanerCityRepository(self.session)
        if not await cc_repo.is_allowed(cleaner_id=cleaner.id, city_id=order.city_id):
            raise PermissionError("Cleaner is not allowed for this city")

        order.cleaner_id = cleaner.id
        order.status = OrderStatus.ACCEPTED
        await self.session.flush()
        await AuditService(self.session).log(
            actor_user_id=cleaner.id,
            action="order_accepted",
            entity_type="order",
            entity_id=str(order.id),
            metadata={},
        )

        if self.bot and cleaner.tg_id:
            await self.bot.send_message(
                chat_id=cleaner.tg_id,
                text=f"Контакты менеджера по заказу #{order.id}: @{order.manager.username or '—'}",
            )
        if self.bot and order.manager.tg_id:
            await self.bot.send_message(
                chat_id=order.manager.tg_id,
                text=f"Заказ #{order.id} взят клинером: @{cleaner.username or '—'}",
            )

        return order

    async def set_in_progress(self, order_id: int, cleaner: User) -> None:
        order = await self._require_order_for_cleaner(order_id, cleaner)
        order.status = OrderStatus.IN_PROGRESS
        await self.session.flush()

    async def save_photos(self, order_id: int, cleaner: User, kind: PhotoKind, file_ids: list[str]) -> None:
        order = await self._require_order_for_cleaner(order_id, cleaner)
        if self.storage is None:
            raise RuntimeError("StorageService is required")

        saved_paths = await self.storage.save_telegram_photos(order_id=order.id, kind=kind.value, file_ids=file_ids)
        for file_id, path in zip(file_ids, saved_paths, strict=True):
            self.session.add(
                OrderPhoto(
                    order_id=order.id,
                    uploader_user_id=cleaner.id,
                    kind=kind,
                    file_path=path,
                    telegram_file_id=file_id,
                )
            )

        if kind == PhotoKind.BEFORE:
            order.status = OrderStatus.BEFORE_PHOTOS_UPLOADED
        else:
            order.status = OrderStatus.AFTER_PHOTOS_UPLOADED
        await self.session.flush()
        await AuditService(self.session).log(
            actor_user_id=cleaner.id,
            action="order_photos_uploaded",
            entity_type="order",
            entity_id=str(order.id),
            metadata={"kind": kind.value, "count": len(file_ids)},
        )

    async def complete_order(self, order_id: int, cleaner: User) -> None:
        order = await self._require_order_for_cleaner(order_id, cleaner)
        order.status = OrderStatus.COMPLETED
        await self.session.flush()
        await AuditService(self.session).log(
            actor_user_id=cleaner.id,
            action="order_completed",
            entity_type="order",
            entity_id=str(order.id),
            metadata={},
        )

    async def _require_order_for_cleaner(self, order_id: int, cleaner: User) -> Order:
        res = await self.session.execute(select(Order).where(Order.id == order_id))
        order = res.scalar_one()
        if order.cleaner_id != cleaner.id:
            raise PermissionError("Not your order")
        return order
