from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.database.crud import get_user_by_telegram_id, update_user_settings
from src.keyboards.inline import get_main_menu

router = Router()


class SettingsStates(StatesGroup):
    """Состояния настроек"""
    morning_time = State()
    evening_time = State()


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌅 Утреннее напоминание", callback_data="set_morning")
    )
    builder.row(
        InlineKeyboardButton(text="🌙 Вечернее напоминание", callback_data="set_evening")
    )
    builder.row(
        InlineKeyboardButton(text="📝 Напоминание о задачах", callback_data="set_task_reminder")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")
    )
    return builder.as_markup()


def get_time_keyboard(setting_type: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора времени"""
    builder = InlineKeyboardBuilder()

    if setting_type == "morning":
        times = ["06:00", "06:30", "07:00", "07:30", "08:00", "08:30", "09:00"]
    else:
        times = ["20:00", "20:30", "21:00", "21:30", "22:00", "22:30", "23:00"]

    # По 3 кнопки в ряд
    row = []
    for time in times:
        row.append(InlineKeyboardButton(text=time, callback_data=f"time_{setting_type}:{time}"))
        if len(row) == 3:
            builder.row(*row)
            row = []
    if row:
        builder.row(*row)

    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="settings")
    )
    return builder.as_markup()


def get_task_reminder_settings_keyboard(enabled: bool, hour: int, minute: int) -> InlineKeyboardMarkup:
    """Клавиатура настроек напоминаний о задачах"""
    builder = InlineKeyboardBuilder()

    # Статус
    status_emoji = "✅" if enabled else "❌"
    builder.row(InlineKeyboardButton(
        text=f"{status_emoji} Напоминания: {'Включены' if enabled else 'Выключены'}",
        callback_data="toggle_task_reminder"
    ))

    # Время (если включено)
    if enabled:
        builder.row(InlineKeyboardButton(
            text=f"🕐 Время: {hour:02d}:{minute:02d}",
            callback_data="set_task_reminder_time"
        ))

    builder.row(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="settings"
    ))

    return builder.as_markup()


def get_task_reminder_time_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора времени напоминания о задачах"""
    builder = InlineKeyboardBuilder()

    times = [
        "09:00", "10:00", "11:00",
        "12:00", "13:00", "14:00",
        "15:00", "16:00", "17:00",
        "18:00"
    ]

    # По 3 кнопки в ряд
    row = []
    for time in times:
        row.append(InlineKeyboardButton(
            text=time,
            callback_data=f"time_task_reminder:{time}"
        ))
        if len(row) == 3:
            builder.row(*row)
            row = []
    if row:
        builder.row(*row)

    builder.row(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="set_task_reminder"
    ))

    return builder.as_markup()


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Команда /settings"""
    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Сначала запусти /start")
        return

    task_status = "✅" if user.task_reminders_enabled else "❌"
    task_time = f"{user.task_reminder_hour:02d}:{user.task_reminder_minute:02d}" if user.task_reminders_enabled else "—"

    await message.answer(
        f"⚙️ *Настройки*\n\n"
        f"🌅 Утреннее напоминание: *{user.morning_hour:02d}:{user.morning_minute:02d}*\n"
        f"🌙 Вечернее напоминание: *{user.evening_hour:02d}:{user.evening_minute:02d}*\n"
        f"📝 Напоминание о задачах: *{task_status} {task_time}*\n"
        f"🌍 Таймзона: *{user.timezone}*\n\n"
        "Что изменить?",
        parse_mode="Markdown",
        reply_markup=get_settings_keyboard()
    )


@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery):
    """Показать настройки"""
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Сначала запусти /start")
        return

    task_status = "✅" if user.task_reminders_enabled else "❌"
    task_time = f"{user.task_reminder_hour:02d}:{user.task_reminder_minute:02d}" if user.task_reminders_enabled else "—"

    await callback.message.edit_text(
        f"⚙️ *Настройки*\n\n"
        f"🌅 Утреннее напоминание: *{user.morning_hour:02d}:{user.morning_minute:02d}*\n"
        f"🌙 Вечернее напоминание: *{user.evening_hour:02d}:{user.evening_minute:02d}*\n"
        f"📝 Напоминание о задачах: *{task_status} {task_time}*\n"
        f"🌍 Таймзона: *{user.timezone}*\n\n"
        "Что изменить?",
        parse_mode="Markdown",
        reply_markup=get_settings_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "set_morning")
async def set_morning_time(callback: CallbackQuery):
    """Выбор времени утреннего напоминания"""
    await callback.message.edit_text(
        "🌅 *Утреннее напоминание*\n\n"
        "Выбери время:",
        parse_mode="Markdown",
        reply_markup=get_time_keyboard("morning")
    )
    await callback.answer()


@router.callback_query(F.data == "set_evening")
async def set_evening_time(callback: CallbackQuery):
    """Выбор времени вечернего напоминания"""
    await callback.message.edit_text(
        "🌙 *Вечернее напоминание*\n\n"
        "Выбери время:",
        parse_mode="Markdown",
        reply_markup=get_time_keyboard("evening")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("time_morning:"))
async def save_morning_time(callback: CallbackQuery):
    """Сохранение времени утреннего напоминания"""
    time_str = callback.data.split(":")[1]
    hour, minute = map(int, time_str.split(":"))

    user = update_user_settings(
        telegram_id=callback.from_user.id,
        morning_hour=hour,
        morning_minute=minute
    )

    await callback.message.edit_text(
        f"✅ Утреннее напоминание установлено на *{hour:02d}:{minute:02d}*\n\n"
        "⚠️ Изменения вступят в силу после перезапуска бота на сервере.",
        parse_mode="Markdown",
        reply_markup=get_settings_keyboard()
    )
    await callback.answer("Сохранено!")


@router.callback_query(F.data.startswith("time_evening:"))
async def save_evening_time(callback: CallbackQuery):
    """Сохранение времени вечернего напоминания"""
    time_str = callback.data.split(":")[1]
    hour, minute = map(int, time_str.split(":"))

    user = update_user_settings(
        telegram_id=callback.from_user.id,
        evening_hour=hour,
        evening_minute=minute
    )

    await callback.message.edit_text(
        f"✅ Вечернее напоминание установлено на *{hour:02d}:{minute:02d}*\n\n"
        "⚠️ Изменения вступят в силу после перезапуска бота на сервере.",
        parse_mode="Markdown",
        reply_markup=get_settings_keyboard()
    )
    await callback.answer("Сохранено!")


@router.callback_query(F.data == "set_task_reminder")
async def show_task_reminder_settings(callback: CallbackQuery):
    """Показать настройки напоминаний о задачах"""
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    await callback.message.edit_text(
        "📝 *Напоминание о задачах*\n\n"
        "Бот будет напоминать о незавершённых задачах один раз в день.\n"
        "Ты сможешь отметить выполнение прямо из напоминания!",
        parse_mode="Markdown",
        reply_markup=get_task_reminder_settings_keyboard(
            user.task_reminders_enabled,
            user.task_reminder_hour or 14,
            user.task_reminder_minute or 0
        )
    )
    await callback.answer()


@router.callback_query(F.data == "toggle_task_reminder")
async def toggle_task_reminder(callback: CallbackQuery):
    """Включить/выключить напоминания о задачах"""
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка")
        return

    new_status = not user.task_reminders_enabled

    update_user_settings(
        telegram_id=callback.from_user.id,
        task_reminders_enabled=new_status
    )

    user = get_user_by_telegram_id(callback.from_user.id)
    status_text = "включены" if new_status else "выключены"

    await callback.message.edit_text(
        f"📝 *Напоминание о задачах*\n\n"
        f"Напоминания {status_text}!\n\n"
        "Бот будет напоминать о незавершённых задачах один раз в день.\n"
        "Ты сможешь отметить выполнение прямо из напоминания!",
        parse_mode="Markdown",
        reply_markup=get_task_reminder_settings_keyboard(
            user.task_reminders_enabled,
            user.task_reminder_hour or 14,
            user.task_reminder_minute or 0
        )
    )
    await callback.answer(f"Напоминания {status_text}")


@router.callback_query(F.data == "set_task_reminder_time")
async def show_task_reminder_time_selection(callback: CallbackQuery):
    """Показать выбор времени напоминания"""
    await callback.message.edit_text(
        "🕐 *Выбери время напоминания*\n\n"
        "Бот отправит сообщение с незавершёнными задачами в выбранное время.",
        parse_mode="Markdown",
        reply_markup=get_task_reminder_time_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("time_task_reminder:"))
async def save_task_reminder_time(callback: CallbackQuery):
    """Сохранить время напоминания о задачах"""
    time_str = callback.data.split(":", 1)[1]  # "14:00"
    hour, minute = map(int, time_str.split(":"))

    user = update_user_settings(
        telegram_id=callback.from_user.id,
        task_reminder_hour=hour,
        task_reminder_minute=minute
    )

    await callback.message.edit_text(
        f"✅ Напоминание о задачах установлено на *{hour:02d}:{minute:02d}*\n\n"
        "Изменения вступят в силу при следующей проверке.",
        parse_mode="Markdown",
        reply_markup=get_task_reminder_settings_keyboard(
            user.task_reminders_enabled,
            hour,
            minute
        )
    )
    await callback.answer("Время сохранено!")
