"""
Абстрактний базовий клас для всіх тренувальних програм.

Щоб додати нову програму (підтягування, планка, прес тощо):
1. Створити папку programs/<назва>/
2. Додати schedule.json з планом
3. Реалізувати клас, що наслідує Program
4. Зареєструвати у programs/registry.py
"""

from abc import ABC, abstractmethod

from core.models import WorkoutDay


class Program(ABC):
    """Базовий інтерфейс тренувальної програми."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Унікальна назва програми (латиницею, без пробілів)."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Назва для відображення користувачу."""
        ...

    @property
    @abstractmethod
    def total_weeks(self) -> int:
        """Загальна кількість тижнів програми."""
        ...

    @abstractmethod
    def get_workout(self, week: int) -> WorkoutDay:
        """
        Повертає тренування для заданого тижня.

        Args:
            week: Номер тижня (1-indexed).

        Returns:
            WorkoutDay з підходами та інформацією про відпочинок.
        """
        ...

    def is_valid_week(self, week: int) -> bool:
        """Перевіряє чи номер тижня в межах програми."""
        return 1 <= week <= self.total_weeks
