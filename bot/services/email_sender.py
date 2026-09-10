import smtplib
import socket
from email.message import EmailMessage
from pathlib import Path

from bot.config import settings


def _resolve_ipv4(host: str) -> str:
    """Force IPv4 resolution.

    Some hosting providers (e.g. Railway) don't route IPv6 egress traffic,
    but SMTP hostnames like smtp.gmail.com resolve to both A and AAAA
    records. smtplib may pick the IPv6 address and fail with
    'Network is unreachable'. Resolving to an IPv4 address explicitly avoids
    that.
    """
    try:
        return socket.getaddrinfo(host, None, socket.AF_INET)[0][4][0]
    except socket.gaierror:
        return host  # fall back to the original host if IPv4 lookup fails


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

    ipv4_host = _resolve_ipv4(settings.SMTP_HOST)

    server = smtplib.SMTP(ipv4_host, settings.SMTP_PORT, timeout=20)
    try:
        # Connected via a raw IPv4 address to dodge Railway's missing IPv6
        # route, but the TLS certificate is issued for the hostname — tell
        # smtplib to verify against the real hostname, not the IP.
        server._host = settings.SMTP_HOST
        server.ehlo(settings.SMTP_HOST)
        server.starttls()
        server.ehlo(settings.SMTP_HOST)
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
    finally:
        server.quit()
