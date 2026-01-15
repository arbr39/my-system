from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌅 Утренний кайдзен", callback_data="morning_start")
    )
    builder.row(
        InlineKeyboardButton(text="🌙 Вечерняя рефлексия", callback_data="evening_start")
    )
    builder.row(
        InlineKeyboardButton(text="📥 Inbox", callback_data="inbox_show"),
        InlineKeyboardButton(text="💭 Когда-нибудь", callback_data="someday_show")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
        InlineKeyboardButton(text="🎯 Цели", callback_data="goals")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Weekly Review", callback_data="review_start"),
        InlineKeyboardButton(text="💰 Награды", callback_data="rewards_show")
    )
    builder.row(
        InlineKeyboardButton(text="✅ Мои задачи", callback_data="tasks_show")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Принципы", callback_data="principles_show"),
        InlineKeyboardButton(text="📅 Даты", callback_data="dates_show")
    )
    builder.row(
        InlineKeyboardButton(text="🗓 Calendar", callback_data="calendar_show"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
    )
    return builder.as_markup()


def get_task_completion_keyboard(task_1: str, task_2: str, task_3: str,
                                  t1_done: bool = False, t2_done: bool = False,
                                  t3_done: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для отметки выполненных задач"""
    builder = InlineKeyboardBuilder()

    check_1 = "✅" if t1_done else "⬜"
    check_2 = "✅" if t2_done else "⬜"
    check_3 = "✅" if t3_done else "⬜"

    if task_1:
        builder.row(InlineKeyboardButton(
            text=f"{check_1} {task_1[:40]}{'...' if len(task_1) > 40 else ''}",
            callback_data=f"toggle_task:1"
        ))
    if task_2:
        builder.row(InlineKeyboardButton(
            text=f"{check_2} {task_2[:40]}{'...' if len(task_2) > 40 else ''}",
            callback_data=f"toggle_task:2"
        ))
    if task_3:
        builder.row(InlineKeyboardButton(
            text=f"{check_3} {task_3[:40]}{'...' if len(task_3) > 40 else ''}",
            callback_data=f"toggle_task:3"
        ))

    builder.row(InlineKeyboardButton(text="✅ Готово", callback_data="tasks_done"))
    return builder.as_markup()


def get_skip_keyboard() -> InlineKeyboardMarkup:
    """Кнопка пропуска"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip"))
    return builder.as_markup()


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"),
        InlineKeyboardButton(text="✏️ Изменить", callback_data="edit")
    )
    return builder.as_markup()


def get_goals_keyboard(goals: list) -> InlineKeyboardMarkup:
    """Клавиатура целей"""
    builder = InlineKeyboardBuilder()
    for goal in goals:
        status_emoji = {"active": "🎯", "paused": "⏸️", "completed": "✅"}.get(goal.status, "🎯")
        builder.row(InlineKeyboardButton(
            text=f"{status_emoji} {goal.title[:30]}",
            callback_data=f"goal:{goal.id}"
        ))
    builder.row(InlineKeyboardButton(text="➕ Добавить цель", callback_data="add_goal"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu"))
    return builder.as_markup()


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка назад"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu"))
    return builder.as_markup()


# ============ GTD INBOX ============

def get_inbox_keyboard(items: list, page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    """Клавиатура inbox с пагинацией"""
    builder = InlineKeyboardBuilder()

    start = page * per_page
    end = start + per_page
    page_items = items[start:end]

    for item in page_items:
        text = item.text[:35] + ('...' if len(item.text) > 35 else '')
        builder.row(InlineKeyboardButton(
            text=f"📥 {text}",
            callback_data=f"inbox_item:{item.id}"
        ))

    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"inbox_page:{page-1}"))
    if end < len(items):
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"inbox_page:{page+1}"))
    if nav_buttons:
        builder.row(*nav_buttons)

    # Действия
    builder.row(InlineKeyboardButton(text="🔍 Фильтр", callback_data="inbox_filter"))
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu"))

    return builder.as_markup()


