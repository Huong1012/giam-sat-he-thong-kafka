"""Gửi ảnh và chú thích qua Telegram và Discord."""
import os

import requests  # type: ignore

from common.logger import configure_logger

logger = configure_logger("gui_tin")


def gui_telegram(anh_png, chu_thich):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.error("Thiếu TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID trong tệp .env")
        return False
    try:
        kq = requests.post(
            f"https://api.telegram.org/bot{token}/sendPhoto",
            data={"chat_id": chat_id, "caption": chu_thich[:1000]},
            files={"photo": ("canh_bao.png", anh_png, "image/png")},
            timeout=30,
        )
    except requests.RequestException as loi:
        logger.error(f"Không gửi được Telegram: {type(loi).__name__}")
        return False
    if kq.status_code != 200:
        logger.error(f"Telegram báo lỗi, mã {kq.status_code}")
        return False
    return True


def gui_discord(anh_png, chu_thich):
    webhook = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook:
        return False
    try:
        kq = requests.post(
            webhook,
            data={"content": chu_thich[:1900]},
            files={"file": ("canh_bao.png", anh_png, "image/png")},
            timeout=30,
        )
    except requests.RequestException as loi:
        logger.error(f"Không gửi được Discord: {type(loi).__name__}")
        return False
    if kq.status_code not in (200, 204):
        logger.error(f"Discord báo lỗi, mã {kq.status_code}")
        return False
    return True
