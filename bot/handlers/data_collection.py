from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import TEXTS
from bot.db import get_guest_by_chat_id, Status
from bot.keyboards import share_phone_kb, remove_kb, change_date_kb
from bot.states import GuestForm

router = Router(name="data_collection")


@router.message(GuestForm.waiting_name)
async def on_name(message: Message, state: FSMContext, session: AsyncSession):
    guest = await get_guest_by_chat_id(session, message.chat.id)
    guest.full_name = message.text.strip()
    await session.commit()

    await message.answer(TEXTS["ask_phone"], reply_markup=share_phone_kb())
    await state.set_state(GuestForm.waiting_phone)


@router.message(GuestForm.waiting_phone, F.contact)
async def on_phone_contact(message: Message, state: FSMContext, session: AsyncSession):
    guest = await get_guest_by_chat_id(session, message.chat.id)
    guest.phone = message.contact.phone_number
    await session.commit()

    await message.answer(TEXTS["ask_company"], reply_markup=remove_kb())
    await state.set_state(GuestForm.waiting_company)


@router.message(GuestForm.waiting_phone, F.text)
async def on_phone_text(message: Message, state: FSMContext, session: AsyncSession):
    guest = await get_guest_by_chat_id(session, message.chat.id)
    guest.phone = message.text.strip()
    await session.commit()

    await message.answer(TEXTS["ask_company"], reply_markup=remove_kb())
    await state.set_state(GuestForm.waiting_company)


@router.message(GuestForm.waiting_company)
async def on_company(message: Message, state: FSMContext, session: AsyncSession):
    guest = await get_guest_by_chat_id(session, message.chat.id)
    guest.company = message.text.strip()
    guest.status = Status.CONFIRMED.value
    await session.commit()

    await message.answer(TEXTS["data_saved"], reply_markup=change_date_kb())
    await state.clear()
