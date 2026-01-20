# My System

Персональный Telegram-бот для контроля и улучшения жизни. Утренние ритуалы, вечерняя рефлексия, цели, аналитика.

## Tech Stack

- **Python 3.11+** с aiogram 3.x
- **SQLAlchemy 2.0** + SQLite (aiosqlite)
- **APScheduler** для напоминаний
- **Docker + docker-compose** для деплоя

## Project Structure

```
src/
├── bot.py           # Точка входа
├── config.py        # Конфигурация из .env
├── handlers/        # Обработчики команд и callback'ов
│   ├── start.py     # /start, /help, /commands, /today, main menu
│   ├── morning.py   # Утренний кайдзен flow (FSM) + выбор приоритетной задачи + награды
│   ├── evening.py   # Вечерняя рефлексия flow (FSM) + статус главной задачи + награды
│   ├── stats.py     # /stats, еженедельный отчёт
│   ├── goals.py     # /goals, управление целями
│   ├── settings.py  # /settings, настройки напоминаний
│   ├── report.py    # /report, /reports, обратная связь
│   ├── habits.py    # /habits, статистика привычек
│   ├── inbox.py     # /inbox, GTD inbox, перехват текста (FSM)
│   ├── someday.py   # /someday, список "когда-нибудь/может быть"
│   ├── review.py    # /review, GTD Weekly Review (FSM 6 состояний) + награды
│   ├── calendar.py  # /calendar, Google Calendar OAuth + sync
│   ├── rewards.py   # /rewards, фонд наград (@whysasha), управление наградами (FSM)
│   └── user_tasks.py # /tasks, пользовательские задачи с наградами (FSM)
├── database/
│   ├── models.py    # SQLAlchemy модели (User, DailyEntry, Goal, Report, InboxItem,
│   │                # SomedayMaybe, WeeklyReview, RewardFund, RewardTransaction, RewardItem,
│   │                # UserTask, UserTaskCompletion)
│   ├── crud.py      # CRUD операции для основных моделей
│   ├── crud_rewards.py  # CRUD для системы наград
│   └── crud_user_tasks.py  # CRUD для пользовательских задач
├── integrations/
│   └── google_calendar.py  # Google Calendar API wrapper, OAuth
├── scheduler/
│   ├── jobs.py           # APScheduler jobs (morning, evening, weekly_review, weekly_report, calendar_sync)
│   └── calendar_sync.py  # Логика синхронизации с Google Calendar
└── keyboards/
    ├── inline.py         # InlineKeyboardMarkup builders (основные)
    ├── inline_rewards.py # Клавиатуры для системы наград
    └── inline_user_tasks.py # Клавиатуры для пользовательских задач
```

## Commands

```bash
# Локальный запуск
python -m src.bot

# Docker
docker-compose up -d --build
docker logs -f kaizen-bot
docker-compose restart
docker-compose down

# Деплой автоматический через GitHub Actions (push в master)
```

## Server Database Access

### Database Location

```bash
# Production database path
/root/my-system/kaizen-bot/data/kaizen.db
```

### Quick Queries (sqlite3 CLI)

