from aiogram.types import Message, InlineKeyboardMarkup


async def smart_edit(message: Message, text: str, reply_markup: InlineKeyboardMarkup | None = None):
    """Edits a message's text or caption, whichever applies."""
    if message.photo:
        await message.edit_caption(caption=text, reply_markup=reply_markup)
    else:
        await message.edit_text(text, reply_markup=reply_markup)