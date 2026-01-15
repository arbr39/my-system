"""
Клавиатуры для пользовательских задач
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_tasks_main_menu(tasks: list, completions_today: dict, stats_today: dict) -> InlineKeyboardMarkup:
    """
    Главное меню задач.

    Args:
        tasks: список UserTask
        completions_today: dict {task_id: count} - количество выполнений за сегодня
        stats_today: dict {"tasks_completed": int, "total_earned": int}
    """
    builder = InlineKeyboardBuilder()

    # Статистика за день
    if stats_today["tasks_completed"] > 0:
        builder.row(InlineKeyboardButton(
            text=f"📊 Сегодня: {stats_today['tasks_completed']} задач, +{stats_today['total_earned']}₽",
            callback_data="tasks_stats_info"
        ))

    # Список задач
    if tasks:
        for task in tasks:
            # Для повторяющихся задач показываем статус выполнения
            completed_count = completions_today.get(task.id, 0)

            if task.is_recurring:
                if completed_count > 0:
                    text = f"✅ {task.name} — {task.reward_amount}₽ (выполнено)"
                    callback_data = f"task_view:{task.id}"
                else:
                    text = f"⭕ {task.name} — {task.reward_amount}₽"
                    callback_data = f"task_complete:{task.id}"
            else:
                # Одноразовая задача
                text = f"🎯 {task.name} — {task.reward_amount}₽"
                callback_data = f"task_complete:{task.id}"

            builder.row(InlineKeyboardButton(
                text=text,
                callback_data=callback_data
            ))
    else:
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
