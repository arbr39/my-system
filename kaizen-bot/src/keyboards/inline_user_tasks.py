"""
Клавиатуры для пользовательских задач
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_tasks_main_menu(
    tasks: list,
    completions_today: dict,
    stats_today: dict,
    inbox_tasks: list = None,
    daily_entry = None,
    filter_type: str = "all"
) -> InlineKeyboardMarkup:
    """
    Главное меню задач с поддержкой inbox и daily tasks (unified view).

    Args:
        tasks: список UserTask
        completions_today: dict {task_id: count} - количество выполнений за сегодня
        stats_today: dict {"tasks_completed": int, "total_earned": int}
        inbox_tasks: список InboxItem (опционально)
        daily_entry: DailyEntry за сегодня (опционально)
        filter_type: "all" | "user_tasks" | "inbox" | "daily"
    """
    builder = InlineKeyboardBuilder()

    # Статистика за день (расширенная)
    if stats_today["tasks_completed"] > 0:
        builder.row(InlineKeyboardButton(
            text=f"📊 Сегодня: {stats_today['tasks_completed']} задач, +{stats_today['total_earned']}₽",
            callback_data="tasks_stats_info"
        ))

    # Задачи дня из утреннего кайдзена (показываем первыми!)
    if filter_type in ["all", "daily"] and daily_entry:
        daily_tasks = [
            (1, daily_entry.task_1, daily_entry.task_1_done),
            (2, daily_entry.task_2, daily_entry.task_2_done),
            (3, daily_entry.task_3, daily_entry.task_3_done)
        ]

        for task_num, task_text, task_done in daily_tasks:
            if not task_text:
                continue

            is_priority = (daily_entry.priority_task == task_num)
            priority_marker = "⭐" if is_priority else ""

            # Обрезать длинный текст
            text_snippet = task_text[:35] + "..." if len(task_text) > 35 else task_text

            if task_done:
                text = f"✅ {text_snippet} {priority_marker}"
                callback_data = f"daily_task_info:{daily_entry.id}:{task_num}"
            else:
                reward = 70 if is_priority else 20
                text = f"📅 {text_snippet} — {reward}₽ {priority_marker}"
                callback_data = f"daily_task_complete:{daily_entry.id}:{task_num}"

            builder.row(InlineKeyboardButton(
                text=text,
                callback_data=callback_data
            ))

    # Кнопки фильтра (если есть разные типы задач)
    has_multiple_types = sum([bool(tasks), bool(inbox_tasks), bool(daily_entry)]) > 1
    if has_multiple_types and filter_type == "all":
        filter_buttons = []
        filter_buttons.append(InlineKeyboardButton(
            text="📋 Все",
            callback_data="tasks_filter:all"
        ))
        if daily_entry:
            filter_buttons.append(InlineKeyboardButton(
                text="📅 День",
                callback_data="tasks_filter:daily"
            ))
        if tasks:
            filter_buttons.append(InlineKeyboardButton(
                text="⭕ Мои",
                callback_data="tasks_filter:user_tasks"
            ))
        if inbox_tasks:
            filter_buttons.append(InlineKeyboardButton(
                text="📥 Inbox",
                callback_data="tasks_filter:inbox"
            ))
        builder.row(*filter_buttons[:4])  # Макс 4 кнопки в ряд

    # User tasks (если фильтр разрешает)
    if filter_type in ["all", "user_tasks"] and tasks:
        for task in tasks:
            completed_count = completions_today.get(task.id, 0)

            if task.is_recurring:
                if completed_count > 0:
                    text = f"✅ {task.name} — {task.reward_amount}₽"
                    callback_data = f"task_view:{task.id}"
                else:
                    text = f"⭕ {task.name} — {task.reward_amount}₽"
                    callback_data = f"task_complete:{task.id}"
            else:
                text = f"🎯 {task.name} — {task.reward_amount}₽"
                callback_data = f"task_complete:{task.id}"

            builder.row(InlineKeyboardButton(
                text=text,
                callback_data=callback_data
            ))

    # Inbox tasks (если фильтр разрешает)
    if filter_type in ["all", "inbox"] and inbox_tasks:
        for item in inbox_tasks:
            # Обрезать длинный текст
            text_snippet = item.text[:40] + "..." if len(item.text) > 40 else item.text
            text = f"📥 {text_snippet}"

            builder.row(InlineKeyboardButton(
                text=text,
                callback_data=f"inbox_quick_done:{item.id}"
            ))

    # Пустое состояние
    if not tasks and not inbox_tasks and not daily_entry:
        builder.row(InlineKeyboardButton(
            text="📭 Задач пока нет",
            callback_data="tasks_empty"
        ))

    # Кнопки управления
    builder.row(InlineKeyboardButton(
        text="➕ Добавить задачу",
        callback_data="task_add"
    ))

    builder.row(InlineKeyboardButton(
        text="🔙 Главное меню",
        callback_data="main_menu"
    ))

    return builder.as_markup()


def get_task_view_keyboard(task_id: int, already_completed_today: bool, is_recurring: bool) -> InlineKeyboardMarkup:
    """Просмотр задачи с деталями"""
    builder = InlineKeyboardBuilder()

    # Кнопка "Выполнено" (disabled если уже выполнена сегодня)
    if is_recurring and already_completed_today:
        builder.row(InlineKeyboardButton(
            text="✅ Выполнено сегодня",
            callback_data="task_already_completed"
        ))
    else:
        builder.row(InlineKeyboardButton(
            text="✅ Выполнить",
            callback_data=f"task_complete:{task_id}"
        ))

    # Добавить в календарь
    builder.row(InlineKeyboardButton(
        text="📅 В календарь",
        callback_data=f"task_to_calendar:{task_id}"
    ))

    # Управление
    builder.row(
        InlineKeyboardButton(
            text="📊 История",
            callback_data=f"task_history:{task_id}"
        ),
        InlineKeyboardButton(
            text="✏️ Редактировать",
            callback_data=f"task_edit:{task_id}"
        )
    )

    builder.row(InlineKeyboardButton(
        text="🗑 Удалить",
        callback_data=f"task_delete:{task_id}"
    ))

    builder.row(InlineKeyboardButton(
        text="🔙 К списку задач",
        callback_data="tasks_show"
    ))

    return builder.as_markup()


def get_task_type_keyboard() -> InlineKeyboardMarkup:
    """Выбор типа задачи: повторяющаяся или одноразовая"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="🔄 Повторяющаяся (можно каждый день)",
        callback_data="task_type:recurring"
    ))

    builder.row(InlineKeyboardButton(
        text="🎯 Одноразовая (выполнить один раз)",
        callback_data="task_type:once"
    ))

    builder.row(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="task_cancel"
    ))

    return builder.as_markup()


def get_task_category_keyboard() -> InlineKeyboardMarkup:
    """Выбор категории задачи + кнопка Пропустить"""
    builder = InlineKeyboardBuilder()

    categories = [
        ("🏃 Спорт и здоровье", "sport"),
        ("📚 Обучение", "learning"),
        ("🌱 Личное развитие", "personal"),
        ("💼 Работа над проектами", "work")
    ]

    for label, value in categories:
        builder.row(InlineKeyboardButton(
            text=label,
            callback_data=f"task_category:{value}"
        ))

    builder.row(InlineKeyboardButton(
        text="⏭ Пропустить",
        callback_data="task_category:skip"
    ))

    builder.row(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="task_cancel"
    ))

    return builder.as_markup()


def get_task_delete_confirm_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Подтверждение удаления задачи"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Да, удалить",
            callback_data=f"task_delete_confirm:{task_id}"
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"task_view:{task_id}"
        )
    )

    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Кнопка отмены"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="task_cancel"
    ))

    return builder.as_markup()


def get_task_history_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Кнопки для истории выполнений"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="🔙 К задаче",
        callback_data=f"task_view:{task_id}"
    ))

    return builder.as_markup()
