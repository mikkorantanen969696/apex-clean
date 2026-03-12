from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from project.bot.keyboards.callbacks import MenuCb, OrderCb
from project.bot.keyboards.inline import cleaner_menu, order_cleaner_actions
from project.bot.states.photos import PhotoUploadStates
from project.database.models import PhotoKind, UserRole
from project.database.models import CleanerProfile
from project.services.order import OrderAlreadyTaken, OrderService
from project.services.roles import require_role
from project.services.storage import StorageService

router = Router(name="cleaner")


@router.callback_query(MenuCb.filter(F.section == "cleaner"))
@require_role(UserRole.CLEANER)
async def cleaner_panel(cb: CallbackQuery) -> None:
    await cb.message.edit_text("Меню клинера:", reply_markup=cleaner_menu())
    await cb.answer()


@router.callback_query(MenuCb.filter(F.section == "cleaner_active"))
@require_role(UserRole.CLEANER)
async def cleaner_active(cb: CallbackQuery, session: AsyncSession, user) -> None:
    service = OrderService(session=session)
    orders = await service.list_cleaner_active(cleaner_id=user.id)
    if not orders:
        await cb.message.edit_text("Нет активных заказов.", reply_markup=cleaner_menu())
        await cb.answer()
        return
    lines = ["<b>Активные заказы</b>:"]
    for o in orders[:15]:
        lines.append(f"#{o.id} — {o.status} — {o.address}")
    await cb.message.edit_text("\n".join(lines), reply_markup=cleaner_menu())
    await cb.answer()


@router.callback_query(MenuCb.filter(F.section == "cleaner_payout"))
@require_role(UserRole.CLEANER)
async def cleaner_payout(cb: CallbackQuery) -> None:
    await cb.message.edit_text(
        "Отправьте реквизиты командой:\n<code>/payout_details карта: 0000 0000 0000 0000</code>",
        reply_markup=cleaner_menu(),
    )
    await cb.answer()


@router.message(F.text.startswith("/payout_details "))
@require_role(UserRole.CLEANER)
async def payout_details(message: Message, session: AsyncSession, user) -> None:
    details = message.text.replace("/payout_details", "", 1).strip()
    if not details:
        await message.answer("Формат: /payout_details карта: 0000 0000 0000 0000")
        return
    profile = await session.get(CleanerProfile, user.id)
    if profile is None:
        profile = CleanerProfile(user_id=user.id, payout_details={})
        session.add(profile)
    profile.payout_details = {"raw": details}
    await session.commit()
    await message.answer("Реквизиты сохранены.")


@router.callback_query(OrderCb.filter(F.action == "accept"))
@require_role(UserRole.CLEANER)
async def accept_order(cb: CallbackQuery, callback_data: OrderCb, session: AsyncSession, user, bot) -> None:
    service = OrderService(session=session, bot=bot)
    try:
        order = await service.accept_order(order_id=callback_data.order_id, cleaner=user)
    except OrderAlreadyTaken:
        await cb.answer("Заказ уже взят.", show_alert=True)
        return
    except PermissionError:
        await cb.answer("Этот город вам недоступен.", show_alert=True)
        return

    await session.commit()
    await cb.answer("Вы взяли заказ!")
    await cb.message.edit_reply_markup(reply_markup=None)
    await bot.send_message(user.tg_id, f"Заказ #{order.id} принят.", reply_markup=order_cleaner_actions(order))


@router.callback_query(OrderCb.filter(F.action == "start"))
@require_role(UserRole.CLEANER)
async def start_work(cb: CallbackQuery, callback_data: OrderCb, session: AsyncSession, user) -> None:
    service = OrderService(session=session)
    await service.set_in_progress(order_id=callback_data.order_id, cleaner=user)
    await session.commit()
    await cb.answer("Статус: IN_PROGRESS")


@router.callback_query(OrderCb.filter(F.action == "upload_before"))
@require_role(UserRole.CLEANER)
async def start_before(cb: CallbackQuery, callback_data: OrderCb, state: FSMContext) -> None:
    await state.set_state(PhotoUploadStates.before_photos)
    await state.update_data(order_id=callback_data.order_id, photos=[])
    await cb.message.answer("Отправьте минимум 2 фото ДО. Когда закончите — отправьте /done")
    await cb.answer()


@router.callback_query(OrderCb.filter(F.action == "upload_after"))
@require_role(UserRole.CLEANER)
async def start_after(cb: CallbackQuery, callback_data: OrderCb, state: FSMContext) -> None:
    await state.set_state(PhotoUploadStates.after_photos)
    await state.update_data(order_id=callback_data.order_id, photos=[])
    await cb.message.answer("Отправьте минимум 2 фото ПОСЛЕ. Когда закончите — отправьте /done")
    await cb.answer()


@router.message(PhotoUploadStates.before_photos, F.photo)
@router.message(PhotoUploadStates.after_photos, F.photo)
@require_role(UserRole.CLEANER)
async def collect_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    photos: list[str] = list(data.get("photos", []))
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    await message.answer(f"Принято фото ({len(photos)}).")


@router.message(F.text == "/done", PhotoUploadStates.before_photos)
@require_role(UserRole.CLEANER)
async def done_before(message: Message, state: FSMContext, session: AsyncSession, user, bot) -> None:
    data = await state.get_data()
    photos: list[str] = list(data.get("photos", []))
    if len(photos) < 2:
        await message.answer("Нужно минимум 2 фото ДО.")
        return
    storage = StorageService(bot=bot)
    service = OrderService(session=session, storage=storage)
    await service.save_photos(order_id=int(data["order_id"]), cleaner=user, kind=PhotoKind.BEFORE, file_ids=photos)
    await session.commit()
    await state.clear()
    await message.answer("Фото ДО загружены.")


@router.message(F.text == "/done", PhotoUploadStates.after_photos)
@require_role(UserRole.CLEANER)
async def done_after(message: Message, state: FSMContext, session: AsyncSession, user, bot) -> None:
    data = await state.get_data()
    photos: list[str] = list(data.get("photos", []))
    if len(photos) < 2:
        await message.answer("Нужно минимум 2 фото ПОСЛЕ.")
        return
    storage = StorageService(bot=bot)
    service = OrderService(session=session, storage=storage)
    await service.save_photos(order_id=int(data["order_id"]), cleaner=user, kind=PhotoKind.AFTER, file_ids=photos)
    await session.commit()
    await state.clear()
    await message.answer("Фото ПОСЛЕ загружены.")


@router.callback_query(OrderCb.filter(F.action == "complete"))
@require_role(UserRole.CLEANER)
async def complete(cb: CallbackQuery, callback_data: OrderCb, session: AsyncSession, user) -> None:
    service = OrderService(session=session)
    await service.complete_order(order_id=callback_data.order_id, cleaner=user)
    await session.commit()
    await cb.answer("Заказ завершен.")
