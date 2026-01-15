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


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Команда /settings"""
    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Сначала запусти /start")
        return

    await message.answer(
        f"⚙️ *Настройки*\n\n"
        f"🌅 Утреннее напоминание: *{user.morning_hour:02d}:{user.morning_minute:02d}*\n"
        f"🌙 Вечернее напоминание: *{user.evening_hour:02d}:{user.evening_minute:02d}*\n"
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

    await callback.message.edit_text(
        f"⚙️ *Настройки*\n\n"
        f"🌅 Утреннее напоминание: *{user.morning_hour:02d}:{user.morning_minute:02d}*\n"
        f"🌙 Вечернее напоминание: *{user.evening_hour:02d}:{user.evening_minute:02d}*\n"
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
