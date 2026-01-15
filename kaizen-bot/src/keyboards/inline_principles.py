"""
Клавиатуры для системы оценки принципов жизни
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_principles_main_menu(has_active: bool = False) -> InlineKeyboardMarkup:
    """Главное меню принципов"""
    builder = InlineKeyboardBuilder()

    if has_active:
        builder.row(InlineKeyboardButton(
            text="▶️ Продолжить оценку",
            callback_data="principles_continue"
        ))
    else:
        builder.row(InlineKeyboardButton(
            text="📝 Начать оценку",
            callback_data="principles_start"
        ))

    builder.row(InlineKeyboardButton(
        text="📜 История оценок",
        callback_data="principles_history"
    ))

    builder.row(InlineKeyboardButton(
        text="🔙 Главное меню",
        callback_data="main_menu"
    ))

    return builder.as_markup()


def get_rating_keyboard(
    principle_id: int,
    current_index: int,
    total: int,
    current_rating: int = None
) -> InlineKeyboardMarkup:
    """Клавиатура для оценки принципа 1-10"""
    builder = InlineKeyboardBuilder()

    # Оценки 1-5
    row1 = []
    for score in range(1, 6):
        mark = "✓" if current_rating == score else ""
        row1.append(InlineKeyboardButton(
            text=f"{score}{mark}",
            callback_data=f"principle_rate:{principle_id}:{score}"
        ))
    builder.row(*row1)

    # Оценки 6-10
    row2 = []
    for score in range(6, 11):
        mark = "✓" if current_rating == score else ""
        row2.append(InlineKeyboardButton(
            text=f"{score}{mark}",
            callback_data=f"principle_rate:{principle_id}:{score}"
        ))
    builder.row(*row2)

    # Навигация
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="principle_prev"
        ))
    nav_buttons.append(InlineKeyboardButton(
        text="⏭ Пропустить",
        callback_data="principle_skip"
    ))
    builder.row(*nav_buttons)

    # Отмена
    builder.row(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="principles_cancel"
    ))

    return builder.as_markup()


def get_day_complete_keyboard(day: int, is_last_day: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура после завершения дня оценки"""
    builder = InlineKeyboardBuilder()

    if is_last_day:
        builder.row(InlineKeyboardButton(
            text="📊 Посмотреть итоги",
            callback_data="principles_results"
        ))
    else:
        builder.row(InlineKeyboardButton(
            text=f"✅ День {day} завершён!",
            callback_data="principles_day_done"
        ))

    builder.row(InlineKeyboardButton(
        text="🔙 Главное меню",
        callback_data="main_menu"
    ))

    return builder.as_markup()


def get_assessment_results_keyboard(assessment_id: int) -> InlineKeyboardMarkup:
    """Клавиатура результатов оценки"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="📊 Детальный отчёт",
        callback_data=f"principles_detail:{assessment_id}"
    ))

    builder.row(InlineKeyboardButton(
        text="🔙 Главное меню",
        callback_data="main_menu"
    ))

    return builder.as_markup()


def get_history_keyboard(assessments: list) -> InlineKeyboardMarkup:
    """Клавиатура истории оценок"""
    builder = InlineKeyboardBuilder()

    month_names = ["", "Янв", "Фев", "Мар", "Апр", "Май",
                   "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]

    for a in assessments[:6]:
        avg = a.average_score / 10 if a.average_score else 0
        text = f"{month_names[a.month]} {a.year}: {avg:.1f}/10"
        builder.row(InlineKeyboardButton(
            text=text,
            callback_data=f"principles_detail:{a.id}"
        ))

    builder.row(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="principles_show"
    ))

    return builder.as_markup()


def get_detail_keyboard(assessment_id: int) -> InlineKeyboardMarkup:
    """Клавиатура детального отчёта"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="🔴 Проблемные зоны",
        callback_data=f"principles_problems:{assessment_id}"
    ))

    builder.row(InlineKeyboardButton(
        text="🟢 Сильные стороны",
        callback_data=f"principles_success:{assessment_id}"
    ))

    builder.row(InlineKeyboardButton(
        text="🔙 К истории",
        callback_data="principles_history"
    ))

    return builder.as_markup()


def get_principles_start_keyboard() -> InlineKeyboardMarkup:
    """Кнопка начала оценки (для напоминаний)"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="📝 Начать оценку",
        callback_data="principles_start"
    ))

    return builder.as_markup()
