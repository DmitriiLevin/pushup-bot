"""
Команда /status — показує хто виконав тренування сьогодні.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from core.config import Config
from core.state import load_state
from messages.formatter import format_status_message

logger = logging.getLogger(__name__)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник команди /status."""
    config: Config = context.bot_data["config"]
    state = load_state()

    record = state.get_today_record()
    status_text = format_status_message(config.participant_names, record.completed)

    done_count = len(record.completed)
    total_count = len(config.participants)

    header = f"📊 Статус на сьогодні ({done_count}/{total_count}):\n\n"

    await update.message.reply_text(header + status_text)
