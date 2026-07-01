"""
Обгортка навколо Anthropic API для AI-фіч бота.

Дизайн:
- Якщо ANTHROPIC_API_KEY не заданий, всі функції повертають None,
  і виклики в handlers/jobs мають fallback на статичні фрази.
  Бот ніколи не падає через відсутність або збій AI.
- Використовує AsyncAnthropic, бо весь бот асинхронний (python-telegram-bot).
"""

from __future__ import annotations

import logging

from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

MAX_TOKENS = 500

SYSTEM_PROMPT_BASE = """Ти — дружній помічник у Telegram-групі друзів, які разом проходять
15-тижневий командний челендж по нарощуванню кількості віджимань (5 підходів на тренування,
кількість повторень зростає щотижня). Твоя роль — підтримувати мотивацію, коротко відповідати
на питання про програму та статистику, і час від часу підколювати учасників по-дружньому.

Правила:
- Відповідай українською мовою, неформально, як свій у компанії друзів.
- Коротко: 1-4 речення, без зайвої води. Це Telegram-чат, не есе.
- Можна використовувати емодзі, але не перебарщуй (1-3 на повідомлення).
- Не вигадуй цифри чи факти, яких немає в контексті нижче — якщо не знаєш, так і скажи.
- Не давай медичних порад (травми, біль тощо) — у таких випадках порадь звернутись до лікаря."""


def _client(api_key: str) -> AsyncAnthropic:
    return AsyncAnthropic(api_key=api_key)


async def answer_question(
    api_key: str,
    model: str,
    question: str,
    context: str,
    asked_by: str,
) -> str | None:
    """
    Відповідає на довільне питання учасника в контексті челенджу.

    Args:
        api_key:  Anthropic API ключ.
        model:    Модель для виклику.
        question: Питання учасника.
        context:  Поточний стан челенджу (тиждень, програма, статистика).
        asked_by: Ім'я того, хто питає.

    Returns:
        Текст відповіді, або None при помилці API (fallback на боці викликача).
    """
    try:
        client = _client(api_key)
        response = await client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=f"{SYSTEM_PROMPT_BASE}\n\nПоточний контекст челенджу:\n{context}",
            messages=[
                {"role": "user", "content": f"{asked_by} питає: {question}"}
            ],
        )
        return "".join(
            block.text for block in response.content if block.type == "text"
        ).strip() or None
    except Exception:
        logger.exception("Помилка виклику Anthropic API (answer_question)")
        return None


async def weekly_analysis(
    api_key: str,
    model: str,
    context: str,
) -> str | None:
    """
    Генерує короткий персоналізований аналіз тижня для п'ятничного підсумку.

    Args:
        api_key: Anthropic API ключ.
        model:   Модель для виклику.
        context: Дані по тижню — хто скільки виконав, який тиждень програми.

    Returns:
        Текст аналізу (2-4 речення), або None при помилці.
    """
    try:
        client = _client(api_key)
        response = await client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT_BASE,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Ось результати тижня по учасниках челенджу:\n\n"
                        f"{context}\n\n"
                        "Напиши короткий (2-4 речення) дружній аналіз тижня: відзнач того, "
                        "хто впорався найкраще, легко підколи того, хто відстає (без злості), "
                        "і додай мотивацію на наступний тиждень."
                    ),
                }
            ],
        )
        return "".join(
            block.text for block in response.content if block.type == "text"
        ).strip() or None
    except Exception:
        logger.exception("Помилка виклику Anthropic API (weekly_analysis)")
        return None
