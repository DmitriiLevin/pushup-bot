#!/usr/bin/env python3
"""
Живий 24/7 Telegram-бот для командного 15-тижневого челенджу з віджимань.

На відміну від старої версії (двічі на день через GitHub Actions cron),
цей процес працює постійно: миттєво реагує на /done, /status, /ask та інші
команди, а нагадування о 12:00/18:00 надсилає через вбудований планувальник
(JobQueue) з коректним урахуванням часового поясу.

Запуск: python main.py
"""

import logging
from datetime import time
from zoneinfo import ZoneInfo

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from bot.handlers import (
    ask_command,
    done_command,
    error_handler,
    help_command,
    mention_message,
    motivation_command,
    start_command,
    status_command,
    today_command,
    undone_command,
    week_command,
)
from bot.jobs import friday_weekly_summary_job, morning_reminder_job
from bot.shared import Runtime
from core.clock import local_today
from core.config import Config
from core.persistence import pull_latest
from core.state import load_state
from messages.formatter import format_intro_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def build_runtime() -> Runtime:
    config = Config.from_env()

    if config.persistence_enabled:
        logger.info("Синхронізую state.json з GitHub перед стартом...")
        pull_latest(config.github_token, config.github_repo)  # type: ignore[arg-type]
    else:
        logger.warning(
            "GITHUB_TOKEN/GITHUB_REPO не задані — стан зберігається тільки на "
            "локальному диску і може загубитись при передеплої. Дивись README."
        )

    state = load_state()

    # Перше запалення: щоб maybe_advance_week не піднімав тиждень заднім числом
    # одразу при старті, якщо сьогодні понеділок, а історія просування ще порожня.
    if state.last_advanced_on is None:
        state.last_advanced_on = local_today(config.timezone).isoformat()

    return Runtime(config=config, state=state)


async def send_intro_if_needed(app) -> None:
    """Одноразово (при першому запуску бота в групі) вітається і пояснює,
    що бот вміє. Далі, навіть після перезапусків/передеплоїв, більше не
    повторюється — прапорець intro_announced зберігається в стані."""
    runtime: Runtime = app.bot_data["runtime"]
    if runtime.state.intro_announced:
        return

    text = format_intro_message(runtime.config.participant_names, runtime.config.ai_enabled)
    await app.bot.send_message(runtime.config.chat_id, text)

    runtime.state.intro_announced = True
    await runtime.persist("intro message sent")
    logger.info("Вітальне повідомлення надіслано в групу")


def main() -> None:
    runtime = build_runtime()
    tz = ZoneInfo(runtime.config.timezone)

    app = (
        ApplicationBuilder()
        .token(runtime.config.bot_token)
        .post_init(send_intro_if_needed)
        .build()
    )
    app.bot_data["runtime"] = runtime

    # Бот реагує ТІЛЬКИ в межах нашої групи (CHAT_ID). Повідомлення з будь-якого
    # іншого чату (приват, чужа група) ігноруються повністю — без цього будь-хто,
    # хто знайде бота в Telegram, міг би смикати платні AI-команди чи /done.
    own_chat = filters.Chat(chat_id=runtime.config.chat_id)

    # Команди
    app.add_handler(CommandHandler("start", start_command, filters=own_chat))
    app.add_handler(CommandHandler("help", help_command, filters=own_chat))
    app.add_handler(CommandHandler("today", today_command, filters=own_chat))
    app.add_handler(CommandHandler("done", done_command, filters=own_chat))
    app.add_handler(CommandHandler("undone", undone_command, filters=own_chat))
    app.add_handler(CommandHandler("status", status_command, filters=own_chat))
    app.add_handler(CommandHandler("week", week_command, filters=own_chat))
    app.add_handler(CommandHandler("motivation", motivation_command, filters=own_chat))
    app.add_handler(CommandHandler("ask", ask_command, filters=own_chat))

    # Живий AI-чат: коли бота згадали або відповіли на його повідомлення
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & own_chat, mention_message)
    )

    app.add_error_handler(error_handler)

    # Заплановані завдання (Пн-Пт, з урахуванням DST через ZoneInfo)
    #
    # УВАГА: у встановленій версії python-telegram-bot (21.10) параметр
    # `days` для run_daily рахує дні від НЕДІЛІ (0=нд, 1=пн, ..., 6=сб),
    # а не від понеділка, як можна було б очікувати. Перевірено напряму
    # через APScheduler-тригер на реальних датах — (1,2,3,4,5) дає
    # справжні Пн-Пт, а (5,) справжню п'ятницю. Не міняти на (0,1,2,3,4)
    # без повторної перевірки — з тими індексами job фактично спрацьовує
    # в неділю-четвер.
    job_queue = app.job_queue
    job_queue.run_daily(
        morning_reminder_job,
        time=time(hour=10, minute=0, tzinfo=tz),
        days=(1, 2, 3, 4, 5),
        name="morning_reminder",
    )
    # Підсумок дня більше НЕ надсилається за розкладом — миттєве святкове
    # повідомлення при завершенні всіма командою вже покриває цей сценарій
    # (bot/handlers.py, done_command). Тут лишається тільки п'ятничний
    # тижневий підсумок.
    job_queue.run_daily(
        friday_weekly_summary_job,
        time=time(hour=18, minute=0, tzinfo=tz),
        days=(5,),
        name="friday_weekly_summary",
    )

    logger.info(
        "Бот запущено. Тиждень %d/%d. AI: %s. Персистентність: %s.",
        runtime.state.current_week,
        runtime.program.total_weeks,
        "увімкнено" if runtime.config.ai_enabled else "вимкнено",
        "GitHub" if runtime.config.persistence_enabled else "тільки локальний диск",
    )

    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
