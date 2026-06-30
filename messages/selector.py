"""
Вибір фрази без повтору (anti-repeat логіка з history).

Логіка:
- Визначає категорію за днем тижня
- Вибирає випадковий індекс, якого немає в recent_phrases[category]
- Повертає текст фрази та оновлений список останніх індексів
- Зберігається у AppState (персистентно між перезапусками)
"""

from __future__ import annotations

import logging
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from core.models import AppState
from messages.phrases import ALL_PHRASES

logger = logging.getLogger(__name__)

_KYIV_TZ = ZoneInfo("Europe/Kyiv")


def get_day_category(dt: datetime | None = None) -> str:
    """
    Повертає категорію фраз залежно від дня тижня.

    Returns:
        'monday' | 'friday' | 'weekend' | 'regular'
    """
    now = dt or datetime.now(tz=_KYIV_TZ)
    weekday = now.weekday()  # 0=Monday, 6=Sunday

    if weekday == 0:
        return "monday"
    if weekday == 4:
        return "friday"
    if weekday >= 5:
        return "weekend"
    return "regular"


def pick_phrase(state: AppState, category: str, history_size: int) -> tuple[str, list[int]]:
    """
    Вибирає фразу з категорії, уникаючи нещодавно використаних.

    Args:
        state:        Поточний стан застосунку.
        category:     Категорія фрази.
        history_size: Кількість останніх індексів, які не повторюються.

    Returns:
        Кортеж (текст фрази, оновлений список recent indices).
    """
    phrases = ALL_PHRASES.get(category, ALL_PHRASES["regular"])
    recent: list[int] = list(state.recent_phrases.get(category, []))

    if len(phrases) == 1:
        return phrases[0], [0]

    # Якщо всі фрази у recent — очищаємо (не дамо застрягти)
    available_indices = [i for i in range(len(phrases)) if i not in recent]
    if not available_indices:
        recent = []
        available_indices = list(range(len(phrases)))

    chosen_index = random.choice(available_indices)

    logger.debug(
        "Вибрано фразу [%s][%d]: %s",
        category,
        chosen_index,
        phrases[chosen_index][:40],
    )

    updated_recent = (recent + [chosen_index])[-history_size:]
    return phrases[chosen_index], updated_recent


def select_phrase(state: AppState, history_size: int) -> tuple[str, list[int], str]:
    """
    Головна функція: визначає категорію і вибирає фразу.

    Returns:
        Кортеж (текст фрази, оновлений recent list, категорія).
    """
    category = get_day_category()
    phrase, updated_recent = pick_phrase(state, category, history_size)
    return phrase, updated_recent, category
