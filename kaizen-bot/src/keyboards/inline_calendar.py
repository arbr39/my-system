"""
Клавиатуры для функций Google Calendar.

- Follow-up после событий
- Выбор времени для Quick Action
- Настройки напоминаний
- Управление привычками в календаре
"""

from datetime import datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_followup_keyboard(reminder_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для follow-up после события"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Да, записать",
            callback_data=f"followup_yes:{reminder_id}"
        ),
        InlineKeyboardButton(
            text="❌ Нет",
            callback_data=f"followup_no:{reminder_id}"
        )
    )
    return builder.as_markup()


def get_time_slots_keyboard(item_type: str, item_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура с quick slots для выбора времени.

    Args:
        item_type: "inbox" или "task"
        item_id: ID элемента
    """
    builder = InlineKeyboardBuilder()

    now = datetime.now()
    today = now.date()
    tomorrow = today + timedelta(days=1)

    # Сегодняшние слоты (только будущие)
    today_slots = []
    for hour in [10, 14, 18]:
        slot_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if slot_time > now:
            today_slots.append((hour, f"Сегодня {hour}:00"))

    # Добавляем сегодняшние слоты
    if today_slots:
        row_buttons = []
        for hour, label in today_slots:
            row_buttons.append(InlineKeyboardButton(
                text=label,
                callback_data=f"cal_slot:{item_type}:{item_id}:today:{hour}"
            ))
        builder.row(*row_buttons)

    # Завтрашние слоты
    builder.row(
        InlineKeyboardButton(
            text="Завтра 10:00",
            callback_data=f"cal_slot:{item_type}:{item_id}:tomorrow:10"
        ),
        InlineKeyboardButton(
            text="Завтра 14:00",
            callback_data=f"cal_slot:{item_type}:{item_id}:tomorrow:14"
        )
    )

    # Ввод вручную
    builder.row(InlineKeyboardButton(
        text="⌨️ Другое время",
        callback_data=f"cal_custom:{item_type}:{item_id}"
    ))

    # Отмена
    builder.row(InlineKeyboardButton(
        text="🔙 Отмена",
        callback_data=f"cal_cancel:{item_type}:{item_id}"
    ))

    return builder.as_markup()


def get_reminder_settings_keyboard(
    current_minutes: int = 15,
    reminders_enabled: bool = True
) -> InlineKeyboardMarkup:
    """Клавиатура настроек напоминаний"""
    builder = InlineKeyboardBuilder()

    # Включение/выключение
    toggle_text = "🔔 Напоминания: ВКЛ" if reminders_enabled else "🔕 Напоминания: ВЫКЛ"
    builder.row(InlineKeyboardButton(
        text=toggle_text,
        callback_data="reminder_toggle"
    ))

    # Выбор времени (15/30/60 минут)
    time_buttons = []
    for minutes in [15, 30, 60]:
        is_selected = minutes == current_minutes
        label = f"{'✓ ' if is_selected else ''}{minutes} мин"
        time_buttons.append(InlineKeyboardButton(
            text=label,
            callback_data=f"reminder_time:{minutes}"
        ))
    builder.row(*time_buttons)

    # Назад
    builder.row(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="calendar_menu"
    ))

    return builder.as_markup()


def get_habit_calendar_keyboard(
    exercise_active: bool = False,
    eating_active: bool = False
) -> InlineKeyboardMarkup:
    """Клавиатура настройки привычек в календаре"""
    builder = InlineKeyboardBuilder()

    # Спорт
    exercise_icon = "✅" if exercise_active else "⬜"
    builder.row(InlineKeyboardButton(
        text=f"{exercise_icon} 🏃 Спорт",
        callback_data="habit_toggle:exercise"
    ))

    # Питание
    eating_icon = "✅" if eating_active else "⬜"
    builder.row(InlineKeyboardButton(
        text=f"{eating_icon} 🥗 Питание",
        callback_data="habit_toggle:eating"
    ))

    # Настройка времени (если что-то включено)
    if exercise_active or eating_active:
        builder.row(InlineKeyboardButton(
            text="⏰ Настроить время",
            callback_data="habit_set_time"
        ))

    # Назад
    builder.row(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="calendar_menu"
    ))

    return builder.as_markup()


def get_habit_time_keyboard(habit_type: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора времени для привычки"""
    builder = InlineKeyboardBuilder()

    # Популярные времена для привычек
    times = [
        ("06:00", "🌅 06:00"),
        ("07:00", "🌅 07:00"),
        ("18:00", "🌆 18:00"),
        ("19:00", "🌆 19:00"),
        ("20:00", "🌙 20:00"),
    ]

    # По 2-3 кнопки в ряд
    row = []
    for time_val, label in times:
        row.append(InlineKeyboardButton(
            text=label,
            callback_data=f"habit_time:{habit_type}:{time_val}"
        ))
        if len(row) == 2:
            builder.row(*row)
            row = []
    if row:
        builder.row(*row)

    # Ввод вручную
    builder.row(InlineKeyboardButton(
        text="⌨️ Своё время",
        callback_data=f"habit_custom_time:{habit_type}"
    ))

    # Отмена
    builder.row(InlineKeyboardButton(
        text="🔙 Отмена",
        callback_data="habit_calendar_setup"
    ))

    return builder.as_markup()


def get_morning_sport_time_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора времени спорта в утреннем кайдзене"""
    builder = InlineKeyboardBuilder()

    now = datetime.now()

    # Quick slots — только будущие времена сегодня
    slots = [
        (10, "🌅 10:00"),
        (14, "☀️ 14:00"),
        (18, "🌆 18:00"),
        (20, "🌙 20:00"),
    ]

    row = []
    for hour, label in slots:
        slot_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if slot_time > now:
            row.append(InlineKeyboardButton(
                text=label,
                callback_data=f"morning_sport_time:{hour}:00"
            ))
            if len(row) == 2:
                builder.row(*row)
                row = []

    if row:
        builder.row(*row)

    # Ввод вручную
    builder.row(InlineKeyboardButton(
        text="⌨️ Другое время",
        callback_data="morning_sport_custom"
    ))

    # Отмена (не пойду)
    builder.row(InlineKeyboardButton(
        text="🔙 Не сегодня",
        callback_data="morning_sport_no"
    ))

    return builder.as_markup()
