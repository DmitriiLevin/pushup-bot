"""
Єдина точка читання та запису state.json.

Атомарний запис через temp-файл + os.replace() гарантує,
що state.json ніколи не буде пошкоджений при раптовому зупиненні процесу.
"""

import json
import logging
import os
import tempfile
from pathlib import Path

from core.models import AppState

logger = logging.getLogger(__name__)

STATE_FILE = Path("data/state.json")


def load_state() -> AppState:
    """Завантажує стан з диску. Якщо файл відсутній — повертає початковий стан."""
    if not STATE_FILE.exists():
        logger.info("state.json не знайдено, створюємо початковий стан")
        return AppState()

    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return AppState.from_dict(data)
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Помилка читання state.json: %s. Використовуємо початковий стан.", e)
        return AppState()


def save_state(state: AppState) -> None:
    """Атомарно зберігає стан на диск."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = state.to_dict()

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=STATE_FILE.parent,
            delete=False,
            suffix=".tmp",
            encoding="utf-8",
        ) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp_path = tmp.name

        os.replace(tmp_path, STATE_FILE)
        logger.debug("state.json збережено успішно")
    except OSError as e:
        logger.error("Помилка запису state.json: %s", e)
        raise
