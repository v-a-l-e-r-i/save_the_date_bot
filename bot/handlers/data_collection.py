from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import TEXTS
from bot.db import get_guest_by_chat_id, Status
from bot.keyboards import share_phone_kb, remove_kb, change_date_kb
from bot.states import GuestForm
from bot.utils import is_valid_full_name, normalize_phone

router = Router(name="data_collection")


@router.message(GuestForm.waiting_name)
async def on_name(message: Message, state: FSMContext, session: AsyncSession):
    name = message.text.strip()
    if not is_valid_full_name(name):
        await message.answer(TEXTS["ask_name_invalid"])
        return

    guest = await get_guest_by_chat_id(session, message.chat.id)
    guest.full_name = name
    await session.commit()

    await message.answer(TEXTS["ask_phone"], reply_markup=share_phone_kb())
    await state.set_state(GuestForm.waiting_phone)


async def _save_phone(message: Message, state: FSMContext, session: AsyncSession, raw_phone: str):
    phone = normalize_phone(raw_phone)
    if phone is None:
        await message.answer(TEXTS["ask_phone_invalid"], reply_markup=share_phone_kb())
        return

    guest = await get_guest_by_chat_id(session, message.chat.id)
    guest.phone = phone
    await session.commit()

    await message.answer(TEXTS["ask_company"], reply_markup=remove_kb())
    await state.set_state(GuestForm.waiting_company)


@router.message(GuestForm.waiting_phone, F.contact)
async def on_phone_contact(message: Message, state: FSMContext, session: AsyncSession):
    await _save_phone(message, state, session, message.contact.phone_number)


@router.message(GuestForm.waiting_phone, F.text)
async def on_phone_text(message: Message, state: FSMContext, session: AsyncSession):
    await _save_phone(message, state, session, message.text)


@router.message(GuestForm.waiting_company)
async def on_company(message: Message, state: FSMContext, session: AsyncSession):
    guest = await get_guest_by_chat_id(session, message.chat.id)
    guest.company = message.text.strip()
    await session.commit()

    await message.answer(TEXTS["ask_position"])
    await state.set_state(GuestForm.waiting_position)


@router.message(GuestForm.waiting_position)
async def on_position(message: Message, state: FSMContext, session: AsyncSession):
    guest = await get_guest_by_chat_id(session, message.chat.id)
    guest.position = message.text.strip()
    guest.status = Status.CONFIRMED.value
    await session.commit()

    await message.answer(TEXTS["data_saved"], reply_markup=change_date_kb())
    await state.clear()