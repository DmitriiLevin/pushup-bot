"""
Точка входу застосунку.

Запуск:
    python main.py
"""

import asyncio
import logging
import sys

from bot.app import create_app
from core.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Завантажує конфігурацію, створює та запускає бота."""
    logger.info("Запуск Pushup Bot...")

    try:
        config = Config.from_env()
    except ValueError as e:
        logger.critical("Помилка конфігурації: %s", e)
        sys.exit(1)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = create_app(config)

    logger.info("Бот запущено. Очікування повідомлень...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