def get_inbox_empty_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для пустого inbox"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def get_inbox_item_keyboard(item_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для обработки элемента inbox"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Выполнено", callback_data=f"inbox_quick_done:{item_id}"))
    builder.row(InlineKeyboardButton(text="⚡ Обработать", callback_data=f"inbox_process:{item_id}"))
    builder.row(
        InlineKeyboardButton(text="📦 Когда-нибудь", callback_data=f"inbox_someday:{item_id}"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"inbox_delete:{item_id}")
    )
    builder.row(InlineKeyboardButton(text="🔙 К списку", callback_data="inbox_show"))
    return builder.as_markup()


def get_two_minute_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура 'Займет < 2 минут?'"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, < 2 мин", callback_data="inbox_2min_yes"),
        InlineKeyboardButton(text="❌ Нет, дольше", callback_data="inbox_2min_no")
    )
    return builder.as_markup()


def get_energy_keyboard() -> InlineKeyboardMarkup:
    """Выбор уровня энергии"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔋🔋🔋 Высокая", callback_data="inbox_energy:high"))
    builder.row(InlineKeyboardButton(text="🔋🔋 Средняя", callback_data="inbox_energy:medium"))
    builder.row(InlineKeyboardButton(text="🔋 Низкая", callback_data="inbox_energy:low"))
    builder.row(InlineKeyboardButton(text="⏭ Пропустить", callback_data="inbox_energy:skip"))
    return builder.as_markup()


def get_time_estimate_keyboard() -> InlineKeyboardMarkup:
    """Оценка времени"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏱ 5 мин", callback_data="inbox_time:5min"),
        InlineKeyboardButton(text="⏱ 15 мин", callback_data="inbox_time:15min")
    )
    builder.row(
        InlineKeyboardButton(text="⏱ 30 мин", callback_data="inbox_time:30min"),
        InlineKeyboardButton(text="⏱ 1 час+", callback_data="inbox_time:1hour")
    )
    builder.row(InlineKeyboardButton(text="⏭ Пропустить", callback_data="inbox_time:skip"))
    return builder.as_markup()


def get_inbox_filter_keyboard() -> InlineKeyboardMarkup:
    """Меню фильтрации inbox"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔋 По энергии", callback_data="inbox_filter_energy"))
    builder.row(InlineKeyboardButton(text="⏱ По времени", callback_data="inbox_filter_time"))
    builder.row(InlineKeyboardButton(text="📋 Все задачи", callback_data="inbox_show"))
    return builder.as_markup()


def get_filter_energy_keyboard() -> InlineKeyboardMarkup:
    """Фильтр по энергии"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔋🔋🔋 Высокая", callback_data="inbox_fe:high"))
    builder.row(InlineKeyboardButton(text="🔋🔋 Средняя", callback_data="inbox_fe:medium"))
    builder.row(InlineKeyboardButton(text="🔋 Низкая", callback_data="inbox_fe:low"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="inbox_filter"))
    return builder.as_markup()


def get_filter_time_keyboard() -> InlineKeyboardMarkup:
    """Фильтр по времени"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏱ 5 мин", callback_data="inbox_ft:5min"),
        InlineKeyboardButton(text="⏱ 15 мин", callback_data="inbox_ft:15min")
    )
    builder.row(
        InlineKeyboardButton(text="⏱ 30 мин", callback_data="inbox_ft:30min"),
        InlineKeyboardButton(text="⏱ 1 час+", callback_data="inbox_ft:1hour")
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="inbox_filter"))
    return builder.as_markup()


def get_inbox_done_keyboard() -> InlineKeyboardMarkup:
    """Задача обработана"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Сделал!", callback_data="inbox_mark_done"))
    builder.row(InlineKeyboardButton(text="📥 Оставить в Inbox", callback_data="inbox_show"))
    return builder.as_markup()


# ============ GTD SOMEDAY ============

