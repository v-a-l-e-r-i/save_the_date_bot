import tempfile
from pathlib import Path

from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db import Guest, Status, count_by_status
from bot.services.import_contacts import import_contacts_file
from bot.services.link_generator import export_personal_links
from bot.services.excel_export import build_report
from bot.services.email_sender import send_report_email
from bot.services.messaging import send_save_the_date

router = Router(name="admin")


def _is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


@router.message(Command("whoami"))
async def cmd_whoami(message: Message):
    """TEMP DEBUG — прибрати після діагностики."""
    await message.answer(
        f"Твій user_id: {message.from_user.id}\n"
        f"ADMIN_IDS з .env: {settings.ADMIN_IDS}\n"
        f"Ти адмін: {_is_admin(message.from_user.id)}"
    )


@router.message(Command("import"))
async def cmd_import(message: Message, session: AsyncSession):
    """Reply to a CSV/Excel file with /import to load contacts (variant A and/or B)."""
    if not _is_admin(message.from_user.id):
        return
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.answer(
            "Дай відповідь командою /import на повідомлення з прикріпленим CSV/Excel файлом."
        )
        return

    doc = message.reply_to_message.document
    suffix = Path(doc.file_name).suffix or ".csv"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name

    bot: Bot = message.bot
    file = await bot.get_file(doc.file_id)
    await bot.download_file(file.file_path, destination=tmp_path)

    summary = await import_contacts_file(session, tmp_path)
    Path(tmp_path).unlink(missing_ok=True)

    await message.answer(
        "Імпорт завершено:\n"
        f"Всього: {summary['imported']}\n"
        f"Варіант А (chat_id відомий): {summary['variant_a']}\n"
        f"Варіант Б (потрібне персональне посилання): {summary['variant_b']}\n"
        f"Пропущено (порожні рядки): {summary['skipped']}"
    )


@router.message(Command("links"))
async def cmd_links(message: Message, session: AsyncSession):
    """Export personal invite links for variant B guests."""
    if not _is_admin(message.from_user.id):
        return
    if not settings.BOT_USERNAME:
        await message.answer("Вкажи BOT_USERNAME у .env, щоб генерувати посилання.")
        return

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name

    count = await export_personal_links(session, tmp_path)
    await message.answer_document(FSInputFile(tmp_path, filename="personal_links.xlsx"))
    await message.answer(f"Згенеровано {count} персональних посилань.")
    Path(tmp_path).unlink(missing_ok=True)


@router.message(Command("send_invitations"))
async def cmd_send_invitations(message: Message, session: AsyncSession, bot: Bot):
    """Broadcasts Save-the-date to all variant-A guests (known chat_id) not yet invited."""
    if not _is_admin(message.from_user.id):
        return

    result = await session.execute(
        select(Guest).where(Guest.chat_id.is_not(None), Guest.status == Status.NOT_SENT.value)
    )
    guests = list(result.scalars().all())

    if not guests:
        await message.answer("Немає гостей зі статусом 'не надіслано' для розсилки.")
        return

    sent = failed = 0
    for guest in guests:
        ok = await send_save_the_date(bot, guest)
        sent += int(ok)
        failed += int(not ok)
    await session.commit()

    await message.answer(f"Розсилка завершена. Надіслано: {sent}. Помилки доставки: {failed}.")


@router.message(Command("report_now"))
async def cmd_report_now(message: Message, session: AsyncSession):
    if not _is_admin(message.from_user.id):
        return

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name

    await build_report(session, tmp_path)
    await message.answer_document(FSInputFile(tmp_path, filename="guests_report.xlsx"))

    try:
        send_report_email(tmp_path)
        await message.answer(f"Звіт також надіслано на {settings.REPORT_EMAIL_TO}.")
    except Exception as e:
        await message.answer(f"Звіт згенеровано, але email не надіслано: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession):
    if not _is_admin(message.from_user.id):
        return
    counts = await count_by_status(session)
    lines = [f"{status}: {count}" for status, count in counts.items()]
    await message.answer("Статистика по гостях:\n" + "\n".join(lines) if lines else "Порожньо.")