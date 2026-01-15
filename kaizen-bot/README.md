# My System

Персональный Telegram-бот для контроля и улучшения жизни.

Это моя личная система, которая помогает каждый день становиться лучше через структурированные ритуалы и отслеживание прогресса.

## Что умеет

- **Утренний ритуал** — планирование дня, постановка задач и намерений
- **Вечерняя рефлексия** — анализ дня, отметка выполненных задач, благодарности
- **Цели** — долгосрочные цели с отслеживанием прогресса
- **Аналитика** — статистика и еженедельные отчёты
- **Напоминания** — автоматические пуши утром и вечером

## Tech Stack

- **Python 3.11+** с aiogram 3.x
- **SQLAlchemy 2.0** + SQLite (aiosqlite)
- **APScheduler** для напоминаний
- **Docker** для деплоя

## Быстрый старт

### 1. Клонирование и настройка

```bash
git clone https://github.com/arbr39/kaizen-bot.git
cd kaizen-bot
cp .env.example .env
```

### 2. Настройка переменных окружения

Отредактируйте `.env`:

```
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_USER_ID=your_telegram_user_id
MORNING_HOUR=7
EVENING_HOUR=22
TIMEZONE=Europe/Moscow
```

### 3. Запуск

**Docker (рекомендуется):**

```bash
docker-compose up -d --build
```

**Локально:**

```bash
pip install -r requirements.txt
python -m src.bot
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Начало работы, главное меню |
| `/today` | Статус текущего дня |
| `/stats` | Статистика и прогресс |
| `/goals` | Управление целями |
| `/help` | Справка |

## Структура проекта

```
src/
├── bot.py              # Точка входа
├── config.py           # Конфигурация
├── handlers/           # Обработчики команд
│   ├── start.py        # /start, /help, /today
│   ├── morning.py      # Утренний кайдзен
│   ├── evening.py      # Вечерняя рефлексия
│   ├── stats.py        # Статистика
│   └── goals.py        # Цели
├── database/
│   ├── models.py       # SQLAlchemy модели
│   └── crud.py         # CRUD операции
├── scheduler/
│   └── jobs.py         # Scheduled jobs
└── keyboards/
    └── inline.py       # Inline клавиатуры
```

## Лицензия

MIT
