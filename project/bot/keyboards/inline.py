from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from project.bot.keyboards.callbacks import CityPickCb, MenuCb, OrderCb, UserCb
from project.database.models import City, Order


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Админ-панель", callback_data=MenuCb(section="admin").pack())],
            [InlineKeyboardButton(text="Меню менеджера", callback_data=MenuCb(section="manager").pack())],
            [InlineKeyboardButton(text="Меню клинера", callback_data=MenuCb(section="cleaner").pack())],
        ]
    )


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Пользователи", callback_data=MenuCb(section="admin_users").pack())],
            [InlineKeyboardButton(text="Города/темы", callback_data=MenuCb(section="admin_cities").pack())],
        ]
    )


def manager_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Создать заявку", callback_data=MenuCb(section="manager_create").pack())],
            [InlineKeyboardButton(text="Мои заявки", callback_data=MenuCb(section="manager_orders").pack())],
        ]
    )


def cleaner_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Мои активные заказы", callback_data=MenuCb(section="cleaner_active").pack())],
            [InlineKeyboardButton(text="Реквизиты для выплаты", callback_data=MenuCb(section="cleaner_payout").pack())],
        ]
    )


def cities_keyboard(cities: list[City]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for city in cities:
        rows.append([InlineKeyboardButton(text=city.name, callback_data=CityPickCb(city_id=city.id).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def order_accept_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Взять заказ", callback_data=OrderCb(action="accept", order_id=order_id).pack())]
        ]
    )


def order_cleaner_actions(order: Order) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начал работу", callback_data=OrderCb(action="start", order_id=order.id).pack())],
            [
                InlineKeyboardButton(
                    text="Загрузить фото ДО", callback_data=OrderCb(action="upload_before", order_id=order.id).pack()
                )
            ],
            [
                InlineKeyboardButton(
                    text="Загрузить фото ПОСЛЕ", callback_data=OrderCb(action="upload_after", order_id=order.id).pack()
                )
            ],
            [InlineKeyboardButton(text="Завершить", callback_data=OrderCb(action="complete", order_id=order.id).pack())],
        ]
    )


def user_list_keyboard(users: list, action: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for u in users:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{u.full_name} ({u.id})", callback_data=UserCb(action=action, user_id=u.id).pack()
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
