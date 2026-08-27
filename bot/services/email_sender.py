import smtplib
from email.message import EmailMessage
from pathlib import Path

from bot.config import settings


def send_report_email(file_path: str, subject: str = "Save the Date — звіт по гостях") -> None:
    if not settings.SMTP_HOST or not settings.REPORT_EMAIL_TO:
        raise RuntimeError(
            "SMTP не налаштовано: перевірте SMTP_HOST/SMTP_USER/SMTP_PASSWORD/REPORT_EMAIL_TO у .env"
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_USER
    msg["To"] = settings.REPORT_EMAIL_TO
    msg.set_content("У додатку — актуальний звіт по гостях виставки.")

    data = Path(file_path).read_bytes()
    msg.add_attachment(
        data,
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=Path(file_path).name,
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
