from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    CLEANER = "CLEANER"


class OrderStatus(str, enum.Enum):
    NEW = "NEW"
    PUBLISHED = "PUBLISHED"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    BEFORE_PHOTOS_UPLOADED = "BEFORE_PHOTOS_UPLOADED"
    AFTER_PHOTOS_UPLOADED = "AFTER_PHOTOS_UPLOADED"
    COMPLETED = "COMPLETED"
    PAID_TO_CLEANER = "PAID_TO_CLEANER"
    CANCELLED = "CANCELLED"


class TransactionType(str, enum.Enum):
    INCOME = "income"
    PAYOUT = "payout"


class TransactionStatus(str, enum.Enum):
    NEW = "new"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class PhotoKind(str, enum.Enum):
    BEFORE = "before"
    AFTER = "after"


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)


class CityTopic(Base):
    __tablename__ = "city_topics"
    __table_args__ = (UniqueConstraint("supergroup_id", "thread_id", name="uq_city_topics_thread"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"), nullable=False)
    supergroup_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    thread_id: Mapped[int] = mapped_column(Integer, nullable=False)

    city: Mapped[City] = relationship()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    cleaner_profile: Mapped["CleanerProfile | None"] = relationship(back_populates="user")


class CleanerProfile(Base):
    __tablename__ = "cleaner_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    payout_details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    rating: Mapped[float] = mapped_column(Numeric(3, 2), default=5.0, nullable=False)

    user: Mapped[User] = relationship(back_populates="cleaner_profile")


class CleanerCity(Base):
    __tablename__ = "cleaner_cities"
    __table_args__ = (UniqueConstraint("cleaner_id", "city_id", name="uq_cleaner_cities"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cleaner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"), nullable=False)

    cleaner: Mapped[User] = relationship(foreign_keys=[cleaner_id])
    city: Mapped[City] = relationship()


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    client_name: Mapped[str] = mapped_column(String(120), nullable=False)
    client_phone: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    cleaning_type: Mapped[str] = mapped_column(String(120), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    manager_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    cleaner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus, name="order_status"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    published_supergroup_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    published_thread_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    published_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    city: Mapped[City] = relationship()
    manager: Mapped[User] = relationship(foreign_keys=[manager_id])
    cleaner: Mapped[User | None] = relationship(foreign_keys=[cleaner_id])
    photos: Mapped[list["OrderPhoto"]] = relationship(back_populates="order")


class OrderPhoto(Base):
    __tablename__ = "order_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    uploader_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    kind: Mapped[PhotoKind] = mapped_column(Enum(PhotoKind, name="photo_kind"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    telegram_file_id: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    order: Mapped[Order] = relationship(back_populates="photos")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType, name="transaction_type"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, name="transaction_status"), default=TransactionStatus.NEW, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ActionLog(Base):
    __tablename__ = "action_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(80), nullable=False)
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ClientBlacklist(Base):
    __tablename__ = "client_blacklist"
    __table_args__ = (UniqueConstraint("phone", name="uq_client_blacklist_phone"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
