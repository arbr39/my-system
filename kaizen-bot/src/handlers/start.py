from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from src.database.crud import get_or_create_user
from src.keyboards.inline import get_main_menu

router = Router()


WELCOME_MESSAGE = """
🌟 *Добро пожаловать в Kaizen Bot!*

Я помогу тебе внедрить систему ежедневного улучшения жизни:

🌅 *Утренний кайдзен* — анализ вчерашнего дня и планирование
🌙 *Вечерняя рефлексия* — подведение итогов и инсайты
📊 *Еженедельный отчёт* — статистика и прогресс

Я буду напоминать тебе каждое утро и вечер.
Начнём?
"""


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start"""
    user = get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )

    await message.answer(
        WELCOME_MESSAGE,
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )


COMMANDS_TEXT = """
📖 *Все команды бота:*

*Основные:*
/start — Главное меню
/help — Краткая справка
/commands — Этот список команд

*Ежедневные:*
/today — Задачи на сегодня
/stats — Статистика за неделю
/habits — Статистика привычек (спорт, питание, сон)

*GTD (Getting Things Done):*
/inbox — Быстрый сбор задач (или отправь любой текст)
/someday — Список "когда-нибудь/может быть"
/review — Еженедельный обзор (GTD Weekly Review)

*Управление:*
/goals — Мои цели
/settings — Настройки напоминаний (время утра/вечера)
/calendar — Google Calendar интеграция

*Система наград (@whysasha):*
/rewards — Фонд наград, история, трата баллов

*Принципы и даты:*
/principles — Ежемесячная оценка 25 принципов жизни
/dates — Важные даты (дни рождения, напоминания)

*Обратная связь:*
/report — Сообщить о баге, идее или предложить улучшение
/reports — Список всех репортов (только админ)

*Автоматические напоминания:*
🌅 Утро (по умолчанию 7:00) — заполни кайдзен
🌙 Вечер (по умолчанию 22:00) — подведи итоги + планирование
📋 Воскресенье 18:00 — Weekly Review
📊 Воскресенье 20:00 — еженедельный отчёт
🎂 Ежедневно 9:00 — напоминания о днях рождения
📊 1-е число месяца — оценка принципов
"""


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help — краткая справка"""
    help_text = """
📖 *Быстрая справка:*

1. Утром заполни кайдзен (3 задачи + рефлексия)
2. Вечером отметь выполненное + инсайт
3. В воскресенье получи отчёт за неделю

Полный список команд: /commands
"""
    await message.answer(help_text, parse_mode="Markdown", reply_markup=get_main_menu())


@router.message(Command("commands"))
async def cmd_commands(message: Message):
    """Команда /commands — полный список команд"""
    await message.answer(COMMANDS_TEXT, parse_mode="Markdown", reply_markup=get_main_menu())


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery):
    """Показать главное меню"""
    await callback.message.edit_text(
        "🏠 *Главное меню*\n\nВыбери действие:",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )
    await callback.answer()


@router.message(Command("today"))
async def cmd_today(message: Message):
    """Показать задачи на сегодня"""
    from src.database.crud import get_today_entry, get_user_by_telegram_id

    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Сначала запусти бота командой /start")
        return

    entry = get_today_entry(user.id)

    if not entry or not entry.morning_completed:
        await message.answer(
            "📝 Утренний кайдзен ещё не заполнен.\n\nНажми кнопку ниже, чтобы начать.",
            reply_markup=get_main_menu()
        )
        return

    tasks_text = ""
    if entry.task_1:
        status = "✅" if entry.task_1_done else "⬜"
        tasks_text += f"{status} {entry.task_1}\n"
    if entry.task_2:
        status = "✅" if entry.task_2_done else "⬜"
        tasks_text += f"{status} {entry.task_2}\n"
    if entry.task_3:
        status = "✅" if entry.task_3_done else "⬜"
        tasks_text += f"{status} {entry.task_3}\n"

    await message.answer(
        f"📋 *Задачи на сегодня:*\n\n{tasks_text}",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )
