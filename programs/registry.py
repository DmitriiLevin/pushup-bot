"""
Реєстр тренувальних програм.

Щоб додати нову програму:
1. Імпортуй клас
2. Додай до REGISTRY

Більше нічого змінювати не потрібно.
"""

from programs.base import Program
from programs.pushups.program import PushupsProgram

REGISTRY: dict[str, Program] = {
    "pushups": PushupsProgram(),
}


def get_program(name: str) -> Program:
    """
    Повертає програму за назвою.

    Raises:
        KeyError: Якщо програма не знайдена.
    """
    if name not in REGISTRY:
        available = ", ".join(REGISTRY.keys())
        raise KeyError(
            f"Програма '{name}' не знайдена. Доступні: {available}"
        )
    return REGISTRY[name]
