import logging
from datetime import datetime
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramNotFound
from aiogram.types import FSInputFile

from bot.config import TEXTS, BASE_DIR
from bot.db import Guest, Status

logger = logging.getLogger("save_the_date.delivery")


async def send_save_the_date(bot: Bot, guest: Guest) -> bool:
    """Sends the initial Save-the-Date banner + date buttons to a guest.
    Returns True on success, False on delivery failure (and logs/records the error)."""
    from bot.keyboards import date_selection_kb  # local import to avoid circulars

    banner_path = BASE_DIR / TEXTS["banner_path"]
    try:
        if banner_path.exists():
            await bot.send_photo(
                guest.chat_id,
                photo=FSInputFile(str(banner_path)),
                caption=TEXTS["save_the_date"]["text"],
                reply_markup=date_selection_kb(),
            )
        else:
            await bot.send_message(
                guest.chat_id,
                TEXTS["save_the_date"]["text"],
                reply_markup=date_selection_kb(),
            )
        guest.status = Status.INVITED.value
        guest.invited_at = datetime.utcnow()
        guest.last_delivery_error = None
        return True
    except (TelegramForbiddenError, TelegramNotFound) as e:
        # user blocked the bot or deleted their account
        guest.last_delivery_error = f"{type(e).__name__}: {e}"
        logger.warning("Delivery failed for chat_id=%s: %s", guest.chat_id, e)
        return False
    except TelegramBadRequest as e:
        guest.last_delivery_error = f"{type(e).__name__}: {e}"
        logger.error("Bad request sending to chat_id=%s: %s", guest.chat_id, e)
        return False


async def send_reminder(bot: Bot, guest: Guest, text_key: str) -> bool:
    from bot.keyboards import date_selection_kb

    try:
        await bot.send_message(guest.chat_id, TEXTS[text_key], reply_markup=date_selection_kb())
        guest.last_delivery_error = None
        return True
    except (TelegramForbiddenError, TelegramNotFound, TelegramBadRequest) as e:
        guest.last_delivery_error = f"{type(e).__name__}: {e}"
        logger.warning("Reminder delivery failed for chat_id=%s: %s", guest.chat_id, e)
        return False