```bash
# Connect to database
ssh root@64.137.9.146 "sqlite3 /root/my-system/kaizen-bot/data/kaizen.db"

# Basic stats
ssh root@64.137.9.146 "sqlite3 /root/my-system/kaizen-bot/data/kaizen.db 'SELECT COUNT(*) FROM users'"

# Reward fund balance
ssh root@64.137.9.146 "sqlite3 /root/my-system/kaizen-bot/data/kaizen.db 'SELECT balance, total_earned, total_spent FROM reward_funds'"

# Daily entries stats
ssh root@64.137.9.146 "sqlite3 /root/my-system/kaizen-bot/data/kaizen.db '
SELECT
  COUNT(*) as total,
  SUM(CASE WHEN morning_completed = 1 THEN 1 ELSE 0 END) as morning,
  SUM(CASE WHEN evening_completed = 1 THEN 1 ELSE 0 END) as evening
FROM daily_entries'"

# Recent entries (last 7 days)
ssh root@64.137.9.146 "sqlite3 /root/my-system/kaizen-bot/data/kaizen.db '
SELECT entry_date, morning_completed, evening_completed, task_1, task_1_done
FROM daily_entries
ORDER BY entry_date DESC
LIMIT 7'"

# Recent reward transactions
ssh root@64.137.9.146 "sqlite3 /root/my-system/kaizen-bot/data/kaizen.db '
SELECT transaction_type, amount, description, datetime(created_at)
FROM reward_transactions
ORDER BY created_at DESC
LIMIT 10'"

# User tasks with completions
ssh root@64.137.9.146 "sqlite3 /root/my-system/kaizen-bot/data/kaizen.db '
SELECT
  ut.name,
  ut.reward_amount,
  ut.is_active,
  COUNT(utc.id) as completions
FROM user_tasks ut
LEFT JOIN user_task_completions utc ON ut.id = utc.task_id
GROUP BY ut.id'"

# Inbox status breakdown
ssh root@64.137.9.146 "sqlite3 /root/my-system/kaizen-bot/data/kaizen.db '
SELECT status, COUNT(*)
FROM inbox_items
GROUP BY status'"
```

### Advanced: Formatted Output (Python for complex formatting)

```bash
# Comprehensive stats with JSON output
ssh root@64.137.9.146 "cd /root/my-system/kaizen-bot && python3 -c \"
import sqlite3
import json

conn = sqlite3.connect('data/kaizen.db')
cursor = conn.cursor()

stats = {}

# Users
cursor.execute('SELECT COUNT(*) FROM users')
stats['users'] = cursor.fetchone()[0]

# Daily entries
cursor.execute('''
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN morning_completed = 1 THEN 1 ELSE 0 END) as morning,
        SUM(CASE WHEN evening_completed = 1 THEN 1 ELSE 0 END) as evening
    FROM daily_entries
''')
row = cursor.fetchone()
stats['daily_entries'] = {'total': row[0], 'morning': row[1], 'evening': row[2]}

# Reward fund
cursor.execute('SELECT balance, total_earned, total_spent FROM reward_funds')
row = cursor.fetchone()
if row:
    stats['reward_fund'] = {'balance': row[0], 'earned': row[1], 'spent': row[2]}

print(json.dumps(stats, indent=2))
conn.close()
\""

# Daily entries with formatted tasks display
ssh root@64.137.9.146 "cd /root/my-system/kaizen-bot && python3 -c \"
import sqlite3
conn = sqlite3.connect('data/kaizen.db')
cursor = conn.cursor()

cursor.execute('''
    SELECT
        entry_date,
        morning_completed,
        evening_completed,
        task_1, task_1_done,
        task_2, task_2_done,
        task_3, task_3_done,
        priority_task
    FROM daily_entries
    ORDER BY entry_date DESC
    LIMIT 7
''')

for row in cursor.fetchall():
    date, m, e, t1, t1d, t2, t2d, t3, t3d, priority = row
    morning = '✅' if m else '❌'
    evening = '✅' if e else '❌'
    print(f'{date}: M{morning} E{evening}')
    if t1: print(f'  1. {t1} {'✅' if t1d else '❌'} {'★' if priority == 1 else ''}')
    if t2: print(f'  2. {t2} {'✅' if t2d else '❌'} {'★' if priority == 2 else ''}')
    if t3: print(f'  3. {t3} {'✅' if t3d else '❌'} {'★' if priority == 3 else ''}')

conn.close()
\""
```

## Development Patterns

### Handlers

- Каждый handler в отдельном файле с собственным `Router()`
- FSM (Finite State Machine) для многошаговых диалогов
- Callback data формат: `action:param` (например `toggle_task:1`)

### Database

