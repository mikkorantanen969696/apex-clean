from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.types.input_file import FSInputFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from project.bot.keyboards.callbacks import CityPickCb, MenuCb
from project.bot.keyboards.inline import cities_keyboard, manager_menu
from project.bot.states.order_create import OrderCreateStates
from project.database.crud import CityRepository
from project.database.models import Order
from project.database.models import UserRole
from project.services.finance import FinanceService
from project.services.order import OrderService
from project.services.pdf import PdfService
from project.services.roles import require_role
from project.utils.time import parse_datetime

router = Router(name="manager")


@router.callback_query(MenuCb.filter(F.section == "manager"))
@require_role(UserRole.MANAGER)
async def manager_panel(cb: CallbackQuery) -> None:
    await cb.message.edit_text("Меню менеджера:", reply_markup=manager_menu())
    await cb.answer()


@router.callback_query(MenuCb.filter(F.section == "manager_create"))
@require_role(UserRole.MANAGER)
async def start_create(cb: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    repo = CityRepository(session)
    cities = await repo.list()
    if not cities:
        await cb.message.edit_text("Сначала добавьте города (админ).")
        await cb.answer()
        return
    await state.set_state(OrderCreateStates.city)
    await cb.message.edit_text("Выберите город:", reply_markup=cities_keyboard(cities))
    await cb.answer()


@router.callback_query(OrderCreateStates.city, CityPickCb.filter())
@require_role(UserRole.MANAGER)
async def pick_city(cb: CallbackQuery, callback_data: CityPickCb, state: FSMContext) -> None:
    await state.update_data(city_id=callback_data.city_id)
    await state.set_state(OrderCreateStates.address)
    await cb.message.edit_text("Введите адрес:")
    await cb.answer()


@router.message(OrderCreateStates.address)
@require_role(UserRole.MANAGER)
async def set_address(message: Message, state: FSMContext) -> None:
    await state.update_data(address=message.text.strip())
    await state.set_state(OrderCreateStates.cleaning_type)
    await message.answer("Тип уборки (например: генеральная / поддерживающая / после ремонта):")


@router.message(OrderCreateStates.cleaning_type)
@require_role(UserRole.MANAGER)
async def set_cleaning_type(message: Message, state: FSMContext) -> None:
    await state.update_data(cleaning_type=message.text.strip())
    await state.set_state(OrderCreateStates.scheduled_time)
    await message.answer("Дата и время (например: 2026-03-15 14:30):")


@router.message(OrderCreateStates.scheduled_time)
@require_role(UserRole.MANAGER)
async def set_time(message: Message, state: FSMContext) -> None:
    try:
        dt = parse_datetime(message.text.strip())
    except Exception:
        await message.answer("Не удалось распознать дату/время. Пример: 2026-03-15 14:30")
        return
    await state.update_data(scheduled_time=dt)
    await state.set_state(OrderCreateStates.description)
    await message.answer("Описание заказа:")


@router.message(OrderCreateStates.description)
@require_role(UserRole.MANAGER)
async def set_desc(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await state.set_state(OrderCreateStates.price)
    await message.answer("Цена (число):")


@router.message(OrderCreateStates.price)
@require_role(UserRole.MANAGER)
async def set_price(message: Message, state: FSMContext) -> None:
    try:
        price = float(message.text.replace(",", ".").strip())
    except ValueError:
        await message.answer("Введите число, например 3500")
        return
    await state.update_data(price=price)
    await state.set_state(OrderCreateStates.client_name)
    await message.answer("Имя клиента:")


@router.message(OrderCreateStates.client_name)
@require_role(UserRole.MANAGER)
async def set_client_name(message: Message, state: FSMContext) -> None:
    await state.update_data(client_name=message.text.strip())
    await state.set_state(OrderCreateStates.client_phone)
    await message.answer("Телефон клиента:")


@router.message(OrderCreateStates.client_phone)
@require_role(UserRole.MANAGER)
async def finalize(message: Message, state: FSMContext, session: AsyncSession, user, bot) -> None:
    await state.update_data(client_phone=message.text.strip())
    data = await state.get_data()

    service = OrderService(session=session, bot=bot)
    order = await service.create_and_publish(manager=user, **data)
    await session.commit()
    await state.clear()
    await message.answer(f"Заявка создана и опубликована. ID: #{order.id}", reply_markup=manager_menu())


@router.callback_query(MenuCb.filter(F.section == "manager_orders"))
@require_role(UserRole.MANAGER)
async def list_orders(cb: CallbackQuery, session: AsyncSession, user) -> None:
    service = OrderService(session=session)
    orders = await service.list_manager_orders(manager_id=user.id)
    if not orders:
        await cb.message.edit_text("У вас нет заявок.", reply_markup=manager_menu())
        await cb.answer()
        return
    lines = ["<b>Ваши заявки</b>:"]
    for o in orders[:15]:
        lines.append(f"#{o.id} — {o.status} — {o.address} — {o.price}")
    await cb.message.edit_text("\n".join(lines), reply_markup=manager_menu())
    await cb.answer()


@router.message(F.text.startswith("/invoice "))
@require_role(UserRole.MANAGER)
async def invoice(message: Message, session: AsyncSession, user) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Формат: /invoice 123")
        return
    try:
        order_id = int(parts[1].strip())
    except ValueError:
        await message.answer("order_id должен быть числом.")
        return

    res = await session.execute(select(Order).where(Order.id == order_id, Order.manager_id == user.id))
    order = res.scalar_one_or_none()
    if order is None:
        await message.answer("Заявка не найдена или не ваша.")
        return

    from project.config.settings import Settings

    pdf_path = PdfService(Settings()).generate_invoice(order)
    await message.answer_document(FSInputFile(pdf_path), caption=f"Счет по заказу #{order.id}")


@router.message(F.text.startswith("/income "))
@require_role(UserRole.MANAGER)
async def mark_income(message: Message, session: AsyncSession, user) -> None:
    parts = message.text.split(maxsplit=2)
    if len(parts) != 3:
        await message.answer("Формат: /income 123 5000")
        return
    try:
        order_id = int(parts[1])
        amount = float(parts[2].replace(",", "."))
    except ValueError:
        await message.answer("Неверный формат чисел.")
        return
    service = FinanceService(session)
    try:
        tx = await service.record_income(order_id=order_id, manager=user, amount=amount)
    except PermissionError:
        await message.answer("Заявка не найдена или не ваша.")
        return
    await session.commit()
    await message.answer(f"Доход записан: {tx.amount} по заказу #{order_id}")


@router.message(F.text.startswith("/payout "))
@require_role(UserRole.MANAGER)
async def mark_payout(message: Message, session: AsyncSession, user) -> None:
    parts = message.text.split(maxsplit=2)
    if len(parts) != 3:
        await message.answer("Формат: /payout 123 2500")
        return
    try:
        order_id = int(parts[1])
        amount = float(parts[2].replace(",", "."))
    except ValueError:
        await message.answer("Неверный формат чисел.")
        return
    service = FinanceService(session)
    try:
        tx = await service.record_payout(order_id=order_id, manager=user, amount=amount)
    except PermissionError:
        await message.answer("Заявка не найдена или не ваша.")
        return
    await session.commit()
    await message.answer(f"Выплата клинеру записана: {tx.amount} по заказу #{order_id} (статус: PAID_TO_CLEANER)")
