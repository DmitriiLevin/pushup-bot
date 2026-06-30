"""
Команда /motivation — відправляє мотиваційну фразу.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from core.config import Config
from core.state import load_state, save_state
from messages.formatter import format_motivation_message
from messages.selector import pick_phrase

logger = logging.getLogger(__name__)


async def motivation_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник команди /motivation."""
    config: Config = context.bot_data["config"]
    state = load_state()

    phrase, new_history = pick_phrase(state, "motivation", config.phrase_history_size)
    state.recent_phrases["motivation"] = new_history
    save_state(state)

    logger.info("💡 Motivation phrase sent")
    await update.message.reply_text(format_motivation_message(phrase))
