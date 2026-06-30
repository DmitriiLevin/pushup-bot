"""
Команда /help — довідка по командах бота.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from core.config import Config
from messages.formatter import format_help_message

logger = logging.getLogger(__name__)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник команди /help."""
    config: Config = context.bot_data["config"]

    text = format_help_message(
        config.reminder_time.strftime("%H:%M"),
        config.reminder_timezone,
    )

    await update.message.reply_text(text)
