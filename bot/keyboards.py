from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)

from bot.config import TEXTS


def date_selection_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"date:{key}")]
        for key, label in TEXTS["date_buttons"].items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def change_date_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=TEXTS["change_date_button"], callback_data="change_date")
        ]]
    )


def share_phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=TEXTS["ask_phone_button"], request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def confirm_prefilled_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=TEXTS["confirm_prefilled_yes"], callback_data="prefill:yes"),
            InlineKeyboardButton(text=TEXTS["confirm_prefilled_edit"], callback_data="prefill:edit"),
        ]]
    )