- Все CRUD операции в `database/crud.py`
- Сессии создаются и закрываются внутри каждой функции
- `get_or_create_*` паттерн для идемпотентности

### Keyboards

- Все клавиатуры строятся через `InlineKeyboardBuilder`
- Функции возвращают `InlineKeyboardMarkup`

## Code Style

- Type hints для параметров функций
- Docstrings только для неочевидных функций
- Async/await везде (aiogram 3.x)
- f-strings для форматирования
- Markdown в сообщениях бота (`parse_mode="Markdown"`)

## Environment Variables

```
BOT_TOKEN=           # От @BotFather
ADMIN_USER_ID=       # Telegram user ID владельца
MORNING_HOUR=7       # Час утреннего напоминания
EVENING_HOUR=22      # Час вечернего напоминания
TIMEZONE=Europe/Moscow

# Google Calendar (опционально)
GOOGLE_CLIENT_ID=    # OAuth 2.0 Client ID
GOOGLE_CLIENT_SECRET=# OAuth 2.0 Client Secret
ENCRYPTION_KEY=      # Fernet key для шифрования токенов
```

---

## Bot Commands Reference

> **ВАЖНО:** При добавлении новых команд ОБЯЗАТЕЛЬНО обновляй этот раздел и `COMMANDS_TEXT` в `start.py`!

### Основные команды
| Команда | Описание | Handler |
|---------|----------|---------|
| `/start` | Главное меню, регистрация пользователя | `start.py` |
| `/help` | Краткая справка | `start.py` |
| `/commands` | Полный список всех команд | `start.py` |

### Ежедневные команды
| Команда | Описание | Handler |
|---------|----------|---------|
| `/today` | Показать задачи на сегодня | `start.py` |
| `/stats` | Статистика за неделю | `stats.py` |
| `/habits` | Статистика привычек (спорт, питание, сон) | `habits.py` |

### GTD (Getting Things Done)
| Команда | Описание | Handler |
|---------|----------|---------|
| `/inbox` | Быстрый сбор задач (или отправь любой текст) | `inbox.py` |
| `/someday` | Список "когда-нибудь/может быть" | `someday.py` |
| `/review` | Еженедельный обзор (GTD Weekly Review) | `review.py` |

### Мотивация (@whysasha методика)
| Команда | Описание | Handler |
|---------|----------|---------|
| `/rewards` | Фонд наград — баланс, награды, история | `rewards.py` |
| `/tasks` | Пользовательские задачи с наградами | `user_tasks.py` |

### Интеграции
| Команда | Описание | Handler |
|---------|----------|---------|
| `/calendar` | Google Calendar подключение и синхронизация | `calendar.py` |

### Управление
| Команда | Описание | Handler |
|---------|----------|---------|
| `/goals` | Мои цели | `goals.py` |
| `/settings` | Настройки времени напоминаний | `settings.py` |

### Обратная связь
| Команда | Описание | Handler | Доступ |
|---------|----------|---------|--------|
| `/report` | Сообщить баг/идею/улучшение | `report.py` | Все |
| `/reports` | Список всех репортов | `report.py` | Только админ |

### Автоматические напоминания
| Событие | Время по умолчанию | Job |
|---------|-------------------|-----|
| Утренний кайдзен | 07:00 | `send_morning_reminder` |
| Вечерняя рефлексия | 22:00 | `send_evening_reminder` |
| Weekly Review напоминание | Вс 18:00 | `send_weekly_review_reminder` |
| Еженедельный отчёт | Вс 20:00 | `send_weekly_report` |
| Google Calendar sync | Каждые 30 мин | `sync_calendars` |

---

## Reward System Philosophy

**Система построена на методике @whysasha — превратить мозг в помощника, а не врага.**

### Принципы:
1. **Награда ТОЛЬКО за результат** — никакого "халявного" дофамина
2. **Больше результат = больше награда** — соразмерность
3. **Награда сразу** — немедленно после достижения
4. **Личный список наград** — пользователь определяет, что доставляет удовольствие именно ему
5. **Анти-кортизол** — празднуем победы, никогда не стыдим за пропуски

