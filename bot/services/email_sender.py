"""
Надсилання звіту через Brevo HTTP API (https://api.brevo.com), а не SMTP.

Чому не SMTP: багато хмарних платформ (у т.ч. Railway) блокують вихідний
трафік на SMTP-порти (25/465/587), щоб їх не використовували для спаму.
Спроба з'єднання просто висить і падає по timeout. HTTP API працює на
порту 443 (звичайний https), який ніхто не блокує.

Налаштування (безкоштовно):
1. Зареєструватись на https://app.brevo.com
2. Settings -> Senders, Domains & Dedicated IPs -> Senders -> додати й
   підтвердити email, з якого надсилатимуться листи (лист з посиланням
   підтвердження прийде на цю ж адресу).
3. Settings -> SMTP & API -> API Keys -> створити ключ, вставити у
   BREVO_API_KEY в .env.
"""
import base64
import requests

from bot.config import settings

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_report_email(file_path: str, subject: str = "Save the Date — звіт по гостях") -> None:
    if not settings.BREVO_API_KEY or not settings.REPORT_EMAIL_TO or not settings.SMTP_USER:
        raise RuntimeError(
            "Email не налаштовано: перевірте BREVO_API_KEY, SMTP_USER (підтверджений "
            "відправник) і REPORT_EMAIL_TO у .env"
        )

    with open(file_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()

    payload = {
        "sender": {"email": settings.SMTP_USER},
        "to": [{"email": settings.REPORT_EMAIL_TO}],
        "subject": subject,
        "htmlContent": "<p>У додатку — актуальний звіт по гостях виставки.</p>",
        "attachment": [
            {
                "content": content_b64,
                "name": file_path.split("/")[-1],
            }
        ],
    }

    response = requests.post(
        BREVO_API_URL,
        json=payload,
        headers={
            "api-key": settings.BREVO_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        timeout=20,
    )

    if response.status_code >= 300:
        raise RuntimeError(f"Brevo API помилка {response.status_code}: {response.text}")
