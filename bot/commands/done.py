"""
Команда /done — відмічає користувача як такого, що виконав тренування.

Логіка:
1. Знаходить учасника за Telegram username
2. Відмічає його у state.json
3. Якщо всі виконали — надсилає святкове повідомлення
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from core.config import Config
from core.models import Participant
from core.state import load_state, save_state
from messages.formatter import (
    format_all_done_message,
    format_already_done_message,
    format_done_message,
)
from messages.selector import pick_phrase

logger = logging.getLogger(__name__)


def _find_participant(
    user_username: str | None,
    participants: list[Participant],
) -> Participant | None:
    """
    Шукає учасника за Telegram username.

    Порівнює без урахування регістру.
    Символ @ у конфігурації або у username Telegram ігнорується.

    Args:
        user_username: Telegram username користувача (без @).
        participants:  Список учасників з конфігурації.

    Returns:
        Знайдений Participant або None.
    """
    if not user_username:
        return None

    incoming = user_username.lower().lstrip("@")
    for participant in participants:
        if participant.username.lower() == incoming:
            return participant

    return None


async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник команди /done."""
    config: Config = context.bot_data["config"]
    user = update.effective_user

    participant = _find_participant(
        user_username=user.username,
        participants=config.participants,
    )

    if participant is None:
        detected = f"@{user.username}" if user.username else "невідомо (username не встановлено)"
        logger.warning(
            "Невідомий користувач: username=%s, first_name=%s",
            user.username,
            user.first_name,
        )
        await update.message.reply_text(
            f"❓ Не знайшов тебе у списку учасників.\n\n"
            f"Твій Telegram username: {detected}\n\n"
            f"Перевір PARTICIPANTS у .env."
        )
        return

    state = load_state()
    record = state.get_today_record()

    if participant.name in record.completed:
        await update.message.reply_text(format_already_done_message(participant.name))
        return

    state.mark_done(participant.name)
    save_state(state)

    logger.info("✅ %s (@%s) completed workout", participant.name, participant.username)

    record = state.get_today_record()
    all_done = set(record.completed) >= set(config.participant_names)

    if all_done and not record.all_notified:
        record.all_notified = True

        celebration, new_history = pick_phrase(state, "team_done", config.phrase_history_size)
        state.recent_phrases["team_done"] = new_history
        save_state(state)

        await update.message.reply_text(
            format_all_done_message(celebration, config.participant_names)
        )
    else:
        await update.message.reply_text(
            format_done_message(participant.name, config.participant_names, record.completed)
        )
