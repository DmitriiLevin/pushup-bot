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
    timezone: str
    anthropic_api_key: str | None
    ai_model: str
    ai_enabled: bool
    github_token: str | None
    github_repo: str | None

    @property
    def participant_names(self) -> list[str]:
        """Список відображуваних імен учасників."""
        return [p.name for p in self.participants]

    @property
    def persistence_enabled(self) -> bool:
        """Чи налаштована git-персистентність стану (переживає передеплой)."""
        return bool(self.github_token and self.github_repo)

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

        timezone = os.getenv("TIMEZONE", "Europe/Warsaw").strip()

        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip() or None
        ai_model = os.getenv("AI_MODEL", "claude-haiku-4-5-20251001").strip()
        ai_enabled = anthropic_api_key is not None

        github_token = os.getenv("GITHUB_TOKEN", "").strip() or None
        github_repo = os.getenv("GITHUB_REPO", "").strip() or None

        return cls(
            bot_token=bot_token,
            chat_id=chat_id,
            participants=participants,
            phrase_history_size=phrase_history_size,
            timezone=timezone,
            anthropic_api_key=anthropic_api_key,
            ai_model=ai_model,
            ai_enabled=ai_enabled,
            github_token=github_token,
            github_repo=github_repo,
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
