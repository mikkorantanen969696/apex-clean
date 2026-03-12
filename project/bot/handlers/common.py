from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from project.bot.keyboards.inline import main_menu
from project.bot.states.auth import AuthStates
from project.services.auth import AuthService, AuthTooManyAttempts

router = Router(name="common")


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, session: AsyncSession, redis: Redis, user=None) -> None:
    if user is None:
        await state.set_state(AuthStates.waiting_password)
        await message.answer(
            "Привет! Для входа введи пароль, выданный администратором.\n\n"
            "Если пароля нет — попроси его у администратора."
        )
        return

    await state.clear()
    await message.answer(f"Вы вошли как: <b>{user.role}</b>\nВыберите раздел:", reply_markup=main_menu())


@router.message(AuthStates.waiting_password)
async def auth_by_password(message: Message, state: FSMContext, session: AsyncSession, redis: Redis) -> None:
    if not message.text:
        await message.answer("Введите пароль текстом.")
        return
    service = AuthService(session=session, redis=redis)
    try:
        bound = await service.bind_by_password(
            tg_id=message.from_user.id,
            username=message.from_user.username,
            password=message.text.strip(),
        )
    except AuthTooManyAttempts:
        await message.answer("Слишком много попыток. Попробуйте позже.")
        return

    if not bound:
        await message.answer("Неверный пароль. Попробуйте еще раз.")
        return

    await session.commit()
    await state.clear()
    await message.answer(f"Успешно. Роль: <b>{bound.role}</b>", reply_markup=main_menu())
