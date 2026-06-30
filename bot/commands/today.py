"""
Команда /today — показує сьогоднішнє тренування.
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

from core.config import Config
from core.state import load_state
from messages.formatter import format_rest_day_today, format_today_workout
from messages.selector import get_day_category
from programs.registry import get_program

logger = logging.getLogger(__name__)

_KYIV_TZ = ZoneInfo("Europe/Kyiv")


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник команди /today."""
    config: Config = context.bot_data["config"]
    state = load_state()

    category = get_day_category(datetime.now(tz=_KYIV_TZ))

    if category == "weekend":
        await update.message.reply_text(format_rest_day_today())
        return

    try:
        program = get_program(state.current_program)
        workout = program.get_workout(state.current_week)
    except (KeyError, ValueError) as e:
        logger.error("Помилка отримання тренування: %s", e)
        await update.message.reply_text("⚠️ Не вдалось завантажити тренування.")
        return

    await update.message.reply_text(format_today_workout(workout))
