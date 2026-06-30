#!/usr/bin/env python3
"""
Щоденне нагадування: надсилає тренування або повідомлення про відпочинок.

Запускається GitHub Actions о 12:00 Europe/Warsaw (Пн–Пт).
Оновлює стан фраз і зберігає data/state.json.
"""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

from core.config import Config
from core.state import load_state, save_state
from messages.formatter import format_weekend_message, format_workout_message
from messages.selector import select_phrase
from programs.registry import get_program

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def send_message(bot_token: str, chat_id: int, text: str) -> None:
    """Надсилає повідомлення через Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": chat_id, "text": text},
        timeout=30,
    )
    resp.raise_for_status()
    logger.info("Повідомлення надіслано (%d символів)", len(text))


def main() -> None:
    config = Config.from_env()
    state = load_state()

    phrase, updated_recent, category = select_phrase(state, config.phrase_history_size)
    state.recent_phrases[category] = updated_recent

    if category == "weekend":
        text = format_weekend_message(phrase)
        save_state(state)
        send_message(config.bot_token, config.chat_id, text)
        logger.info("Повідомлення про вихідний надіслано")
        return

    program = get_program(state.current_program)
    workout = program.get_workout(state.current_week)
    text = format_workout_message(phrase, workout)

    save_state(state)
    send_message(config.bot_token, config.chat_id, text)
    logger.info(
        "Нагадування надіслано: тиждень %d, %d повторень",
        workout.week,
        workout.total,
    )


if __name__ == "__main__":
    main()
