"""
Клавиатуры для системы наград
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_rewards_main_menu(balance: int, total_earned: int = 0) -> InlineKeyboardMarkup:
    """Главное меню наград с балансом"""
    builder = InlineKeyboardBuilder()

    # Баланс как информационная кнопка
    builder.row(InlineKeyboardButton(
        text=f"💰 Баланс: {balance}₽",
        callback_data="rewards_balance_info"
    ))

    # Награды и добавление
    builder.row(
        InlineKeyboardButton(text="🎁 Мои награды", callback_data="rewards_items"),
        InlineKeyboardButton(text="➕ Добавить", callback_data="reward_add")
    )

    # История
    builder.row(
        InlineKeyboardButton(text="📜 История", callback_data="rewards_history")
    )

    # Настройки
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки ставок", callback_data="rewards_settings")
    )

    # Назад
    builder.row(
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")
    )

    return builder.as_markup()


def get_reward_items_keyboard(items: list, balance: int) -> InlineKeyboardMarkup:
    """Список наград пользователя"""
    builder = InlineKeyboardBuilder()

    if not items:
        builder.row(InlineKeyboardButton(
            text="📭 Список пуст",
            callback_data="rewards_empty"
        ))
    else:
        for item in items:
            can_afford = "✅" if balance >= item.price else "❌"
            text = f"{can_afford} {item.name} — {item.price}₽"
            builder.row(InlineKeyboardButton(
                text=text,
                callback_data=f"reward_view:{item.id}"
            ))

    builder.row(InlineKeyboardButton(
        text="➕ Добавить награду",
        callback_data="reward_add"
    ))

    builder.row(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="rewards_show"
    ))

    return builder.as_markup()


def get_reward_view_keyboard(item_id: int, can_afford: bool) -> InlineKeyboardMarkup:
    """Просмотр награды с возможностью потратить"""
    builder = InlineKeyboardBuilder()

    if can_afford:
        builder.row(InlineKeyboardButton(
            text="🎉 Потратить!",
            callback_data=f"reward_spend:{item_id}"
        ))

    builder.row(
        InlineKeyboardButton(text="✏️ Изменить", callback_data=f"reward_edit:{item_id}"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"reward_delete:{item_id}")
    )

    builder.row(InlineKeyboardButton(
        text="🔙 К списку",
        callback_data="rewards_items"
    ))

    return builder.as_markup()


def get_spend_confirm_keyboard(item_id: int) -> InlineKeyboardMarkup:
    """Подтверждение траты"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="✅ Да, потратить!",
        callback_data=f"reward_spend_confirm:{item_id}"
    ))

    builder.row(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data=f"reward_view:{item_id}"
    ))

    return builder.as_markup()


def get_delete_confirm_keyboard(item_id: int) -> InlineKeyboardMarkup:
    """Подтверждение удаления"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="🗑 Да, удалить",
        callback_data=f"reward_delete_confirm:{item_id}"
    ))

    builder.row(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data=f"reward_view:{item_id}"
    ))

    return builder.as_markup()


def get_history_keyboard(has_more: bool = False, page: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура истории транзакций"""
    builder = InlineKeyboardBuilder()

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"rewards_history:{page - 1}"
        ))
    if has_more:
        nav_buttons.append(InlineKeyboardButton(
            text="➡️ Далее",
            callback_data=f"rewards_history:{page + 1}"
        ))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(InlineKeyboardButton(
        text="🔙 Меню наград",
        callback_data="rewards_show"
    ))

    return builder.as_markup()


def get_settings_keyboard(fund) -> InlineKeyboardMarkup:
    """Меню настроек ставок"""
    builder = InlineKeyboardBuilder()

    # Текущие ставки
    builder.row(InlineKeyboardButton(
        text=f"🌅 Утро: {fund.rate_morning_kaizen}₽",
        callback_data="rate_edit:morning_kaizen"
    ))
    builder.row(InlineKeyboardButton(
        text=f"🌙 Вечер: {fund.rate_evening_reflection}₽",
        callback_data="rate_edit:evening_reflection"
    ))
    builder.row(InlineKeyboardButton(
        text=f"✅ Задача: {fund.rate_task_done}₽",
        callback_data="rate_edit:task_done"
    ))
    builder.row(InlineKeyboardButton(
        text=f"⭐ Главная задача: +{fund.rate_priority_task_bonus}₽",
        callback_data="rate_edit:priority_task_bonus"
    ))
    builder.row(InlineKeyboardButton(
        text=f"🏃 Спорт: {fund.rate_exercise}₽",
        callback_data="rate_edit:exercise"
    ))
    builder.row(InlineKeyboardButton(
        text=f"🥗 Питание: {fund.rate_eating_well}₽",
        callback_data="rate_edit:eating_well"
    ))
    builder.row(InlineKeyboardButton(
        text=f"📋 Weekly Review: {fund.rate_weekly_review}₽",
        callback_data="rate_edit:weekly_review"
    ))

    # Штрафы
    penalties_status = "✅ Вкл" if fund.penalties_enabled else "❌ Выкл"
    builder.row(InlineKeyboardButton(
        text=f"⚠️ Штрафы: {penalties_status}",
        callback_data="toggle_penalties"
    ))

    builder.row(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="rewards_show"
    ))

    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Кнопка отмены"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="rewards_show"
    ))
    return builder.as_markup()


def get_skip_category_keyboard() -> InlineKeyboardMarkup:
    """Пропустить категорию при добавлении награды"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="⏭ Пропустить категорию",
        callback_data="reward_skip_category"
    ))
    builder.row(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="rewards_show"
    ))
    return builder.as_markup()
