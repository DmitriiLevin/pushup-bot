"""
Форматування тексту повідомлень.

Відповідає тільки за збірку рядків.
Не знає про Telegram, не зберігає стан.
"""

from __future__ import annotations

from core.models import WorkoutDay

SET_EMOJIS: list[str] = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
SEPARATOR = "━━━━━━━━━━━━━━"


def format_workout_message(phrase: str, workout: WorkoutDay) -> str:
    """
    Формує повідомлення про тренування з гарним форматуванням.

    Args:
        phrase:  Вступна фраза дня.
        workout: Дані тренування (підходи, тиждень, відпочинок).

    Returns:
        Готовий текст для відправки у Telegram.
    """
    sets_lines = "\n".join(
        f"{SET_EMOJIS[i] if i < len(SET_EMOJIS) else f'{i+1}.'} {reps}"
        for i, reps in enumerate(workout.sets)
    )

    return (
        f"{phrase}\n\n"
        f"💪 Сьогодні тренування\n\n"
        f"{SEPARATOR}\n\n"
        f"📅 Тиждень {workout.week}\n\n"
        f"{sets_lines}\n\n"
        f"🔥 Всього: {workout.total}\n\n"
        f"⏱️ Відпочинок\n"
        f"{workout.rest}\n\n"
        f"Після тренування:\n"
        f"/done\n\n"
        f"Успіхів 💪"
    )


def format_weekend_message(phrase: str) -> str:
    """
    Формує повідомлення для вихідного дня.

    Args:
        phrase: Вступна фраза дня.

    Returns:
        Готовий текст для відправки у Telegram.
    """
    return (
        f"{phrase}\n\n"
        f"{SEPARATOR}\n\n"
        f"😴 Сьогодні день відпочинку\n\n"
        f"Відновлюємось.\n"
        f"Набираємось сил.\n\n"
        f"У понеділок знову в бій 💪"
    )


def format_status_message(participants: list[str], completed: list[str]) -> str:
    """
    Формує рядки статусу для кожного учасника.

    Args:
        participants: Список всіх учасників.
        completed:    Список тих, хто вже виконав.

    Returns:
        Рядки з 🟢/⚪ для кожного учасника.
    """
    lines = []
    for participant in participants:
        icon = "🟢" if participant in completed else "⚪"
        lines.append(f"{icon} {participant}")
    return "\n".join(lines)


def format_done_message(
    participant: str,
    participants: list[str],
    completed: list[str],
) -> str:
    """
    Формує повідомлення після того, як учасник відмітив виконання.

    Args:
        participant:  Ім'я учасника, що відмітився.
        participants: Список всіх учасників.
        completed:    Список тих, хто виконав (вже включає participant).

    Returns:
        Готовий текст повідомлення.
    """
    remaining = len(participants) - len(completed)
    status_lines = format_status_message(participants, completed)

    return (
        f"✅ {participant} закрив тренування!\n\n"
        f"{SEPARATOR}\n\n"
        f"Виконали:\n"
        f"{status_lines}\n\n"
        f"Залишилось: {remaining}"
    )


def format_already_done_message(participant: str) -> str:
    """
    Повідомлення коли учасник вже відмітився раніше.

    Args:
        participant: Ім'я учасника.

    Returns:
        Готовий текст повідомлення.
    """
    return (
        f"😄 Спокійно, {participant}!\n\n"
        f"Ти вже сьогодні відмітився 💪"
    )


def format_all_done_message(celebration_phrase: str, participants: list[str]) -> str:
    """
    Святкове повідомлення коли всі учасники виконали тренування.

    Args:
        celebration_phrase: Святкова фраза з TEAM_DONE.
        participants:        Список всіх учасників.

    Returns:
        Готовий текст повідомлення.
    """
    done_lines = "\n".join(f"🟢 {p}" for p in participants)

    return (
        f"{celebration_phrase}\n\n"
        f"{SEPARATOR}\n\n"
        f"{done_lines}"
    )


def format_today_workout(workout: WorkoutDay) -> str:
    """
    Коротка картка тренування для команди /today.

    Args:
        workout: Дані тренування.

    Returns:
        Текст картки тренування.
    """
    sets_lines = "\n".join(
        f"{SET_EMOJIS[i] if i < len(SET_EMOJIS) else f'{i+1}.'} {reps}"
        for i, reps in enumerate(workout.sets)
    )

    return (
        f"💪 Тренування\n\n"
        f"{SEPARATOR}\n\n"
        f"📅 Тиждень {workout.week}\n\n"
        f"{sets_lines}\n\n"
        f"🔥 Всього: {workout.total}\n\n"
        f"⏱️ Відпочинок\n"
        f"{workout.rest}"
    )


def format_rest_day_today() -> str:
    """Відповідь на /today у вихідний день."""
    return "😴 Сьогодні вихідний день.\n\nВідпочиваємо та відновлюємось."


