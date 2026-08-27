"""
Імпорт контактів з CSV/Excel.

Очікувані колонки (не всі обов'язкові):
    chat_id   - якщо є (варіант А, вже підписані на бота)
    username  - опційно
    full_name - опційно (буде запропоновано підтвердити/ввести)
    phone     - опційно
    company   - опційно
    position  - опційно

Якщо chat_id відсутній - рядок трактується як варіант Б: генерується
унікальний start_code, і людину потрібно запросити персональним посиланням
(див. link_generator.py).
"""
import secrets
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db import Guest


def _read_table(path: str) -> pd.DataFrame:
    if path.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    return df


async def import_contacts_file(session: AsyncSession, path: str) -> dict:
    """Returns a summary dict: {'imported': N, 'variant_a': N, 'variant_b': N, 'skipped': N}"""
    df = _read_table(path)
    imported = variant_a = variant_b = skipped = 0

    for _, row in df.iterrows():
        chat_id = row.get("chat_id")
        chat_id = int(chat_id) if pd.notna(chat_id) else None

        full_name = str(row.get("full_name")) if pd.notna(row.get("full_name")) else None
        phone = str(row.get("phone")) if pd.notna(row.get("phone")) else None
        company = str(row.get("company")) if pd.notna(row.get("company")) else None
        position = str(row.get("position")) if pd.notna(row.get("position")) else None
        username = str(row.get("username")) if pd.notna(row.get("username")) else None

        if not chat_id and not full_name and not phone:
            skipped += 1
            continue

        guest = Guest(
            chat_id=chat_id,
            username=username,
            full_name=full_name,
            phone=phone,
            company=company,
            position=position,
            prefilled=bool(full_name or phone or company),
            source="A" if chat_id else "B",
        )
        if not chat_id:
            guest.start_code = secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:12]
            variant_b += 1
        else:
            variant_a += 1

        session.add(guest)
        imported += 1

    await session.commit()
    return {
        "imported": imported,
        "variant_a": variant_a,
        "variant_b": variant_b,
        "skipped": skipped,
    }
