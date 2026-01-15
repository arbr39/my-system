"""
Клавиатуры для важных дат
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_dates_main_menu() -> InlineKeyboardMarkup:
    """Главное меню дат"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="📋 Все даты",
        callback_data="dates_list"
    ))

    builder.row(InlineKeyboardButton(
        text="➕ Добавить дату",
        callback_data="date_add"
    ))

    builder.row(InlineKeyboardButton(
        text="🔙 Главное меню",
        callback_data="main_menu"
    ))

    return builder.as_markup()


def get_dates_list_keyboard(dates: list) -> InlineKeyboardMarkup:
    """Список дат для выбора"""
    builder = InlineKeyboardBuilder()

    month_names = ["", "янв", "фев", "мар", "апр", "мая",
                   "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]

    for d in dates[:15]:  # Лимит 15 дат
        emoji = "🎂" if d.date_type == "birthday" else "📌"
        text = f"{emoji} {d.name} — {d.day} {month_names[d.month]}"
        builder.row(InlineKeyboardButton(
            text=text,
            callback_data=f"date_view:{d.id}"
        ))

    builder.row(InlineKeyboardButton(
        text="➕ Добавить",
        callback_data="date_add"
    ))

    builder.row(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="dates_show"
    ))

    return builder.as_markup()


def get_date_view_keyboard(date_id: int) -> InlineKeyboardMarkup:
    """Просмотр даты"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✏️ Изменить", callback_data=f"date_edit:{date_id}"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"date_delete:{date_id}")
    )

    builder.row(InlineKeyboardButton(
        text="🔙 К списку",
        callback_data="dates_list"
    ))

    return builder.as_markup()


def get_date_type_keyboard() -> InlineKeyboardMarkup:
    """Выбор типа даты"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="🎂 День рождения",
        callback_data="date_type:birthday"
    ))
    builder.row(InlineKeyboardButton(
        text="💍 Годовщина",
        callback_data="date_type:anniversary"
    ))
    builder.row(InlineKeyboardButton(
        text="📌 Другое",
        callback_data="date_type:custom"
    ))

    builder.row(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="date_cancel"
    ))

    return builder.as_markup()


def get_month_keyboard() -> InlineKeyboardMarkup:
    """Выбор месяца"""
    builder = InlineKeyboardBuilder()

    months = [
        ("Янв", 1), ("Фев", 2), ("Мар", 3), ("Апр", 4),
        ("Май", 5), ("Июн", 6), ("Июл", 7), ("Авг", 8),
        ("Сен", 9), ("Окт", 10), ("Ноя", 11), ("Дек", 12)
    ]

    # По 4 в ряд
    for i in range(0, 12, 4):
        row = []
        for name, num in months[i:i+4]:
            row.append(InlineKeyboardButton(
                text=name,
                callback_data=f"date_month:{num}"
            ))
        builder.row(*row)

    builder.row(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="date_cancel"
    ))

    return builder.as_markup()


def get_day_keyboard(month: int) -> InlineKeyboardMarkup:
    """Выбор дня в зависимости от месяца"""
    builder = InlineKeyboardBuilder()

    # Количество дней в месяце
    days_in_month = {
        1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
        7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
    }
    max_day = days_in_month.get(month, 31)

    # По 7 в ряд
    for start in range(1, max_day + 1, 7):
        row = []
        for day in range(start, min(start + 7, max_day + 1)):
            row.append(InlineKeyboardButton(
                text=str(day),
                callback_data=f"date_day:{day}"
            ))
        builder.row(*row)

    builder.row(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="date_cancel"
    ))

    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Кнопка отмены"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="date_cancel"
    ))
    return builder.as_markup()


def get_confirm_delete_keyboard(date_id: int) -> InlineKeyboardMarkup:
    """Подтверждение удаления"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="🗑 Да, удалить",
        callback_data=f"date_delete_confirm:{date_id}"
    ))

    builder.row(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data=f"date_view:{date_id}"
    ))

    return builder.as_markup()