def format_week_message(week: int, total_weeks: int, program_name: str) -> str:
    """
    Повідомлення про поточний тиждень програми для /week.

    Args:
        week:         Поточний тиждень.
        total_weeks:  Загальна кількість тижнів.
        program_name: Назва програми.

    Returns:
        Готовий текст повідомлення.
    """
    return (
        f"📅 Поточний тиждень: {week} з {total_weeks}\n\n"
        f"{SEPARATOR}\n\n"
        f"Програма: {program_name}"
    )


def format_intro_message(participant_names: list[str], ai_enabled: bool) -> str:
    """
    Одноразове вітальне повідомлення при першому запуску бота в групі.

    Args:
        participant_names: Список імен учасників.
        ai_enabled:         Чи увімкнені AI-фічі (є ANTHROPIC_API_KEY).

    Returns:
        Готовий текст повідомлення.
    """
    names = ", ".join(participant_names)
    ai_line = (
        "🤖 Ще розумію живу мову: напишіть /ask <питання> або згадайте мене — відповім.\n\n"
        if ai_enabled
        else ""
    )
    return (
        f"👋 Привіт, {names}!\n\n"
        f"{SEPARATOR}\n\n"
        f"Я бот вашого 15-тижневого челенджу з віджимань. Ось що я вмію:\n\n"
        f"💪 12:00 (Пн–Пт) — надсилаю тренування на день\n"
        f"✅ /done — відмічаєте виконання, миттєво\n"
        f"📊 18:00 (Пн–Пт) — підсумок дня, хто виконав\n"
        f"📈 П'ятниця — підсумок тижня\n\n"
        f"Команди будь-коли:\n"
        f"/today — сьогоднішнє тренування\n"
        f"/status — хто вже виконав сьогодні\n"
        f"/week — який зараз тиждень\n"
        f"/motivation — підбадьорити себе\n"
        f"/help — ця довідка ще раз\n\n"
        f"{ai_line}"
        f"Тиждень підвищується сам щопонеділка. Субота й неділя — вихідні, "
        f"я мовчу про тренування.\n\n"
        f"Погнали 🔥"
    )


def format_help_message(reminder_time_str: str, reminder_timezone: str) -> str:
    """
    Довідкове повідомлення /help.

    Args:
        reminder_time_str: Час нагадування у форматі HH:MM.
        reminder_timezone: Назва timezone.

    Returns:
        Готовий текст повідомлення.
    """
    return (
        f"💪 Pushup Bot — щоденні тренування для команди\n\n"
        f"{SEPARATOR}\n\n"
        f"Команди:\n"
        f"/today — сьогоднішнє тренування\n"
        f"/done — відмітити виконання\n"
        f"/status — хто виконав сьогодні\n"
        f"/week — поточний тиждень програми\n"
        f"/motivation — отримати мотиваційну фразу\n"
        f"/help — ця довідка\n\n"
        f"{SEPARATOR}\n\n"
        f"⏰ Щоденне нагадування: {reminder_time_str} ({reminder_timezone})\n\n"
        f"Програма: 15-тижнева прогресивна програма віджимань.\n"
        f"Виконуй кожен день і пиши /done після тренування."
    )


def format_motivation_message(text: str) -> str:
    """
    Форматує мотиваційну фразу для /motivation.

    Args:
        text: Текст мотиваційної фрази.

    Returns:
        Готовий текст повідомлення.
    """
    return f"💡 {text}"


def format_weekly_summary(
    participants: list[str],
    weekly_counts: dict[str, int],
    week_num: int,
) -> str:
    """
    Підсумок тижня для п'ятничного звіту.

    Args:
        participants:  Список всіх учасників.
        weekly_counts: Dict {participant: кількість виконань за тиждень}.
        week_num:      Номер поточного тижня програми.

    Returns:
        Готовий текст повідомлення.
    """
    lines = []
    for participant in participants:
        count = weekly_counts.get(participant, 0)
        icon = "✅" if count == 5 else ("⚠️" if count >= 3 else "❌")
        lines.append(f"{participant} {icon} {count}/5")

    participants_block = "\n".join(lines)

    total_sessions = sum(weekly_counts.values())
    max_possible = len(participants) * 5

    if total_sessions == max_possible:
        closing = "🏆 Ідеальний тиждень! Вся команда — без пропусків!"
    elif total_sessions >= max_possible * 0.8:
        closing = "💪 Відмінний тиждень! Майже без пропусків."
    elif total_sessions >= max_possible * 0.6:
        closing = "😏 Непоганий тиждень. Але є куди рости."
    else:
        closing = "😬 Тиждень можна було закрити краще. Наступного разу!"

    return (
        f"📈 Підсумок тижня\n\n"
        f"{SEPARATOR}\n\n"
        f"Тиждень {week_num}\n\n"
        f"{participants_block}\n\n"
        f"{SEPARATOR}\n\n"
        f"{closing}"
    )
