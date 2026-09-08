from datetime import datetime, date as date_cls

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import TEXTS, DATE_KEY_TO_ISO
from bot.db import get_guest_by_chat_id, Status
from bot.keyboards import date_selection_kb, change_date_kb, confirm_prefilled_kb
from bot.states import GuestForm
from bot.utils import smart_edit

router = Router(name="date_selection")


@router.callback_query(F.data.startswith("date:"))
async def on_date_chosen(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    key = callback.data.split(":", 1)[1]
    guest = await get_guest_by_chat_id(session, callback.message.chat.id)
    if guest is None:
        await callback.answer()
        return

    iso_date = DATE_KEY_TO_ISO.get(key)
    guest.chosen_date = date_cls.fromisoformat(iso_date) if iso_date else None
    guest.add_date_change(iso_date)
    if guest.first_response_at is None:
        guest.first_response_at = datetime.utcnow()

    confirm_text = TEXTS["confirmation"][key]

    if guest.prefilled and (guest.full_name or guest.phone or guest.company):
        guest.status = Status.PENDING.value
        await session.commit()
        text = confirm_text + "\n\n" + TEXTS["confirm_prefilled"].format(
            name=guest.full_name or "—", phone=guest.phone or "—", company=guest.company or "—"
        )
        await smart_edit(callback.message, text, reply_markup=confirm_prefilled_kb())
        await callback.answer()
        return

    if guest.full_name and guest.phone and guest.company:
        # already have everything (e.g. user is re-picking a date after already onboarding)
        guest.status = Status.CONFIRMED.value
        await session.commit()
        await smart_edit(callback.message, confirm_text, reply_markup=change_date_kb())
        await callback.answer()
        return

    guest.status = Status.PENDING.value
    await session.commit()
    await smart_edit(callback.message, confirm_text)
    await callback.message.answer(TEXTS["ask_name"])
    await state.set_state(GuestForm.waiting_name)
    await callback.answer()


@router.callback_query(F.data == "change_date")
async def on_change_date(callback: CallbackQuery):
    await callback.message.answer(TEXTS["change_date_prompt"], reply_markup=date_selection_kb())
    await callback.answer()


@router.callback_query(F.data == "prefill:yes")
async def on_prefill_confirmed(callback: CallbackQuery, session: AsyncSession):
    guest = await get_guest_by_chat_id(session, callback.message.chat.id)
    if guest:
        guest.status = Status.CONFIRMED.value
        await session.commit()
    await smart_edit(callback.message, TEXTS["data_saved"], reply_markup=change_date_kb())
    await callback.answer()


@router.callback_query(F.data == "prefill:edit")
async def on_prefill_edit(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(TEXTS["ask_name"])
    await state.set_state(GuestForm.waiting_name)
    await callback.answer()