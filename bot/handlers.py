"""
Живі обробники команд Telegram-бота.

На відміну від старої версії (GitHub Actions, обробка раз на 18:00),
тут кожна команда виконується миттєво, коли учасник її надсилає.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from bot.shared import Runtime
from core import ai_client
from messages.formatter import (
    format_already_done_message,
    format_all_done_message,
    format_done_message,
    format_help_message,
    format_motivation_message,
    format_rest_day_today,
    format_status_message,
    format_today_workout,
    format_week_message,
)
from messages.phrases import ALL_PHRASES
from messages.selector import pick_phrase

logger = logging.getLogger(__name__)


def _runtime(context: ContextTypes.DEFAULT_TYPE) -> Runtime:
    return context.application.bot_data["runtime"]


def _username_to_name(runtime: Runtime) -> dict[str, str]:
    return {p.username.lower(): p.name for p in runtime.config.participants}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await help_command(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime = _runtime(context)
    text = format_help_message("10:00", runtime.config.timezone)
    await update.message.reply_text(text)


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime = _runtime(context)
    if runtime.today.weekday() >= 5:
        await update.message.reply_text(format_rest_day_today())
        return
    program = runtime.program
    workout = program.get_workout(runtime.state.current_week)
    await update.message.reply_text(format_today_workout(workout))


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime = _runtime(context)
    names = runtime.config.participant_names
    record = runtime.state.get_today_record(runtime.today)
    completed = record.completed if record else []
    text = (
        f"📊 Сьогодні виконали {len(completed)}/{len(names)}:\n\n"
        f"{format_status_message(names, completed)}"
    )
    await update.message.reply_text(text)


async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime = _runtime(context)
    program = runtime.program
    text = format_week_message(runtime.state.current_week, program.total_weeks, program.display_name)
    await update.message.reply_text(text)


async def motivation_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime = _runtime(context)
    phrase, updated = pick_phrase(runtime.state, "motivation", runtime.config.phrase_history_size)
    runtime.state.recent_phrases["motivation"] = updated
    await update.message.reply_text(format_motivation_message(phrase))
    await runtime.persist("motivation phrase used")


async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime = _runtime(context)
    user = update.message.from_user
    username = (user.username or "").lower()
    name = _username_to_name(runtime).get(username)

    if not name:
        await update.message.reply_text(
            "🤔 Не знайшов тебе у списку учасників. Перевір, що твій Telegram "
            "username доданий у PARTICIPANTS (звернись до адміна групи)."
        )
        return

    names = runtime.config.participant_names
    record = runtime.state.get_or_create_today_record(runtime.today)

    if name in record.completed:
        await update.message.reply_text(format_already_done_message(name))
        return

    record.completed.append(name)
    all_done = len(record.completed) == len(names)

    await update.message.reply_text(format_done_message(name, names, record.completed))

    # Святкове повідомлення "всі виконали" — це, по суті, "вечірній підсумок",
    # тільки миттєвий, а не по розкладу. У вихідні бот нічого не пише сам
    # (навіть це), тому обмежуємо буднями — так само, як і решту проактивних
    # повідомлень. Сам /done при цьому все одно працює в будь-який день.
    if all_done and runtime.today.weekday() < 5:
        celebration, updated = pick_phrase(runtime.state, "team_done", runtime.config.phrase_history_size)
        runtime.state.recent_phrases["team_done"] = updated
        await update.message.reply_text(format_all_done_message(celebration, names))

    await runtime.persist(f"{name} marked /done")


def _match_participant(runtime: Runtime, raw: str) -> str | None:
    """Шукає учасника за ім'ям або @username (без урахування регістру)."""
    key = raw.strip().lstrip("@").lower()
    for name in runtime.config.participant_names:
        if name.lower() == key:
            return name
    return _username_to_name(runtime).get(key)


async def undone_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Скасовує відмітку /done за сьогодні.

    Без аргументів — скасовує власну відмітку (за Telegram username того,
    хто пише). З аргументом — /undone Ім'я — скасовує відмітку будь-кого
    з команди, щоб не залежати від того, хто саме помилково відмітив."""
    runtime = _runtime(context)
    names = runtime.config.participant_names
    record = runtime.state.get_or_create_today_record(runtime.today)

    if context.args:
        raw_target = " ".join(context.args)
        target_name = _match_participant(runtime, raw_target)
        if target_name is None:
            await update.message.reply_text(
                f"🤔 Не знайшов учасника '{raw_target}'.\nУчасники: {', '.join(names)}"
            )
            return
    else:
        user = update.message.from_user
        username = (user.username or "").lower()
        target_name = _username_to_name(runtime).get(username)
        if not target_name:
            await update.message.reply_text(
                "🤔 Не знайшов тебе у списку учасників, тому не знаю, чию відмітку знімати.\n"
                f"Можеш вказати ім'я явно: /undone {names[0]}"
            )
            return

    if target_name not in record.completed:
        await update.message.reply_text(f"У {target_name} й так немає відмітки за сьогодні 🤷")
        return

    record.completed.remove(target_name)
    await update.message.reply_text(
        f"↩️ Відмітку {target_name} за сьогодні скасовано.\n\n"
        f"{format_status_message(names, record.completed)}"
    )
    await runtime.persist(f"{target_name}'s /done undone")


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime = _runtime(context)
    question = " ".join(context.args) if context.args else ""
    if not question:
        await update.message.reply_text(
            "Напиши питання після команди, наприклад:\n/ask скільки ще тижнів залишилось?"
        )
        return
    await _answer_ai_question(update, runtime, question)


async def mention_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Реагує, коли бота згадали (@username) або відповіли на його повідомлення."""
    runtime = _runtime(context)
    message = update.message
    if not message or not message.text:
        return

    bot_username = context.bot.username or ""
    is_mention = bool(bot_username) and f"@{bot_username.lower()}" in message.text.lower()
    is_reply_to_bot = (
        message.reply_to_message is not None
        and message.reply_to_message.from_user is not None
        and message.reply_to_message.from_user.id == context.bot.id
    )
    if not (is_mention or is_reply_to_bot):
        return

    question = message.text.replace(f"@{bot_username}", "").strip()
    if not question:
        return
    await _answer_ai_question(update, runtime, question)


async def _answer_ai_question(update: Update, runtime: Runtime, question: str) -> None:
    if not runtime.config.ai_enabled:
        await update.message.reply_text(
            "🤖 AI-відповіді ще не увімкнені — треба додати ANTHROPIC_API_KEY у налаштування бота."
        )
        return

    await update.message.chat.send_action(ChatAction.TYPING)

    asked_by = update.message.from_user.first_name or update.message.from_user.username or "хтось"
    context_str = runtime.build_ai_context()
    answer = await ai_client.answer_question(
        runtime.config.anthropic_api_key,  # type: ignore[arg-type]
        runtime.config.ai_model,
        question,
        context_str,
        asked_by,
    )
    if answer is None:
        answer = "🤖 Щось пішло не так із запитом до AI. Спробуй ще раз трохи пізніше."
    await update.message.reply_text(answer)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Необроблена помилка при обробці update: %s", update, exc_info=context.error)
