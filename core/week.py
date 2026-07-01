"""
Автоматичне просування тижня програми.

Раніше `current_week` треба було редагувати вручну в state.json.
Тепер: щопонеділка (перед ранковим нагадуванням) бот сам перевіряє,
чи минув новий тиждень, і піднімає current_week, поки не досягне
total_weeks. Захищено від подвійного інкременту в один день
(наприклад, при перезапуску процесу) через last_advanced_on.

Коли останній тиждень (total_weeks) уже пройшов і настав понеділок,
коли мало б статись чергове просування — це і є момент завершення
челенджу. Функція сигналізує це один-єдиний раз через
challenge_completed_announced, щоб викликач міг надіслати вітання
рівно один раз і після цього більше нічого не надсилати.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from core.models import AppState


class WeekAdvanceResult(Enum):
    UNCHANGED = "unchanged"    # звичайний день, нічого не змінилось
    ADVANCED = "advanced"      # тиждень піднято на 1
    COMPLETED = "completed"    # челендж щойно повністю завершився (одноразово)


def maybe_advance_week(
    state: AppState, total_weeks: int, today: date | None = None
) -> WeekAdvanceResult:
    """
    Просуває current_week на 1, якщо сьогодні понеділок і тиждень
    ще не було просунуто сьогодні. Повертає, що саме відбулось.

    Args:
        state:       Поточний стан застосунку (мутується на місці).
        total_weeks: Загальна кількість тижнів програми.
        today:       Дата "сьогодні" (для тестів); за замовчуванням date.today().
    """
    today = today or date.today()
    today_str = today.isoformat()

    if today.weekday() != 0:  # 0 = понеділок
        return WeekAdvanceResult.UNCHANGED

    if state.last_advanced_on == today_str:
        return WeekAdvanceResult.UNCHANGED

    if state.current_week >= total_weeks:
        state.last_advanced_on = today_str
        if not state.challenge_completed_announced:
            state.challenge_completed_announced = True
            return WeekAdvanceResult.COMPLETED
        return WeekAdvanceResult.UNCHANGED

    state.current_week += 1
    state.last_advanced_on = today_str
    return WeekAdvanceResult.ADVANCED
