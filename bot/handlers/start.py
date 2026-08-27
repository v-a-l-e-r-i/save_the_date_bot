from aiogram import Router, Bot, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import TEXTS
from bot.db import get_guest_by_chat_id, get_guest_by_start_code, Guest
from bot.services.messaging import send_save_the_date

router = Router(name="start")


@router.message(CommandStart(deep_link=True))
async def start_with_code(message: Message, command: CommandObject, session: AsyncSession, bot: Bot):
    code = command.args
    guest = await get_guest_by_start_code(session, code)

    if guest is None:
        await message.answer(TEXTS["not_recognized"])
        return

    # Link this Telegram account to the imported record
    guest.chat_id = message.chat.id
    guest.username = message.from_user.username
    await session.commit()

    await _greet(message, guest, session, bot)


@router.message(CommandStart())
async def start_plain(message: Message, session: AsyncSession, bot: Bot):
    guest = await get_guest_by_chat_id(session, message.chat.id)

    if guest is None:
        # Not in the pre-imported base (variant A) and no deep-link code used.
        # Create a bare record so admin can see the attempt / manually attach later.
        guest = Guest(chat_id=message.chat.id, username=message.from_user.username, source="A")
        session.add(guest)
        await session.commit()

    await _greet(message, guest, session, bot)


async def _greet(message: Message, guest: Guest, session: AsyncSession, bot: Bot):
    # Always shows the Save-the-date banner + date buttons first (spec 3.1).
    # Prefilled data (if any) is confirmed AFTER a date is picked — see date_selection.py.
    ok = await send_save_the_date(bot, guest)
    await session.commit()
    if not ok:
        # extremely unlikely right after the user just messaged us, but handle gracefully
        await message.answer(TEXTS["save_the_date"]["text"])
