from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from project.bot.keyboards.callbacks import MenuCb, UserCb
from project.bot.keyboards.inline import admin_menu, user_list_keyboard
from project.database.crud import (
    CityRepository,
    CityTopicRepository,
    CleanerCityRepository,
    UserRepository,
    generate_password,
)
from project.database.models import CityTopic
from project.database.models import UserRole
from project.services.roles import require_role

router = Router(name="admin")


@router.callback_query(MenuCb.filter(F.section == "admin"))
@require_role(UserRole.ADMIN)
async def admin_panel(cb: CallbackQuery) -> None:
    await cb.message.edit_text("Админ-панель:", reply_markup=admin_menu())
    await cb.answer()


@router.callback_query(MenuCb.filter(F.section == "admin_cities"))
@require_role(UserRole.ADMIN)
async def admin_cities(cb: CallbackQuery, session: AsyncSession) -> None:
    res = await session.execute(select(CityTopic).options(selectinload(CityTopic.city)))
    topics = list(res.scalars().all())
    if not topics:
        await cb.message.edit_text(
            "Нет настроенных тем. Добавьте города и привяжите thread_id через /set_topic.",
            reply_markup=admin_menu(),
        )
        await cb.answer()
        return
    lines = ["<b>Города/темы</b>:"]
    for t in topics[:50]:
        lines.append(f"- {t.city.name}: thread_id={t.thread_id}")
    await cb.message.edit_text("\n".join(lines), reply_markup=admin_menu())
    await cb.answer()


@router.callback_query(MenuCb.filter(F.section == "admin_users"))
@require_role(UserRole.ADMIN)
async def admin_users(cb: CallbackQuery, session: AsyncSession) -> None:
    repo = UserRepository(session)
    managers = await repo.list_by_role(UserRole.MANAGER)
    cleaners = await repo.list_by_role(UserRole.CLEANER)
    text = (
        "<b>Пользователи</b>\n\n"
        f"Менеджеры: {len(managers)}\n"
        f"Клинеры: {len(cleaners)}\n\n"
        "Команды:\n"
        "<code>/add_manager ФИО</code>\n"
        "<code>/add_cleaner ФИО</code>\n"
        "<code>/del_manager</code>\n"
        "<code>/del_cleaner</code>\n"
        "<code>/add_city Москва</code>\n"
        "<code>/set_topic Москва 123</code> (thread_id)\n"
        "<code>/set_cleaner_cities 42 Москва,Казань</code>\n"
    )
    await cb.message.edit_text(text, reply_markup=admin_menu())
    await cb.answer()


@router.message(F.text.startswith("/add_manager "))
@require_role(UserRole.ADMIN)
async def add_manager(message: Message, session: AsyncSession) -> None:
    full_name = message.text.replace("/add_manager", "", 1).strip()
    if not full_name:
        await message.answer("Формат: /add_manager ФИО")
        return
    repo = UserRepository(session)
    password = generate_password()
    user = await repo.create_user(full_name=full_name, role=UserRole.MANAGER, password=password)
    await session.commit()
    await message.answer(f"Создан менеджер #{user.id}\nПароль: <code>{password}</code>")


@router.message(F.text.startswith("/add_cleaner "))
@require_role(UserRole.ADMIN)
async def add_cleaner(message: Message, session: AsyncSession) -> None:
    full_name = message.text.replace("/add_cleaner", "", 1).strip()
    if not full_name:
        await message.answer("Формат: /add_cleaner ФИО")
        return
    repo = UserRepository(session)
    password = generate_password()
    user = await repo.create_user(full_name=full_name, role=UserRole.CLEANER, password=password)
    await session.commit()
    await message.answer(f"Создан клинер #{user.id}\nПароль: <code>{password}</code>")


@router.message(F.text == "/del_manager")
@require_role(UserRole.ADMIN)
async def del_manager_list(message: Message, session: AsyncSession) -> None:
    repo = UserRepository(session)
    managers = await repo.list_by_role(UserRole.MANAGER)
    await message.answer("Выберите менеджера для деактивации:", reply_markup=user_list_keyboard(managers, "deactivate"))


@router.message(F.text == "/del_cleaner")
@require_role(UserRole.ADMIN)
async def del_cleaner_list(message: Message, session: AsyncSession) -> None:
    repo = UserRepository(session)
    cleaners = await repo.list_by_role(UserRole.CLEANER)
    await message.answer("Выберите клинера для деактивации:", reply_markup=user_list_keyboard(cleaners, "deactivate"))


@router.callback_query(UserCb.filter(F.action == "deactivate"))
@require_role(UserRole.ADMIN)
async def deactivate_user(cb: CallbackQuery, callback_data: UserCb, session: AsyncSession) -> None:
    repo = UserRepository(session)
    await repo.deactivate_user(callback_data.user_id)
    await session.commit()
    await cb.message.edit_text(f"Пользователь #{callback_data.user_id} деактивирован.")
    await cb.answer()


@router.message(F.text.startswith("/add_city "))
@require_role(UserRole.ADMIN)
async def add_city(message: Message, session: AsyncSession) -> None:
    name = message.text.replace("/add_city", "", 1).strip()
    if not name:
        await message.answer("Формат: /add_city Москва")
        return
    repo = CityRepository(session)
    city = await repo.get_or_create(name)
    await session.commit()
    await message.answer(f"Город добавлен/существует: {city.name} (id={city.id})")


@router.message(F.text.startswith("/set_topic "))
@require_role(UserRole.ADMIN)
async def set_topic(message: Message, session: AsyncSession) -> None:
    parts = message.text.split(maxsplit=2)
    if len(parts) != 3:
        await message.answer("Формат: /set_topic Москва 123 (thread_id)")
        return
    city_name = parts[1].strip()
    try:
        thread_id = int(parts[2].strip())
    except ValueError:
        await message.answer("thread_id должен быть числом.")
        return

    city_repo = CityRepository(session)
    city = await city_repo.get_or_create(city_name)
    topic_repo = CityTopicRepository(session)
    from project.config.settings import Settings

    settings = Settings()
    await topic_repo.upsert(city_id=city.id, supergroup_id=settings.supergroup_id, thread_id=thread_id)
    await session.commit()
    await message.answer(f"Тема сохранена: {city.name} -> thread_id={thread_id}")


@router.message(F.text.startswith("/set_cleaner_cities "))
@require_role(UserRole.ADMIN)
async def set_cleaner_cities(message: Message, session: AsyncSession) -> None:
    parts = message.text.split(maxsplit=2)
    if len(parts) != 3:
        await message.answer("Формат: /set_cleaner_cities 42 Москва,Казань")
        return
    try:
        cleaner_id = int(parts[1])
    except ValueError:
        await message.answer("cleaner_id должен быть числом.")
        return
    names = [p.strip() for p in parts[2].split(",") if p.strip()]
    if not names:
        await message.answer("Укажите хотя бы 1 город.")
        return

    city_repo = CityRepository(session)
    city_ids: list[int] = []
    for n in names:
        city = await city_repo.get_or_create(n)
        city_ids.append(city.id)

    cc_repo = CleanerCityRepository(session)
    await cc_repo.set_allowed_cities(cleaner_id=cleaner_id, city_ids=city_ids)
    await session.commit()
    await message.answer(f"Клинеру #{cleaner_id} назначены города: {', '.join(names)}")
