from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class MenuCb(CallbackData, prefix="menu"):
    section: str


class OrderCb(CallbackData, prefix="order"):
    action: str
    order_id: int


class CityPickCb(CallbackData, prefix="city"):
    city_id: int


class UserCb(CallbackData, prefix="user"):
    action: str
    user_id: int
