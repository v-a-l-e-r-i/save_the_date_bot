import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from bot.config import settings, DATE_KEY_TO_ISO, ISO_TO_DATE_LABEL
from bot.db import async_session, Guest, Status
from bot.services.messaging import send_reminder
from bot.services.excel_export import build_report
from bot.services.email_sender import send_report_email

logger = logging.getLogger("save_the_date.scheduler")

_EVENT_START = min(DATE_KEY_TO_ISO.values()) if DATE_KEY_TO_ISO else None


async def _run_reminders(bot: Bot):
    now = datetime.utcnow()
    today = datetime.now(ZoneInfo(settings.TIMEZONE)).date()

    async with async_session() as session:
        no_date_result = await session.execute(
            select(Guest).where(
                Guest.chat_id.is_not(None),
                Guest.invited_at.is_not(None),
                Guest.chosen_date.is_(None),
            )
        )
        no_date_guests = list(no_date_result.scalars().all())

        for guest in no_date_guests:
            if (
                guest.reminder_1_sent_at is None
                and now - guest.invited_at >= timedelta(days=settings.REMINDER_1_DAYS_AFTER_INVITE)
            ):
                ok = await send_reminder(bot, guest, "reminder_1")
                if ok:
                    guest.reminder_1_sent_at = now

        confirmed_result = await session.execute(
            select(Guest).where(
                Guest.chat_id.is_not(None),
                Guest.status == Status.CONFIRMED.value,
                Guest.chosen_date.is_not(None),
            )
        )
        confirmed_guests = list(confirmed_result.scalars().all())

        for guest in confirmed_guests:
            days_until = (guest.chosen_date - today).days
            if (
                guest.reminder_2_sent_at is None
                and days_until == settings.REMINDER_2_DAYS_BEFORE_EVENT
            ):
                date_label = ISO_TO_DATE_LABEL.get(
                    guest.chosen_date.isoformat(),
                    guest.chosen_date.strftime("%d.%m.%Y"),
                )
                ok = await send_reminder(
                    bot,
                    guest,
                    "reminder_2",
                    format_kwargs={"date": date_label},
                    with_date_buttons=False,
                )
                if ok:
                    guest.reminder_2_sent_at = now

        event_start = datetime.fromisoformat(_EVENT_START) if _EVENT_START else None
        if event_start and now > event_start:
            stale_result = await session.execute(
                select(Guest).where(Guest.status != Status.CONFIRMED.value)
            )
            for guest in stale_result.scalars().all():
                guest.status = Status.NO_RESPONSE.value

        await session.commit()

    logger.info(
        "Reminder run complete: %d without date, %d confirmed",
        len(no_date_guests),
        len(confirmed_guests),
    )


async def _run_daily_report():
    if not settings.DAILY_AUTO_REPORT:
        return
    async with async_session() as session:
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name
        await build_report(session, tmp_path)
        try:
            send_report_email(tmp_path)
            logger.info("Daily report emailed successfully")
        except Exception as e:
            logger.error("Failed to email daily report: %s", e)
        finally:
            Path(tmp_path).unlink(missing_ok=True)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)

    trigger = CronTrigger(hour=settings.SCHEDULER_HOUR, minute=settings.SCHEDULER_MINUTE)
    scheduler.add_job(_run_reminders, trigger, args=[bot], id="reminders", replace_existing=True)
    scheduler.add_job(_run_daily_report, trigger, id="daily_report", replace_existing=True)

    return scheduler
