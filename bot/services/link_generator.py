from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db import Guest


async def export_personal_links(session: AsyncSession, out_path: str) -> int:
    """Exports an Excel file with a personal t.me/Bot?start=code link for every
    guest imported without a chat_id (variant B). Returns the number of links written."""
    result = await session.execute(select(Guest).where(Guest.start_code.is_not(None)))
    guests = list(result.scalars().all())

    wb = Workbook()
    ws = wb.active
    ws.title = "Personal links"
    ws.append(["full_name", "phone", "company", "position", "personal_link"])

    for g in guests:
        link = f"https://t.me/{settings.BOT_USERNAME}?start={g.start_code}"
        ws.append([g.full_name or "", g.phone or "", g.company or "", g.position or "", link])

    wb.save(out_path)
    return len(guests)