def get_someday_keyboard(items: list) -> InlineKeyboardMarkup:
    """Клавиатура списка 'когда-нибудь'"""
    builder = InlineKeyboardBuilder()

    for item in items[:10]:
        text = item.text[:35] + ('...' if len(item.text) > 35 else '')
        builder.row(InlineKeyboardButton(
            text=f"💭 {text}",
            callback_data=f"someday_item:{item.id}"
        ))

    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def get_someday_empty_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для пустого someday"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def get_someday_item_keyboard(item_id: int) -> InlineKeyboardMarkup:
    """Действия с элементом someday"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📥 В Inbox (активировать)", callback_data=f"someday_activate:{item_id}"))
    builder.row(InlineKeyboardButton(text="🗑 Удалить", callback_data=f"someday_delete:{item_id}"))
    builder.row(InlineKeyboardButton(text="🔙 К списку", callback_data="someday_show"))
    return builder.as_markup()


# ============ GTD PRIORITY TASK ============

def get_priority_keyboard(task_1: str = "", task_2: str = "", task_3: str = "") -> InlineKeyboardMarkup:
    """Выбор приоритетной задачи"""
    builder = InlineKeyboardBuilder()

    t1 = task_1[:30] + ('...' if len(task_1) > 30 else '') if task_1 else "Задача 1"
    t2 = task_2[:30] + ('...' if len(task_2) > 30 else '') if task_2 else "Задача 2"
    t3 = task_3[:30] + ('...' if len(task_3) > 30 else '') if task_3 else "Задача 3"

    builder.row(InlineKeyboardButton(text=f"1️⃣ {t1}", callback_data="priority:1"))
    builder.row(InlineKeyboardButton(text=f"2️⃣ {t2}", callback_data="priority:2"))
    builder.row(InlineKeyboardButton(text=f"3️⃣ {t3}", callback_data="priority:3"))

    return builder.as_markup()


# ============ GTD WEEKLY REVIEW ============

def get_review_start_keyboard() -> InlineKeyboardMarkup:
    """Начало weekly review"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🚀 Начать Review", callback_data="review_begin"))
    builder.row(InlineKeyboardButton(text="⏭ Позже", callback_data="main_menu"))
    return builder.as_markup()


def get_review_inbox_keyboard(item_id: int, remaining: int) -> InlineKeyboardMarkup:
    """Клавиатура для обработки inbox в review"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Обработано", callback_data=f"review_inbox_done:{item_id}"))
    builder.row(
        InlineKeyboardButton(text="📦 Когда-нибудь", callback_data=f"review_inbox_someday:{item_id}"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"review_inbox_delete:{item_id}")
    )
    if remaining > 0:
        builder.row(InlineKeyboardButton(text=f"➡️ Далее ({remaining})", callback_data="review_inbox_next"))
    else:
        builder.row(InlineKeyboardButton(text="✅ Inbox пуст! Далее →", callback_data="review_inbox_finish"))
    return builder.as_markup()


def get_review_goals_keyboard(goals: list) -> InlineKeyboardMarkup:
    """Клавиатура просмотра целей в review"""
    builder = InlineKeyboardBuilder()
    for goal in goals:
        status_emoji = {"active": "🎯", "paused": "⏸️", "completed": "✅"}.get(goal.status, "🎯")
        builder.row(InlineKeyboardButton(
            text=f"{status_emoji} {goal.title[:30]}",
            callback_data=f"review_goal:{goal.id}"
        ))
    builder.row(InlineKeyboardButton(text="✅ Цели просмотрены", callback_data="review_goals_done"))
    return builder.as_markup()


def get_review_someday_keyboard(items: list) -> InlineKeyboardMarkup:
    """Клавиатура просмотра someday в review"""
    builder = InlineKeyboardBuilder()
    for item in items[:5]:
        text = item.text[:30] + ('...' if len(item.text) > 30 else '')
        builder.row(InlineKeyboardButton(
            text=f"💭 {text}",
            callback_data=f"review_someday:{item.id}"
        ))
    builder.row(InlineKeyboardButton(text="✅ Someday просмотрен", callback_data="review_someday_done"))
    return builder.as_markup()


def get_review_skip_keyboard() -> InlineKeyboardMarkup:
    """Пропуск шага в review"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⏭️ Пропустить", callback_data="review_skip"))
    return builder.as_markup()
