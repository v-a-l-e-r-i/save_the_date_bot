import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _split_ids(raw: str) -> set[int]:
    return {int(x.strip()) for x in raw.split(",") if x.strip()}


class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "")
    ADMIN_IDS: set[int] = _split_ids(os.getenv("ADMIN_IDS", ""))

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/bot.db")

    EXHIBITION_DATES: list[str] = os.getenv(
        "EXHIBITION_DATES", "2026-10-28,2026-10-29,2026-10-30"
    ).split(",")
    TIMEZONE: str = os.getenv("EXHIBITION_TIMEZONE", "Europe/Kyiv")

    REMINDER_1_DAYS_AFTER_INVITE: int = int(os.getenv("REMINDER_1_DAYS_AFTER_INVITE", 14))
    REMINDER_2_DAYS_BEFORE_EVENT: int = int(os.getenv("REMINDER_2_DAYS_BEFORE_EVENT", 7))
    SCHEDULER_HOUR: int = int(os.getenv("SCHEDULER_HOUR", 10))
    SCHEDULER_MINUTE: int = int(os.getenv("SCHEDULER_MINUTE", 0))

    BREVO_API_KEY: str = os.getenv("BREVO_API_KEY", "")
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    REPORT_EMAIL_TO: str = os.getenv("REPORT_EMAIL_TO", "")
    DAILY_AUTO_REPORT: bool = os.getenv("DAILY_AUTO_REPORT", "false").lower() == "true"


settings = Settings()

with open(BASE_DIR / "texts.yaml", "r", encoding="utf-8") as f:
    TEXTS: dict = yaml.safe_load(f)

# date_key ("1"/"2"/"3") -> actual date string from .env, in the same order as texts.yaml buttons
DATE_KEY_TO_ISO = {
    str(i + 1): d.strip() for i, d in enumerate(settings.EXHIBITION_DATES)
}
