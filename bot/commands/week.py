"""
Команда /week — показує поточний тиждень програми.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from core.state import load_state
from programs.registry import get_program

logger = logging.getLogger(__name__)


async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник команди /week."""
    state = load_state()

    try:
        program = get_program(state.current_program)
    except KeyError as e:
        logger.error("Програма не знайдена: %s", e)
        await update.message.reply_text("⚠️ Програма не знайдена.")
        return

    week = state.current_week
    total = program.total_weeks

    await update.message.reply_text(
        f"📅 Поточний тиждень: {week} з {total}\n\n"
        f"Програма: {program.display_name}"
    )
