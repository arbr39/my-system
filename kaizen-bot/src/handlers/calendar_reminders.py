"""
Handlers для follow-up после событий и настроек напоминаний.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.database.models import get_session, CalendarEventReminder, User
from src.database.crud import get_user_by_telegram_id, create_inbox_item
from src.keyboards.inline_calendar import get_reminder_settings_keyboard
from src.keyboards.inline import get_main_menu

router = Router()


class FollowupStates(StatesGroup):
    """FSM состояния для follow-up"""
    waiting_for_action_items = State()


# === Follow-up handlers ===

@router.callback_query(F.data.startswith("followup_yes:"))
async def start_followup_capture(callback: CallbackQuery, state: FSMContext):
    """Пользователь хочет записать action items"""
    reminder_id = int(callback.data.split(":")[1])

    await state.update_data(reminder_id=reminder_id)
    await state.set_state(FollowupStates.waiting_for_action_items)

    await callback.message.edit_text(
        "📝 *Записываю action items*\n\n"
        "Напиши что нужно сделать после этой встречи.\n"
        "Каждый пункт добавится в Inbox.",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("followup_no:"))
async def skip_followup(callback: CallbackQuery):
    """Нет action items от этого события"""
    await callback.message.edit_text(
        "✅ Отлично, продолжаем работать!",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(FollowupStates.waiting_for_action_items)
async def process_action_items(message: Message, state: FSMContext):
    """Создать inbox item из action items"""
    data = await state.get_data()
    reminder_id = data.get("reminder_id")

    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await state.clear()
        return

    # Получаем reminder для контекста
    session = get_session()
    try:
        reminder = session.query(CalendarEventReminder).filter(
            CalendarEventReminder.id == reminder_id
        ).first()

        event_name = reminder.event_summary if reminder else "Встреча"

        # Создаём inbox item с тегом follow-up
        text = f"[follow-up: {event_name}] {message.text}"
        create_inbox_item(user.id, text)

        # Сохраняем ответ в reminder
        if reminder:
            reminder.followup_response = message.text
            session.commit()

        await message.answer(
            f"✅ *Добавлено в Inbox!*\n\n"
            f"_{message.text}_\n\n"
            f"Источник: {event_name}",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )

    finally:
        session.close()

    await state.clear()


# === Reminder settings handlers ===

@router.callback_query(F.data == "calendar_reminder_settings")
async def show_reminder_settings(callback: CallbackQuery):
    """Показать настройки напоминаний"""
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    await callback.message.edit_text(
        "🔔 *Настройки напоминаний*\n\n"
        "Напоминания о событиях из Google Calendar.\n"
        f"Текущее время: за *{user.reminder_minutes_before or 15}* мин до события.\n\n"
        f"Тихие часы: {user.quiet_hours_start or 23}:00 - {user.quiet_hours_end or 7}:00",
        parse_mode="Markdown",
        reply_markup=get_reminder_settings_keyboard(
            current_minutes=user.reminder_minutes_before or 15,
            reminders_enabled=user.event_reminders_enabled if user.event_reminders_enabled is not None else True
        )
    )
    await callback.answer()


@router.callback_query(F.data == "reminder_toggle")
async def toggle_reminders(callback: CallbackQuery):
    """Включить/выключить напоминания"""
    session = get_session()
    try:
        user = session.query(User).filter(
            User.telegram_id == callback.from_user.id
        ).first()

        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return

        # Toggle
        current = user.event_reminders_enabled if user.event_reminders_enabled is not None else True
        user.event_reminders_enabled = not current
        session.commit()

        status = "включены" if user.event_reminders_enabled else "выключены"
        await callback.answer(f"Напоминания {status}!")

        # Обновляем сообщение
        await callback.message.edit_reply_markup(
            reply_markup=get_reminder_settings_keyboard(
                current_minutes=user.reminder_minutes_before or 15,
                reminders_enabled=user.event_reminders_enabled
            )
        )

    finally:
        session.close()


@router.callback_query(F.data.startswith("reminder_time:"))
async def set_reminder_time(callback: CallbackQuery):
    """Установить время напоминания (15/30/60 мин)"""
    minutes = int(callback.data.split(":")[1])

    session = get_session()
    try:
        user = session.query(User).filter(
            User.telegram_id == callback.from_user.id
        ).first()

        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return

        user.reminder_minutes_before = minutes
        session.commit()

        await callback.answer(f"Напоминания за {minutes} мин до события")

        # Обновляем сообщение
        await callback.message.edit_reply_markup(
            reply_markup=get_reminder_settings_keyboard(
                current_minutes=minutes,
                reminders_enabled=user.event_reminders_enabled if user.event_reminders_enabled is not None else True
            )
        )

    finally:
        session.close()
