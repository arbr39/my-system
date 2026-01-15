from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from src.database.crud import get_user_by_telegram_id, get_habits_stats
from src.keyboards.inline import get_main_menu

router = Router()


@router.message(Command("habits"))
async def cmd_habits(message: Message):
    """Команда /habits — статистика привычек"""
    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Сначала запусти /start")
        return

    stats = get_habits_stats(user.id)

    text = "📊 *Статистика привычек*\n\n"

    # Спорт
    text += "🏃 *Спорт:*\n"
    if stats["exercise_streak"] > 0:
        text += f"• Текущий streak: {stats['exercise_streak']} дней подряд\n"
    else:
        text += "• Текущий streak: 0 дней\n"
    text += f"• За неделю: {stats['week_exercise']}/7\n\n"

    # Питание
    text += "🥗 *Питание:*\n"
    if stats["eating_streak"] > 0:
        text += f"• Текущий streak: {stats['eating_streak']} дней подряд\n"
    else:
        text += "• Текущий streak: 0 дней\n"
    text += f"• За неделю: {stats['week_eating']}/7\n\n"

    # Сон
    text += "😴 *Сон:*\n"
    text += f"• Среднее время подъёма: {stats['avg_wake']}\n"
    text += f"• Среднее время отбоя: {stats['avg_sleep']}\n"

    if stats["total_entries"] == 0:
        text = "📊 *Статистика привычек*\n\n"
        text += "Пока нет данных. Заполни вечернюю рефлексию, чтобы начать отслеживать привычки!"

    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu())