### Как работает:
- Каждое действие (утро, вечер, задача, спорт...) → начисление рублей
- Пользователь создаёт список наград: "Кофе = 150₽", "Ресторан = 800₽"
- Накопил → тратит на награду из своего списка
- Мозг формирует дофаминовую привязку: "работа → награда → удовольствие"

### Anti-patterns (чего НЕ делаем):
- ❌ Не стыдим: "Пропустил спорт" → вместо этого: просто не начислили 30₽
- ❌ Не сравниваем: "Мог бы больше заработать"
- ❌ Не наказываем штрафами автоматически (штрафы опциональны, выключены)

### Messaging Guidelines:
- **DO:** "Отлично! +50₽ за утренний кайдзен!"
- **DON'T:** "Ты пропустил утро, потерял 50₽"

### Inbox Task Rewards

Награды за выполнение inbox задач интегрированы в систему мотивации:

**Базовые ставки по времени:**
- 5min → 10₽
- 15min → 15₽
- 30min → 25₽
- 1hour → 40₽
- Без контекста → 15₽

**Множитель по энергии:**
- low (🔋) → ×1.0
- medium (🔋🔋) → ×1.5
- high (🔋🔋🔋) → ×2.0

**Примеры итоговых сумм:**
- 5min + low = 10₽
- 30min + medium = 25₽ × 1.5 = 38₽ (округление вверх)
- 1hour + high = 40₽ × 2.0 = 80₽

**UI Flow:**
1. Просмотр inbox задачи
2. Кнопка "✅ Выполнено"
3. Немедленная награда + обновление баланса
4. Messaging: "30min (25₽) × энергия 🔋🔋 (×1.5) → 38₽"

### User Tasks Rewards

Пользовательские задачи с наградами — гибкая система для регулярных привычек:

**Два типа задач:**
- **Повторяющиеся** — можно отмечать каждый день (например, "Тренировка в зале")
- **Одноразовые** — выполняется один раз, затем архивируется

**Категории:**
- Спорт и здоровье
- Обучение
- Личное развитие
- Работа над проектами

**Награды:**
- Пользователь сам определяет сумму награды за задачу
- Награда начисляется немедленно после выполнения
- Защита от повторного выполнения за день (для повторяющихся)

**UI Flow:**
1. Создать задачу: название → награда → тип → категория
2. Отметить выполнение: нажать кнопку "⭕ [Название] — [Награда]₽"
3. Немедленная награда + обновление баланса
4. Messaging: "🎉 Отлично! +50₽ за Тренировка в зале"

**Разделение сущностей:**
- **Inbox** = быстрый сбор одноразовых дел с контекстами (энергия, время)
- **User tasks** = регулярные привычки и задачи с постоянными наградами

---

## Documentation Rules

**ВАЖНО:** После каждого коммита обязательно обновлять документацию!

### При добавлении новых функций:
1. Добавь команду в таблицу Bot Commands Reference
2. Обнови `COMMANDS_TEXT` в `start.py`
3. Добавь docstring к handler функции
4. Если это FSM flow — опиши состояния
5. Обнови Project Structure если добавлены файлы

### CHANGELOG.md
- Формат: `## [YYYY-MM-DD] Краткое описание`
- Секции: Added, Changed, Fixed, Removed
- Писать ЧТО изменилось и ЗАЧЕМ

### Код
- Комментарии для неочевидной логики
- Docstrings для публичных функций с нетривиальной сигнатурой
- TODO комментарии для известных ограничений

## Hooks

Проект использует Claude Code hooks (`.claude/settings.json`):

- **PostToolUse (Bash)** — после git commit напоминает обновить документацию
- **PreToolUse (Edit|Write)** — блокирует редактирование `.env` файлов
