"""
Клавиатуры для напоминаний о задачах дня
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_daily_task_reminder_keyboard(
    entry_id: int,
    tasks: list  # [(num, text, done), ...]
) -> InlineKeyboardMarkup:
    """
    Клавиатура для напоминания о задачах.
    Показывает только незавершённые задачи с кнопками быстрого выполнения.
    """
    builder = InlineKeyboardBuilder()

    # Кнопки для незавершённых задач
    for num, text, done in tasks:
        if not text or done:
            continue

        # Обрезать длинный текст
        display_text = text[:30] + "..." if len(text) > 30 else text

        builder.row(InlineKeyboardButton(
            text=f"⬜ {display_text} (20₽)",
            callback_data=f"daily_task_done:{entry_id}:{num}"
        ))

    # Кнопка статистики
    builder.row(InlineKeyboardButton(
        text="📊 Статистика",
        callback_data="stats"
    ))

    return builder.as_markup()
