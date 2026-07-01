"""
Заплановані завдання бота: ранкове нагадування, вечірній статус,
п'ятничний підсумок тижня. Раніше це були окремі GitHub Actions
cron-запуски; тепер це JobQueue живого процесу — з коректним
урахуванням часового поясу (без ручного перерахунку UTC/DST).
"""

from __future__ import annotations

import logging
import random
from datetime import date, datetime, timedelta
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
    """Щоденне нагадування о 12:00 Пн-Пт. Перед відправкою автоматично
    просуває тиждень програми, якщо сьогодні понеділок. Після завершення
    15-тижневого челенджу — надсилає одноразове привітання і більше
    нічого не робить у наступні дні."""
    runtime = _runtime(context)

    if runtime.state.challenge_completed_announced:
        return

    program = runtime.program
    result = maybe_advance_week(runtime.state, program.total_weeks)

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


async def evening_status_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Вечірній статус о 18:00 Пн-Пт. /done тепер обробляється миттєво
    живим handler-ом, тож тут просто підбивається підсумок дня.
    У п'ятницю додатково надсилається підсумок тижня з AI-аналізом."""
    runtime = _runtime(context)

    if runtime.state.challenge_completed_announced:
        return

    names = runtime.config.participant_names
    today = date.today()
    today_str = today.isoformat()
    record = runtime.state.daily.get(today_str, DayRecord())
    completed = record.completed
    count = len(completed)
    total = len(names)

    status_lines = "\n".join(
        f"{'🟢' if n in completed else '⚪'} {n}" for n in names
    )
    status_text = (
        f"📊 Підсумок дня\n\n{SEPARATOR}\n\n"
        f"Виконали {count}/{total}:\n\n{status_lines}"
    )
    if count == total and total > 0:
        status_text += "\n\n🏆 Всі виконали! Так тримати!"

    await context.bot.send_message(runtime.config.chat_id, status_text)
    logger.info("Статус дня надіслано: %d/%d виконали", count, total)

    if today.weekday() == 4:  # п'ятниця
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

    await runtime.persist("evening status processed")


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
