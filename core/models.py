"""
Dataclasses для всіх доменних об'єктів.
Цей модуль не імпортує нічого з bot/ або programs/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Participant:
    """Учасник челенджу з відображуваним ім'ям та Telegram username."""

    name: str      # Відображуване ім'я: Діма
    username: str  # Telegram username без @: dlevinn


@dataclass
class WorkoutDay:
    """Одне тренування: підходи та час відпочинку."""

    week: int
    sets: list[int]
    rest: str

    @property
    def total(self) -> int:
        """Загальна кількість повторень."""
        return sum(self.sets)


@dataclass
class DayRecord:
    """Запис про виконання тренування за один день."""

    completed: list[str] = field(default_factory=list)
    all_notified: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> DayRecord:
        return cls(
            completed=data.get("completed", []),
            all_notified=data.get("all_notified", False),
        )

    def to_dict(self) -> dict:
        return {
            "completed": self.completed,
            "all_notified": self.all_notified,
        }


@dataclass
class AppState:
    """Повний стан застосунку, що зберігається у state.json."""

    current_week: int = 1
    current_program: str = "pushups"
    recent_phrases: dict[str, list[int]] = field(default_factory=dict)
    daily: dict[str, DayRecord] = field(default_factory=dict)
    update_offset: int = 0
    last_advanced_on: str | None = None
    challenge_completed_announced: bool = False
    intro_announced: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> AppState:
        daily = {
            day_str: DayRecord.from_dict(record)
            for day_str, record in data.get("daily", {}).items()
        }
        return cls(
            current_week=data.get("current_week", 1),
            current_program=data.get("current_program", "pushups"),
            recent_phrases=data.get("recent_phrases", {}),
            daily=daily,
            update_offset=data.get("update_offset", 0),
            last_advanced_on=data.get("last_advanced_on"),
            challenge_completed_announced=data.get("challenge_completed_announced", False),
            intro_announced=data.get("intro_announced", False),
        )

    def to_dict(self) -> dict:
        return {
            "current_week": self.current_week,
            "current_program": self.current_program,
            "recent_phrases": self.recent_phrases,
            "daily": {
                day_str: record.to_dict()
                for day_str, record in self.daily.items()
            },
            "update_offset": self.update_offset,
            "last_advanced_on": self.last_advanced_on,
            "challenge_completed_announced": self.challenge_completed_announced,
            "intro_announced": self.intro_announced,
        }

    def get_today_record(self, today: date) -> DayRecord:
        """Повертає запис за вказану дату (або порожній, якщо немає).

        Args:
            today: Календарна дата, обчислена через core.clock.local_today()
                   з урахуванням потрібного часового поясу — НЕ date.today().
        """
        return self.daily.get(today.isoformat(), DayRecord())

    def get_or_create_today_record(self, today: date) -> DayRecord:
        """Повертає або створює запис за вказану дату.

        Args:
            today: Календарна дата, обчислена через core.clock.local_today().
        """
        today_str = today.isoformat()
        if today_str not in self.daily:
            self.daily[today_str] = DayRecord()
        return self.daily[today_str]

    def mark_done(self, participant: str, today: date) -> DayRecord:
        """Відмічає учасника як такого, що виконав тренування за вказану дату."""
        record = self.get_or_create_today_record(today)
        if participant not in record.completed:
            record.completed.append(participant)
        return record
