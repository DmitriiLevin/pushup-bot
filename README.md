# Pushup Bot

Telegram-бот для командного 15-тижневого челенджу з віджимань.

Працює повністю безкоштовно через **GitHub Actions** — без VPS, без Render, без постійно запущеного процесу.

---

## Як це працює

| Час (Europe/Warsaw) | Дія |
|---------------------|-----|
| 12:00 Пн–Пт | GitHub Actions надсилає тренування у групу |
| 18:00 Пн–Пт | GitHub Actions читає `/done` повідомлення, надсилає статус дня |
| 18:00 П'ятниця | Додатково надсилає підсумок тижня |

**Важливо:** `/done` більше не обробляється миттєво. Бот фіксує відмітки один раз о 18:00, обробляючи всі `/done` за день.

Стан (`data/state.json`) зберігається прямо у репозиторії і оновлюється кожного разу після запуску.

---

## Можливості

- 15-тижнева прогресивна програма віджимань (5 підходів, кількість зростає щотижня)
- Щоденні нагадування з тренуванням о 12:00
- Відмітка виконання через `/done` (фіксується о 18:00)
- Вечірній статус: хто виконав, хто ні
- Щоп'ятничний підсумок тижня з результатами кожного
- Більше 490 унікальних фраз з антиповтором
- Різні повідомлення залежно від дня тижня (понеділок, п'ятниця, вихідні)
- Атомарний запис стану (state.json ніколи не пошкоджується)

---

## Встановлення

### 1. Підготовка

1. Зроби fork або клонуй цей репозиторій на свій GitHub акаунт.
2. Переконайся, що репозиторій **публічний** або у тебе є GitHub Actions для приватних репо.

### 2. Створи Telegram бота

1. Відкрий [@BotFather](https://t.me/BotFather) у Telegram.
2. Надішли `/newbot`, дотримуйся інструкцій.
3. Скопіюй **Bot Token**.

### 3. Отримай CHAT_ID групи

1. Додай бота до своєї групи.
2. Відправ будь-яке повідомлення у групу.
3. Відкрий у браузері: `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Знайди `chat.id` — для груп це від'ємне число (наприклад `-1001234567890`).

### 4. Додай GitHub Secrets

Перейди у свій репозиторій на GitHub:

**Settings → Secrets and variables → Actions → New repository secret**

Додай три секрети:

| Secret | Значення | Приклад |
|--------|----------|---------|
| `BOT_TOKEN` | Токен від @BotFather | `1234567890:ABC...` |
| `CHAT_ID` | ID групи | `-1001234567890` |
| `PARTICIPANTS` | Учасники у форматі `Ім'я=@username` через кому | `Діма=@dlevinn,Толя=@anatoliireva` |

### 5. Увімкни GitHub Actions

1. Перейди у репозиторій → вкладка **Actions**.
2. Якщо Actions вимкнені — натисни **"I understand my workflows, go ahead and enable them"**.
3. Переконайся, що обидва workflows відображаються:
   - `Daily Workout Reminder`
   - `Evening Status`

### 6. Перевір вручну

Щоб запустити workflow одразу без очікування:
1. Перейди **Actions → Daily Workout Reminder**.
2. Натисни **Run workflow → Run workflow**.
3. Перевір, що повідомлення з'явилось у Telegram групі.

---

## Налаштування розкладу (часовий пояс)

Cron у GitHub Actions завжди в UTC. Поточні налаштування:

| Workflow | Cron (UTC) | Europe/Warsaw CEST (літо) | Europe/Warsaw CET (зима) |
|----------|------------|---------------------------|--------------------------|
| `daily-reminder` | `0 10 * * 1-5` | 12:00 | 11:00 |
| `evening-status` | `0 16 * * 1-5` | 18:00 | 17:00 |

Якщо хочеш змінити час — відредагуй `cron:` у файлах `.github/workflows/*.yml`.

---

## Конфігурація (необов'язково, для локальної розробки)

Для тестування локально створи `.env` файл на основі `.env.example`:

```env
BOT_TOKEN=your_bot_token_here
CHAT_ID=-1001234567890
PARTICIPANTS=Діма=@dlevinn,Толя=@anatoliireva,Юра=@lurook
PHRASE_HISTORY_SIZE=10
```

Запуск скриптів локально:

```bash
pip install -r requirements.txt
python scripts/send_daily_reminder.py
python scripts/process_done_and_status.py
```

---

## Як оновити розклад тренувань

Розклад знаходиться у `programs/pushups/schedule.json`:

```json
{
  "display_name": "Прогресивні Віджимання",
  "total_weeks": 15,
  "rest": "60 секунд",
  "weeks": [
    { "week": 1, "sets": [10, 10, 8, 8, 10] },
    { "week": 2, "sets": [12, 12, 10, 10, 12] }
  ]
}
```

`sets` — кількість повторень у кожному підході. Можна додавати/прибирати підходи.

Щоб перейти на наступний тиждень вручну — відредагуй `current_week` у `data/state.json` і закомітуй.

---

## Як додати учасника

У GitHub Secret `PARTICIPANTS` додай нового учасника:

```
Діма=@dlevinn,Толя=@anatoliireva,Юра=@lurook,Сашко=@sashahandle
```

- **Ім'я** — відображуване ім'я у повідомленнях (Діма, Толя, Юра)
- **@username** — точний Telegram username (без урахування регістру)

Бот ідентифікує `/done` виключно за Telegram username.

---

## Структура проєкту

```
pushup-bot/
├── .github/
│   └── workflows/
│       ├── daily-reminder.yml   # 12:00 Пн–Пт: надсилає тренування
│       └── evening-status.yml   # 18:00 Пн–Пт: читає /done, надсилає статус
│
├── scripts/
│   ├── send_daily_reminder.py   # Логіка ранкового нагадування
│   └── process_done_and_status.py  # Читає getUpdates, надсилає статус/підсумок
│
├── core/                        # Бізнес-логіка (без залежностей від Telegram SDK)
│   ├── config.py                # Завантаження змінних оточення
│   ├── models.py                # Dataclasses: AppState, DayRecord, Participant...
│   └── state.py                 # Атомарний read/write state.json
│
├── programs/                    # Плагін-система тренувальних програм
│   ├── base.py
│   ├── registry.py
│   └── pushups/
│       ├── program.py
│       └── schedule.json        # 15-тижневий план
│
├── messages/                    # Фрази та форматування
│   ├── phrases.py               # 490+ фраз по 6 категоріях
│   ├── selector.py              # Вибір без повторів (anti-repeat)
│   └── formatter.py             # Збірка тексту повідомлень
│
├── data/
│   └── state.json               # Стан (current_week, /done записи, offset)
│
├── requirements.txt             # requests, python-dotenv
└── .env.example
```

---

## Вирішення проблем

**Workflow не запускається**
- Перевір вкладку **Actions** → чи увімкнені workflows.
- Переконайся, що секрети `BOT_TOKEN`, `CHAT_ID`, `PARTICIPANTS` додані правильно.

**Бот надсилає повідомлення, але `/done` не фіксується**
- `/done` фіксується тільки о 18:00. Надішли `/done` до 18:00 — воно буде враховане.
- Перевір, що Telegram username у `PARTICIPANTS` точно збігається (без урахування регістру).

**Повідомлення надсилаються двічі**
- Перевір вкладку Actions — чи немає duplicate workflow runs.
- Переконайся, що в `data/state.json` є коректний `update_offset`.

**state.json конфліктує при push**
- Якщо два workflows запустились одночасно, може виникнути git конфлікт.
- Workflows налаштовані на різний час (12:00 і 18:00), тому це малоймовірно.
- За потреби відредагуй `data/state.json` вручну і закомітуй.

**"CHAT_ID не встановлено" або схожа помилка**
- Перевір GitHub Secrets — назви мають бути точно `BOT_TOKEN`, `CHAT_ID`, `PARTICIPANTS`.
