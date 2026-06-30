"""
Конфігурація застосунку зі змінних оточення.
Єдине місце, де читаються змінні оточення.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from core.models import Participant


@dataclass(frozen=True)
class Config:
    """Незмінна конфігурація, завантажена зі змінних оточення."""

    bot_token: str
    chat_id: int
    participants: list[Participant]
    phrase_history_size: int

    @property
    def participant_names(self) -> list[str]:
        """Список відображуваних імен учасників."""
        return [p.name for p in self.participants]

    @classmethod
    def from_env(cls) -> Config:
        """Завантажує конфігурацію зі змінних оточення (або .env для локальної розробки)."""
        load_dotenv()

        bot_token = os.getenv("BOT_TOKEN", "").strip()
        if not bot_token:
            raise ValueError("BOT_TOKEN не встановлено")

        chat_id_str = os.getenv("CHAT_ID", "").strip()
        if not chat_id_str:
            raise ValueError("CHAT_ID не встановлено")

        try:
            chat_id = int(chat_id_str)
        except ValueError:
            raise ValueError(f"CHAT_ID має бути числом, отримано: '{chat_id_str}'")

        participants_str = os.getenv("PARTICIPANTS", "").strip()
        if not participants_str:
            raise ValueError("PARTICIPANTS не встановлено")

        participants = _parse_participants(participants_str)
        if not participants:
            raise ValueError("PARTICIPANTS порожній після парсингу")

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
            raise ValueError(f"Порожнє ім'я або username у: '{entry}'")
        participants.append(Participant(name=name, username=username))
    return participants
