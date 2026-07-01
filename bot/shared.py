"""
Спільний рантайм-контекст бота: конфіг, стан, поточна програма.

Зберігається в application.bot_data["runtime"] і доступний з усіх
handlers та jobs через context.application.bot_data["runtime"].
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

from core.config import Config
from core.models import AppState
from core.persistence import commit_and_push
from core.state import save_state
from programs.base import Program
from programs.registry import get_program

logger = logging.getLogger(__name__)


@dataclass
class Runtime:
    config: Config
    state: AppState

    @property
    def program(self) -> Program:
        return get_program(self.state.current_program)

    def today_record_completed(self) -> list[str]:
        return self.state.daily.get(date.today().isoformat())

    async def persist(self, reason: str) -> None:
        """Зберігає стан локально і (якщо налаштовано) пушить у GitHub."""
        save_state(self.state)
        if self.config.persistence_enabled:
            try:
                await commit_and_push(
                    self.config.github_token,  # type: ignore[arg-type]
                    self.config.github_repo,  # type: ignore[arg-type]
                    reason,
                )
            except Exception:
                logger.exception("Не вдалось запушити стан у GitHub (%s)", reason)

    def build_ai_context(self) -> str:
        """Формує текстовий опис поточного стану для передачі в AI як контекст."""
        program = self.program
        today = date.today()
        today_record = self.state.daily.get(today.isoformat())
        completed_today = today_record.completed if today_record else []
        names = self.config.participant_names

        lines = [
            f"Програма: {program.display_name}",
            f"Поточний тиждень: {self.state.current_week} з {program.total_weeks}",
            f"Учасники: {', '.join(names)}",
            f"Сьогодні ({today.isoformat()}) виконали: "
            + (", ".join(completed_today) if completed_today else "поки ніхто"),
        ]
        if program.is_valid_week(self.state.current_week):
            workout = program.get_workout(self.state.current_week)
            lines.append(f"Сьогоднішнє тренування: {workout.sets}, всього {workout.total} повторень")
        return "\n".join(lines)
