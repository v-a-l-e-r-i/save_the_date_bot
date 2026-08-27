import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import settings
from bot.db import init_db
from bot.middlewares import DbSessionMiddleware
from bot.scheduler import setup_scheduler
from bot.handlers import start, date_selection, data_collection, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("save_the_date")


async def main():
    if not settings.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не заданий у .env")

    await init_db()

    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.update.middleware(DbSessionMiddleware())

    dp.include_router(admin.router)          # admin commands first (they short-circuit for non-admins)
    dp.include_router(start.router)
    dp.include_router(date_selection.router)
    dp.include_router(data_collection.router)

    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("Scheduler started (timezone=%s)", settings.TIMEZONE)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Bot polling started")
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
