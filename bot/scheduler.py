import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from bot.config import settings, DATE_KEY_TO_ISO
from bot.db import async_session, Guest, Status
from bot.services.messaging import send_reminder
from bot.services.excel_export import build_report
from bot.services.email_sender import send_report_email

logger = logging.getLogger("save_the_date.scheduler")

# earliest exhibition date, used for the "1 week before event" reminder
_EVENT_START = min(DATE_KEY_TO_ISO.values()) if DATE_KEY_TO_ISO else None


async def _run_reminders(bot: Bot):
    now = datetime.utcnow()
    async with async_session() as session:
        result = await session.execute(
            select(Guest).where(
                Guest.chat_id.is_not(None),
                Guest.status.in_([Status.INVITED.value, Status.PENDING.value]),
            )
        )
        guests = list(result.scalars().all())

        event_start = (
            datetime.fromisoformat(_EVENT_START) if _EVENT_START else None
        )

        for guest in guests:
            # Reminder 1: N days after invite, only once
            if (
                guest.invited_at
                and guest.reminder_1_sent_at is None
                and now - guest.invited_at >= timedelta(days=settings.REMINDER_1_DAYS_AFTER_INVITE)
            ):
                ok = await send_reminder(bot, guest, "reminder_1")
                if ok:
                    guest.reminder_1_sent_at = now

            # Reminder 2: N days before the event, only once
            if (
                event_start
                and guest.reminder_2_sent_at is None
                and event_start - now <= timedelta(days=settings.REMINDER_2_DAYS_BEFORE_EVENT)
                and event_start > now
            ):
                ok = await send_reminder(bot, guest, "reminder_2")
                if ok:
                    guest.reminder_2_sent_at = now

            # Mark as no_response for reporting once the event has effectively passed
            # and the guest still hasn't confirmed (kept simple: just past reminder_2 window)
            if event_start and now > event_start and guest.status != Status.CONFIRMED.value:
                guest.status = Status.NO_RESPONSE.value

        await session.commit()
    logger.info("Reminder run complete: %d guests checked", len(guests))


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
