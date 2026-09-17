import re

from aiogram.types import Message, InlineKeyboardMarkup


def is_valid_full_name(name: str) -> bool:
    words = [w for w in name.strip().split() if w]
    return len(words) >= 2


def normalize_phone(raw: str) -> str | None:
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("380") and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("0") and len(digits) == 10:
        return f"+38{digits}"
    if len(digits) == 9:
        return f"+380{digits}"
    return None


async def smart_edit(message: Message, text: str, reply_markup: InlineKeyboardMarkup | None = None):
    """Edits a message's text or caption, whichever applies."""
    if message.photo:
        await message.edit_caption(caption=text, reply_markup=reply_markup)
    else:
        await message.edit_text(text, reply_markup=reply_markup)