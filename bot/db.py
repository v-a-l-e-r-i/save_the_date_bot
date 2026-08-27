import json
from datetime import datetime, date
from enum import Enum

from sqlalchemy import (
    String, Integer, DateTime, Date, Text, select, func
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from bot.config import settings


class Base(DeclarativeBase):
    pass


class Status(str, Enum):
    INVITED = "invited"           # запрошено, повідомлення надіслано
    PENDING = "pending"           # відповів частково (обрав дату, дані ще збираються)
    CONFIRMED = "confirmed"       # підтвердив дату + дані повні
    NO_RESPONSE = "no_response"   # не відповів (виставляється планувальником для звітності)
    NOT_SENT = "not_sent"         # імпортований, але Save the date ще не надіслано


class Guest(Base):
    __tablename__ = "guests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Telegram identifiers
    chat_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Contact source
    start_code: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(1), default="A")  # "A" or "B"

    # Guest data
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Prefilled from import? (so we ask for confirmation, not fresh input)
    prefilled: Mapped[bool] = mapped_column(default=False)

    # Visit date
    chosen_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # JSON list of {"date": "2026-10-28", "changed_at": "iso"}
    date_history_json: Mapped[str] = mapped_column(Text, default="[]")

    status: Mapped[str] = mapped_column(String(32), default=Status.NOT_SENT.value)

    invited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reminder_1_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reminder_2_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    last_delivery_error: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def date_history(self) -> list[dict]:
        return json.loads(self.date_history_json or "[]")

    def add_date_change(self, new_date: str):
        history = self.date_history()
        history.append({"date": new_date, "changed_at": datetime.utcnow().isoformat()})
        self.date_history_json = json.dumps(history, ensure_ascii=False)


# FSM temp state for data collection is handled by aiogram FSMContext, not stored here.

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_guest_by_chat_id(session: AsyncSession, chat_id: int) -> Guest | None:
    result = await session.execute(select(Guest).where(Guest.chat_id == chat_id))
    return result.scalar_one_or_none()


async def get_guest_by_start_code(session: AsyncSession, code: str) -> Guest | None:
    result = await session.execute(select(Guest).where(Guest.start_code == code))
    return result.scalar_one_or_none()


async def get_all_guests(session: AsyncSession) -> list[Guest]:
    result = await session.execute(select(Guest).order_by(Guest.id))
    return list(result.scalars().all())


async def count_by_status(session: AsyncSession) -> dict:
    result = await session.execute(
        select(Guest.status, func.count(Guest.id)).group_by(Guest.status)
    )
    return {status: count for status, count in result.all()}
