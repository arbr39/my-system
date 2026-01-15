from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from src.database.crud import get_user_by_telegram_id, get_week_stats
from src.keyboards.inline import get_back_keyboard, get_main_menu

router = Router()


def format_week_report(stats: dict) -> str:
    """Форматирование еженедельного отчёта"""
    report = "📊 *Статистика за неделю*\n\n"

    # Общая информация
    report += f"📅 Дней с записями: {stats['total_entries']}/7\n"
    report += f"🌅 Утренних кайдзенов: {stats['morning_completed']}\n"
    report += f"🌙 Вечерних рефлексий: {stats['evening_completed']}\n\n"

    # Задачи
    if stats['total_tasks'] > 0:
        report += f"✅ *Задачи:* {stats['completed_tasks']}/{stats['total_tasks']} "
        report += f"({stats['completion_rate']:.0f}%)\n\n"

        # Прогресс-бар
        filled = int(stats['completion_rate'] / 10)
        empty = 10 - filled
        report += f"[{'█' * filled}{'░' * empty}]\n\n"

    # Источники энергии
    if stats['energy_plus']:
        report += "⚡ *Что давало энергию:*\n"
        for item in stats['energy_plus'][:3]:
            report += f"  • {item[:50]}{'...' if len(item) > 50 else ''}\n"
        report += "\n"

    # Пожиратели энергии
    if stats['energy_minus']:
        report += "🔋 *Что забирало энергию:*\n"
        for item in stats['energy_minus'][:3]:
            report += f"  • {item[:50]}{'...' if len(item) > 50 else ''}\n"
        report += "\n"

    # Инсайты
    if stats['insights']:
        report += "💡 *Инсайты недели:*\n"
        for item in stats['insights'][:3]:
            report += f"  • {item[:50]}{'...' if len(item) > 50 else ''}\n"

    return report


@router.callback_query(F.data == "stats")
async def show_stats(callback: CallbackQuery):
    """Показать статистику"""
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Сначала запусти /start")
        return

    stats = get_week_stats(user.id)

    if stats['total_entries'] == 0:
        await callback.message.edit_text(
            "📊 *Статистика*\n\n"
            "Пока нет данных. Заполни хотя бы один утренний кайдзен!",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
    else:
        report = format_week_report(stats)
        await callback.message.edit_text(
            report,
            parse_mode="Markdown",
            reply_markup=get_back_keyboard()
        )

    await callback.answer()


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Команда /stats"""
    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Сначала запусти /start")
        return

    stats = get_week_stats(user.id)

    if stats['total_entries'] == 0:
        await message.answer(
            "📊 *Статистика*\n\nПока нет данных.",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
    else:
        report = format_week_report(stats)
        await message.answer(report, parse_mode="Markdown", reply_markup=get_back_keyboard())
