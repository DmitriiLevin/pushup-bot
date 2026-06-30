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
        }

    def get_today_record(self) -> DayRecord:
        """Повертає запис за сьогодні (або порожній, якщо немає)."""
        today = date.today().isoformat()
        return self.daily.get(today, DayRecord())

    def get_or_create_today_record(self) -> DayRecord:
        """Повертає або створює запис за сьогодні."""
        today = date.today().isoformat()
        if today not in self.daily:
            self.daily[today] = DayRecord()
        return self.daily[today]

    def mark_done(self, participant: str) -> DayRecord:
        """Відмічає учасника як такого, що виконав тренування."""
        record = self.get_or_create_today_record()
        if participant not in record.completed:
            record.completed.append(participant)
        return record
