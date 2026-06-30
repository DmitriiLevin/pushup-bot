"""
Ініціалізація Telegram Application та реєстрація handlers.
"""

from __future__ import annotations

import logging

from telegram.ext import Application, CommandHandler

from bot.commands.done import done_command
from bot.commands.help import help_command
from bot.commands.motivation import motivation_command
from bot.commands.status import status_command
from bot.commands.today import today_command
from bot.commands.week import week_command
from bot.scheduler import setup_scheduler
from core.config import Config

logger = logging.getLogger(__name__)


def create_app(config: Config) -> Application:
    """
    Створює та налаштовує Telegram Application.

    Args:
        config: Конфігурація застосунку.

    Returns:
        Готовий до запуску Application.
    """
    app = Application.builder().token(config.bot_token).build()

    # Робимо config доступним у всіх handlers через bot_data
    app.bot_data["config"] = config

    # Реєстрація команд
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(CommandHandler("week", week_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("motivation", motivation_command))

    # Налаштування розкладу
    setup_scheduler(app, config)

    logger.info(
        "🤖 Bot initialized. Participants: %s",
        ", ".join(f"{p.name} (@{p.username})" for p in config.participants),
    )

    return app
