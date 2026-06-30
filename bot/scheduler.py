"""
Налаштування розкладу jobs через PTB JobQueue (APScheduler під капотом).
"""

from __future__ import annotations

import logging

from telegram.ext import Application

from bot.jobs.daily_reminder import daily_reminder
from bot.jobs.friday_summary import friday_summary
from core.config import Config

logger = logging.getLogger(__name__)


def setup_scheduler(app: Application, config: Config) -> None:
    """
    Реєструє всі scheduled jobs.

    Args:
        app:    Telegram Application.
        config: Конфігурація застосунку.
    """
    if app.job_queue is None:
        raise RuntimeError(
            "JobQueue недоступний. "
            "Встановіть: pip install 'python-telegram-bot[job-queue]'"
        )

    app.job_queue.run_daily(
        callback=daily_reminder,
        time=config.reminder_time,
        chat_id=config.chat_id,
        name="daily_reminder",
    )

    logger.info(
        "⏰ Daily reminder scheduled: %s %s",
        config.reminder_time.strftime("%H:%M"),
        config.reminder_timezone,
    )

    app.job_queue.run_daily(
        callback=friday_summary,
        time=config.friday_summary_time,
        chat_id=config.chat_id,
        name="friday_summary",
    )

    logger.info(
        "📈 Friday summary scheduled: %s %s",
        config.friday_summary_time.strftime("%H:%M"),
        config.reminder_timezone,
    )

    logger.info("🚀 Bot started successfully")
