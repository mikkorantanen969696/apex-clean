from __future__ import annotations

import secrets
from datetime import datetime

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from project.database.models import City, CityTopic, CleanerCity, Order, OrderStatus, User, UserRole


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def generate_password(length: int = 10) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_tg_id(self, tg_id: int) -> User | None:
        res = await self.session.execute(select(User).where(User.tg_id == tg_id))
        return res.scalar_one_or_none()

    async def list_unbound_active(self) -> list[User]:
        res = await self.session.execute(select(User).where(User.tg_id.is_(None), User.is_active.is_(True)))
        return list(res.scalars().all())

    async def create_user(self, full_name: str, role: UserRole, password: str, username: str | None = None) -> User:
        user = User(
            tg_id=None,
            username=username,
            full_name=full_name,
            role=role,
            password_hash=hash_password(password),
            is_active=True,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def bind_telegram(self, user: User, tg_id: int, username: str | None) -> None:
        user.tg_id = tg_id
        user.username = username
        user.last_login_at = datetime.utcnow()
        await self.session.flush()

    async def deactivate_user(self, user_id: int) -> None:
        res = await self.session.execute(select(User).where(User.id == user_id))
        user = res.scalar_one()
        user.is_active = False
        await self.session.flush()

    async def list_by_role(self, role: UserRole) -> list[User]:
        res = await self.session.execute(select(User).where(User.role == role, User.is_active.is_(True)))
        return list(res.scalars().all())


class CityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self) -> list[City]:
        res = await self.session.execute(select(City).order_by(City.name.asc()))
        return list(res.scalars().all())

    async def get_or_create(self, name: str) -> City:
        res = await self.session.execute(select(City).where(City.name == name))
        city = res.scalar_one_or_none()
        if city:
            return city
        city = City(name=name)
        self.session.add(city)
        await self.session.flush()
        return city

    async def get(self, city_id: int) -> City:
        res = await self.session.execute(select(City).where(City.id == city_id))
        return res.scalar_one()


class CityTopicRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_for_city(self, city_id: int, supergroup_id: int) -> CityTopic | None:
        res = await self.session.execute(
            select(CityTopic).where(CityTopic.city_id == city_id, CityTopic.supergroup_id == supergroup_id)
        )
        return res.scalar_one_or_none()

    async def upsert(self, city_id: int, supergroup_id: int, thread_id: int) -> CityTopic:
        existing = await self.get_for_city(city_id=city_id, supergroup_id=supergroup_id)
        if existing:
            existing.thread_id = thread_id
            await self.session.flush()
            return existing
        topic = CityTopic(city_id=city_id, supergroup_id=supergroup_id, thread_id=thread_id)
        self.session.add(topic)
        await self.session.flush()
        return topic


class CleanerCityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def set_allowed_cities(self, cleaner_id: int, city_ids: list[int]) -> None:
        res = await self.session.execute(select(CleanerCity).where(CleanerCity.cleaner_id == cleaner_id))
        for row in res.scalars().all():
            await self.session.delete(row)
        for city_id in city_ids:
            self.session.add(CleanerCity(cleaner_id=cleaner_id, city_id=city_id))
        await self.session.flush()

    async def is_allowed(self, cleaner_id: int, city_id: int) -> bool:
        res = await self.session.execute(
            select(CleanerCity).where(CleanerCity.cleaner_id == cleaner_id, CleanerCity.city_id == city_id)
        )
        return res.scalar_one_or_none() is not None


class OrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_order(self, **kwargs) -> Order:
        order = Order(status=OrderStatus.NEW, **kwargs)
        self.session.add(order)
        await self.session.flush()
        return order

    async def get(self, order_id: int) -> Order:
        res = await self.session.execute(select(Order).where(Order.id == order_id))
        return res.scalar_one()

    async def list_for_manager(self, manager_id: int, limit: int = 20) -> list[Order]:
        res = await self.session.execute(
            select(Order).where(Order.manager_id == manager_id).order_by(Order.created_at.desc()).limit(limit)
        )
        return list(res.scalars().all())
