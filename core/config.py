"""
Конфігурація застосунку з .env файлу.
Єдине місце, де читаються змінні оточення.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

from core.models import Participant


@dataclass(frozen=True)
class Config:
    """Незмінна конфігурація, завантажена з .env."""

    bot_token: str
    chat_id: int
    participants: list[Participant]
    reminder_time: time
    reminder_timezone: str
    friday_summary_time: time
    phrase_history_size: int

    @property
    def participant_names(self) -> list[str]:
        """Список відображуваних імен учасників."""
        return [p.name for p in self.participants]

    @classmethod
    def from_env(cls) -> Config:
        """Завантажує конфігурацію зі змінних оточення."""
        load_dotenv()

        bot_token = os.getenv("BOT_TOKEN", "").strip()
        if not bot_token:
            raise ValueError("BOT_TOKEN не встановлено у .env")

        chat_id_str = os.getenv("CHAT_ID", "").strip()
        if not chat_id_str:
            raise ValueError("CHAT_ID не встановлено у .env")

        try:
            chat_id = int(chat_id_str)
        except ValueError:
            raise ValueError(f"CHAT_ID має бути числом, отримано: '{chat_id_str}'")

        participants_str = os.getenv("PARTICIPANTS", "").strip()
        if not participants_str:
            raise ValueError("PARTICIPANTS не встановлено у .env")

        participants = _parse_participants(participants_str)
        if not participants:
            raise ValueError("PARTICIPANTS порожній після парсингу")

        reminder_timezone = os.getenv("REMINDER_TIMEZONE", "Europe/Warsaw").strip()
        try:
            tz = ZoneInfo(reminder_timezone)
        except ZoneInfoNotFoundError:
            raise ValueError(f"Невідома timezone: '{reminder_timezone}'")

        reminder_time_str = os.getenv("REMINDER_TIME", "12:00").strip()
        try:
            hour, minute = (int(p) for p in reminder_time_str.split(":"))
            reminder_time = time(hour, minute, tzinfo=tz)
        except (ValueError, TypeError):
            raise ValueError(
                f"REMINDER_TIME має бути у форматі HH:MM, отримано: '{reminder_time_str}'"
            )

        friday_summary_time_str = os.getenv("FRIDAY_SUMMARY_TIME", "18:00").strip()
        try:
            fh, fm = (int(p) for p in friday_summary_time_str.split(":"))
            friday_summary_time = time(fh, fm, tzinfo=tz)
        except (ValueError, TypeError):
            raise ValueError(
                f"FRIDAY_SUMMARY_TIME має бути у форматі HH:MM, отримано: '{friday_summary_time_str}'"
            )

        phrase_history_size_str = os.getenv("PHRASE_HISTORY_SIZE", "10").strip()
        try:
            phrase_history_size = int(phrase_history_size_str)
            if phrase_history_size < 1:
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError(
                f"PHRASE_HISTORY_SIZE має бути позитивним числом, отримано: '{phrase_history_size_str}'"
            )

        return cls(
            bot_token=bot_token,
            chat_id=chat_id,
            participants=participants,
            reminder_time=reminder_time,
            reminder_timezone=reminder_timezone,
            friday_summary_time=friday_summary_time,
            phrase_history_size=phrase_history_size,
        )


def _parse_participants(raw: str) -> list[Participant]:
    """
    Парсить рядок учасників у форматі 'Діма=@dlevinn,Толя=@anatoliireva'.

    Args:
        raw: Рядок зі змінної PARTICIPANTS.

    Returns:
        Список Participant з name і username.

    Raises:
        ValueError: Якщо формат неправильний.
    """
    participants = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if "=" not in entry:
            raise ValueError(
                f"Неправильний формат учасника: '{entry}'. "
                "Використовуй формат: Діма=@dlevinn"
            )
        name, username_raw = entry.split("=", 1)
        name = name.strip()
        username = username_raw.strip().lstrip("@")
        if not name or not username:
            raise ValueError(
                f"Порожнє ім'я або username у: '{entry}'"
            )
        participants.append(Participant(name=name, username=username))
    return participants
