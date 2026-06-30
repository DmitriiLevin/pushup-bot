"""
Щоденний job о вказаний час (за налаштованою timezone).

Логіка:
- Будні (Пн–Пт): надсилає повідомлення з тренуванням
- Вихідні (Сб–Нд): надсилає повідомлення про відпочинок
"""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram.ext import ContextTypes

from core.config import Config
from core.state import load_state, save_state
from messages.formatter import format_weekend_message, format_workout_message
from messages.selector import get_day_category, select_phrase
from programs.registry import get_program

logger = logging.getLogger(__name__)

_KYIV_TZ = ZoneInfo("Europe/Kyiv")


async def daily_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Щоденний job: визначає тип дня і надсилає відповідне повідомлення."""
    config: Config = context.bot_data["config"]
    chat_id = context.job.chat_id

    now = datetime.now(tz=_KYIV_TZ)
    logger.info(
        "📅 Daily reminder triggered for %s",
        now.strftime("%Y-%m-%d %H:%M %Z"),
    )

    category = get_day_category(now)

    state = load_state()
    phrase, updated_recent, used_category = select_phrase(state, config.phrase_history_size)
    state.recent_phrases[used_category] = updated_recent

    if category == "weekend":
        text = format_weekend_message(phrase)
        save_state(state)
        await context.bot.send_message(chat_id=chat_id, text=text)
        logger.info("📤 Weekend rest message sent")
        return

    try:
        program = get_program(state.current_program)
        workout = program.get_workout(state.current_week)
    except (KeyError, ValueError) as e:
        logger.error("❌ Failed to get workout: %s", e)
        return

    text = format_workout_message(phrase, workout)
    save_state(state)

    await context.bot.send_message(chat_id=chat_id, text=text)
    logger.info(
        "📤 Workout message sent: week %d, total %d reps",
        workout.week,
        workout.total,
    )
