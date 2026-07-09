"""
Заплановані завдання бота: ранкове нагадування (10:00), п'ятничний
підсумок тижня (18:00). Раніше це були окремі GitHub Actions
cron-запуски; тепер це JobQueue живого процесу — з коректним
урахуванням часового поясу (без ручного перерахунку UTC/DST).

Немає окремого "вечірнього статусу" щодня: коли останній учасник
відмічає /done, святкове повідомлення надсилається одразу, миттєво
(bot/handlers.py, done_command) — а не за розкладом і не якщо не всі
встигли.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram.ext import ContextTypes

from bot.shared import Runtime
from core import ai_client
from core.models import DayRecord
from core.week import WeekAdvanceResult, maybe_advance_week
from messages.formatter import format_weekend_message, format_weekly_summary, format_workout_message
from messages.selector import pick_phrase, select_phrase

logger = logging.getLogger(__name__)

SEPARATOR = "━━━━━━━━━━━━━━"

# Вітальні повідомлення "просто так": шанс спрацювання при кожній щогодинній
# перевірці в активні години. 0.06 * ~11 активних годин ≈ 1 повідомлення
# на 1.5 доби в середньому — тобто дійсно "іноді", а не щогодини.
GREETING_ACTIVE_HOURS = range(10, 21)  # 10:00–20:59 за локальним часом
GREETING_CHANCE = 0.06

CHALLENGE_COMPLETE_MESSAGE = (
    "🏆 ЧЕЛЕНДЖ ЗАВЕРШЕНО! 🏆\n\n"
    f"{SEPARATOR}\n\n"
    "15 тижнів, сотні підходів, купа поту — і ви дійшли до кінця.\n\n"
    "Це вже не просто цифри в таблиці. Це доказ того, що коли команда "
    "тримається разом — результат буде.\n\n"
    "Дякую, що тренувались зі мною щодня 💪\n"
    "Пишайтесь собою — маєте повне право."
)


def _runtime(context: ContextTypes.DEFAULT_TYPE) -> Runtime:
    return context.application.bot_data["runtime"]


async def morning_reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Щоденне нагадування о 10:00 Пн-Пт. Перед відправкою автоматично
    просуває тиждень програми, якщо сьогодні понеділок. Після завершення
    15-тижневого челенджу — надсилає одноразове привітання і більше
    нічого не робить у наступні дні."""
    runtime = _runtime(context)

    if runtime.state.challenge_completed_announced:
        return

    program = runtime.program
    result = maybe_advance_week(runtime.state, program.total_weeks, runtime.today)

    if result is WeekAdvanceResult.COMPLETED:
        await context.bot.send_message(runtime.config.chat_id, CHALLENGE_COMPLETE_MESSAGE)
        logger.info("Челендж завершено, вітання надіслано")
        await runtime.persist("challenge completed")
        return

    if result is WeekAdvanceResult.ADVANCED:
        logger.info("Тиждень автоматично просунуто до %d", runtime.state.current_week)

    phrase, updated_recent, category = select_phrase(runtime.state, runtime.config.phrase_history_size)
    runtime.state.recent_phrases[category] = updated_recent

    if category == "weekend":
        text = format_weekend_message(phrase)
        await context.bot.send_message(runtime.config.chat_id, text)
        await runtime.persist("morning: weekend message")
        return

    workout = program.get_workout(runtime.state.current_week)
    text = format_workout_message(phrase, workout)
    await context.bot.send_message(runtime.config.chat_id, text)
    logger.info("Ранкове нагадування надіслано: тиждень %d, %d повторень", workout.week, workout.total)
    await runtime.persist("morning reminder sent")


async def friday_weekly_summary_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """О 18:00 щоп'ятниці — підсумок тижня з AI-аналізом.

    Раніше тут ще й щодня (Пн-Пт) надсилався безумовний "Підсумок дня"
    (хто виконав/не виконав) — його прибрано: миттєве святкове
    повідомлення при завершенні всіма командою (bot/handlers.py,
    done_command) вже покриває сценарій "усі виконали", а частковий
    статус ("2 з 3") більше не розсилається сам по собі."""
    runtime = _runtime(context)

    if runtime.state.challenge_completed_announced:
        return

    today = runtime.today
    if today.weekday() != 4:  # тільки п'ятниця
        return

    names = runtime.config.participant_names
    monday = today - timedelta(days=today.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(5)]
    weekly_counts = {
        name: sum(
            1 for d in week_dates
            if name in runtime.state.daily.get(d.isoformat(), DayRecord()).completed
        )
        for name in names
    }

    summary_text = format_weekly_summary(names, weekly_counts, runtime.state.current_week)

    if runtime.config.ai_enabled:
        stats_str = "\n".join(f"{n}: {c}/5 тренувань" for n, c in weekly_counts.items())
        ai_text = await ai_client.weekly_analysis(
            runtime.config.anthropic_api_key,  # type: ignore[arg-type]
            runtime.config.ai_model,
            stats_str,
        )
        if ai_text:
            summary_text += f"\n\n{SEPARATOR}\n\n🤖 {ai_text}"

    await context.bot.send_message(runtime.config.chat_id, summary_text)
    logger.info("П'ятничний підсумок надіслано: %s", weekly_counts)
    await runtime.persist("friday weekly summary sent")


async def greeting_check_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Щогодини перевіряє, чи не написати команді щось невимушене просто так
    (не про тренування). Спрацьовує рідко — див. GREETING_CHANCE вище."""
    runtime = _runtime(context)
    now = datetime.now(tz=ZoneInfo(runtime.config.timezone))

    if now.hour not in GREETING_ACTIVE_HOURS:
        return
    if random.random() > GREETING_CHANCE:
        return

    phrase, updated = pick_phrase(runtime.state, "greetings", runtime.config.phrase_history_size)
    runtime.state.recent_phrases["greetings"] = updated

    await context.bot.send_message(runtime.config.chat_id, phrase)
    logger.info("Випадкове вітання надіслано: %s", phrase)
    await runtime.persist("random greeting sent")
