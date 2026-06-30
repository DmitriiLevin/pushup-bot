"""
Щотижневий підсумок — щоп'ятниці о вказаний час.

Рахує кількість виконань кожного учасника за поточний тиждень (Пн–Пт)
та надсилає форматований звіт у чат.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from telegram.ext import ContextTypes

from core.config import Config
from core.models import DayRecord
from core.state import load_state
from messages.formatter import format_weekly_summary

logger = logging.getLogger(__name__)


async def friday_summary(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job: щоп'ятничний підсумок тижня."""
    config: Config = context.bot_data["config"]
    chat_id = context.job.chat_id

    # Перевіряємо, чи сьогодні п'ятниця (0=Monday, 4=Friday)
    now = datetime.now(tz=ZoneInfo(config.reminder_timezone))
    if now.weekday() != 4:
        return

    state = load_state()

    # Отримуємо дати Пн–Пт поточного тижня
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(5)]

    # Рахуємо виконання для кожного учасника
    weekly_counts: dict[str, int] = {}
    for name in config.participant_names:
        count = sum(
            1
            for d in week_dates
            if name in state.daily.get(d.isoformat(), DayRecord()).completed
        )
        weekly_counts[name] = count

    text = format_weekly_summary(config.participant_names, weekly_counts, state.current_week)
    await context.bot.send_message(chat_id=chat_id, text=text)

    logger.info("📈 Friday summary sent: %s", weekly_counts)
