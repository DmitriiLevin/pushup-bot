"""
Реалізація 15-тижневої програми віджимань.
Завантажує план з schedule.json.
"""

import json
import logging
from pathlib import Path

from core.models import WorkoutDay
from programs.base import Program

logger = logging.getLogger(__name__)

_SCHEDULE_PATH = Path(__file__).parent / "schedule.json"


class PushupsProgram(Program):
    """15-тижнева прогресивна програма віджимань."""

    def __init__(self) -> None:
        self._schedule = self._load_schedule()

    def _load_schedule(self) -> dict:
        with open(_SCHEDULE_PATH, encoding="utf-8") as f:
            return json.load(f)

    @property
    def name(self) -> str:
        return "pushups"

    @property
    def display_name(self) -> str:
        return self._schedule["display_name"]

    @property
    def total_weeks(self) -> int:
        return self._schedule["total_weeks"]

    @property
    def rest(self) -> str:
        return self._schedule["rest"]

    def get_workout(self, week: int) -> WorkoutDay:
        """
        Повертає тренування для заданого тижня.

        Args:
            week: Номер тижня (1–15).

        Returns:
            WorkoutDay із підходами та відпочинком.

        Raises:
            ValueError: Якщо тиждень поза межами програми.
        """
        if not self.is_valid_week(week):
            raise ValueError(
                f"Тиждень {week} поза межами програми (1–{self.total_weeks})"
            )

        week_data = self._schedule["weeks"][week - 1]
        return WorkoutDay(
            week=week,
            sets=week_data["sets"],
            rest=self._schedule["rest"],
        )
