"""
Заплановані завдання бота: ранкове нагадування (10:00), фото-чекпоінт
кожні 4 тижні (8:30, тільки в понеділок) і п'ятничний підсумок тижня
(18:00) — це єдині типи повідомлень, які бот пише сам, без команди
від людини. Раніше це були окремі GitHub Actions cron-запуски; тепер
це JobQueue живого процесу — з коректним урахуванням часового поясу
(без ручного перерахунку UTC/DST).

Немає окремого "вечірнього статусу" щодня: коли останній учасник
відмічає /done, святкове повідомлення (і опитування про складність)
надсилається одразу, миттєво (bot/handlers.py, done_command) — а не
за розкладом і не якщо не всі встигли.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from telegram.ext import ContextTypes

from bot.shared import Runtime
from core import ai_client
from core.models import DayRecord
from core.week import WeekAdvanceResult, maybe_advance_week
from messages.formatter import format_weekend_message, format_weekly_summary, format_workout_message
from messages.selector import select_phrase

logger = logging.getLogger(__name__)

SEPARATOR = "━━━━━━━━━━━━━━"

# Раз на скільки тижнів просити фото прогресу (5, 9, 13-й тиждень і т.д.)
PHOTO_CHECKPOINT_EVERY_N_WEEKS = 4

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

    Це другий і останній тип проактивного повідомлення від бота
    (перший — ранкове нагадування). Жодних інших автоматичних
    повідомлень бот не надсилає — тільки відповіді на команди."""
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


async def photo_checkpoint_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """О 8:30, тільки в понеділок — раз на PHOTO_CHECKPOINT_EVERY_N_WEEKS
    тижнів (тобто на старті 5, 9, 13-го тижня) просить усіх скинути фото
    прогресу. Спрацьовує ДО ранкового нагадування (яке о 10:00 і саме
    підвищує current_week), тому на момент виклику current_week ще
    дорівнює щойно завершеному тижню (4, 8, 12) — це і є умова
    спрацювання, окремий прапорець "чи вже надсилали" не потрібен,
    бо ця конкретна комбінація тиждень+понеділок трапляється рівно
    раз за весь челендж."""
    runtime = _runtime(context)

    if runtime.state.challenge_completed_announced:
        return

    today = runtime.today
    if today.weekday() != 0:  # тільки понеділок
        return

    week = runtime.state.current_week
    program = runtime.program
    if week % PHOTO_CHECKPOINT_EVERY_N_WEEKS != 0 or week >= program.total_weeks:
        return

    next_week = week + 1
    text = (
        f"📸 Тиждень {next_week} починається!\n\n"
        f"{SEPARATOR}\n\n"
        f"Позаду {week} {'тижні' if week in (2, 3, 4) else 'тижнів'} тренувань — час зробити "
        f"фото прогресу 💪\n\n"
        f"Скиньте сюди своє фото, щоб бачити зміни за цей час. "
        f"Порівняти буде з чим 😉"
    )
    await context.bot.send_message(runtime.config.chat_id, text)
    logger.info("Фото-чекпоінт надіслано: завершено %d тижнів", week)
    await runtime.persist("photo checkpoint sent")
