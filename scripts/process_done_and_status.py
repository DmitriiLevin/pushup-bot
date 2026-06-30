#!/usr/bin/env python3
"""
Вечірня обробка: читає /done повідомлення з Telegram, оновлює стан,
надсилає статус дня. У п'ятницю також надсилає підсумок тижня.

Запускається GitHub Actions о 18:00 Europe/Warsaw (Пн–Пт).
Зберігає update_offset у state.json, щоб не обробляти повідомлення двічі.
"""

import logging
import os
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

from core.config import Config
from core.models import DayRecord
from core.state import load_state, save_state
from messages.formatter import format_status_message, format_weekly_summary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_WARSAW_TZ = ZoneInfo("Europe/Warsaw")

SEPARATOR = "━━━━━━━━━━━━━━"


def send_message(bot_token: str, chat_id: int, text: str) -> None:
    """Надсилає повідомлення через Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": chat_id, "text": text},
        timeout=30,
    )
    resp.raise_for_status()
    logger.info("Повідомлення надіслано (%d символів)", len(text))


def get_updates(bot_token: str, offset: int) -> list[dict]:
    """Повертає нові оновлення від Telegram, починаючи з offset."""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    resp = requests.get(
        url,
        params={"offset": offset, "limit": 100, "timeout": 0},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("result", [])


def main() -> None:
    config = Config.from_env()
    state = load_state()

    # username (без @, lowercase) → відображуване ім'я
    username_to_name = {p.username.lower(): p.name for p in config.participants}

    # Завантажуємо нові оновлення
    updates = get_updates(config.bot_token, state.update_offset)
    logger.info("Отримано %d оновлень (offset=%d)", len(updates), state.update_offset)

    now_warsaw = datetime.now(tz=_WARSAW_TZ)
    today_date = now_warsaw.date()

    new_completions: list[str] = []
    max_update_id = state.update_offset

    for update in updates:
        update_id = update["update_id"]
        if update_id + 1 > max_update_id:
            max_update_id = update_id + 1

        msg = update.get("message") or update.get("edited_message")
        if not msg:
            continue

        # Перевіряємо, що повідомлення надіслано сьогодні
        msg_date = datetime.fromtimestamp(msg["date"], tz=_WARSAW_TZ).date()
        if msg_date != today_date:
            continue

        text = (msg.get("text") or "").strip()
        # Матчимо /done, /done@botname, /done з будь-яким суфіксом
        lower = text.lower()
        if not (lower == "/done" or lower.startswith("/done@") or lower.startswith("/done ")):
            continue

        from_user = msg.get("from", {})
        username = (from_user.get("username") or "").lower()
        if not username:
            logger.info("Повідомлення /done без username, пропускаємо")
            continue

        name = username_to_name.get(username)
        if not name:
            logger.info("Невідомий @%s надіслав /done, пропускаємо", username)
            continue

        record = state.get_or_create_today_record()
        if name not in record.completed:
            record.completed.append(name)
            new_completions.append(name)
            logger.info("Відмічено: %s", name)
        else:
            logger.info("%s вже відмічений", name)

    # Зберігаємо новий offset, щоб не обробляти ці повідомлення вдруге
    state.update_offset = max_update_id

    # Формуємо і надсилаємо вечірній статус
    all_names = [p.name for p in config.participants]
    today_str = today_date.isoformat()
    record = state.daily.get(today_str, DayRecord())
    completed = record.completed
    count = len(completed)
    total = len(all_names)

    status_lines = format_status_message(all_names, completed)

    status_text = (
        f"📊 Підсумок дня\n\n"
        f"{SEPARATOR}\n\n"
        f"Виконали {count}/{total}:\n\n"
        f"{status_lines}"
    )
    if count == total and total > 0:
        status_text += f"\n\n🏆 Всі виконали! Так тримати!"

    send_message(config.bot_token, config.chat_id, status_text)
    logger.info("Статус дня надіслано: %d/%d виконали", count, total)

    # П'ятничний підсумок тижня
    if now_warsaw.weekday() == 4:  # 4 = Friday
        monday = today_date - timedelta(days=today_date.weekday())
        week_dates = [monday + timedelta(days=i) for i in range(5)]

        weekly_counts: dict[str, int] = {
            name: sum(
                1
                for d in week_dates
                if name in state.daily.get(d.isoformat(), DayRecord()).completed
            )
            for name in all_names
        }

        summary_text = format_weekly_summary(all_names, weekly_counts, state.current_week)
        send_message(config.bot_token, config.chat_id, summary_text)
        logger.info("П'ятничний підсумок надіслано: %s", weekly_counts)

    save_state(state)


if __name__ == "__main__":
    main()
