"""
Handlers для управления привычками в Google Calendar.

Позволяет:
- Включить/выключить привычки (спорт, питание) в календаре
- Настроить время для recurring событий
- Создать recurring события в Google Calendar
"""

from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.database.models import get_session, HabitCalendarEvent, User
from src.database.crud import get_user_by_telegram_id
from src.integrations.google_calendar import GoogleCalendarService
from src.keyboards.inline_calendar import get_habit_calendar_keyboard, get_habit_time_keyboard

router = Router()


class HabitCalendarStates(StatesGroup):
    """FSM состояния для настройки привычек"""
    selecting_time = State()


# Названия привычек для календаря
HABIT_NAMES = {
    "exercise": "🏃 Спорт",
    "eating": "🥗 Здоровое питание"
}


def _get_habit_status(user_id: int) -> dict:
    """Получить статус привычек пользователя"""
    session = get_session()
    try:
        habits = session.query(HabitCalendarEvent).filter(
            HabitCalendarEvent.user_id == user_id,
            HabitCalendarEvent.is_active == True
        ).all()

        return {
            "exercise": any(h.habit_type == "exercise" for h in habits),
            "eating": any(h.habit_type == "eating" for h in habits)
        }
    finally:
        session.close()


@router.callback_query(F.data == "habit_calendar_setup")
async def show_habit_calendar_setup(callback: CallbackQuery):
    """Показать меню настройки привычек в календаре"""
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    if not user.google_refresh_token_encrypted:
        await callback.answer("Сначала подключите Google Calendar", show_alert=True)
        return

    status = _get_habit_status(user.id)

    await callback.message.edit_text(
        "📅 *Привычки в Google Calendar*\n\n"
        "Выбранные привычки будут отображаться как\n"
        "ежедневные события в календаре.\n\n"
        "При выполнении привычки (в вечерней рефлексии)\n"
        "событие станет *зелёным* ✅",
        parse_mode="Markdown",
        reply_markup=get_habit_calendar_keyboard(
            exercise_active=status["exercise"],
            eating_active=status["eating"]
        )
    )
    await callback.answer()


@router.callback_query(F.data.startswith("habit_toggle:"))
async def toggle_habit_calendar(callback: CallbackQuery):
    """Включить/выключить привычку в календаре"""
    habit_type = callback.data.split(":")[1]

    if habit_type not in HABIT_NAMES:
        await callback.answer("Неизвестный тип привычки", show_alert=True)
        return

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    session = get_session()
    try:
        # Ищем существующую привычку
        habit = session.query(HabitCalendarEvent).filter(
            HabitCalendarEvent.user_id == user.id,
            HabitCalendarEvent.habit_type == habit_type
        ).first()

        if habit and habit.is_active:
            # Выключаем привычку
            habit.is_active = False
            session.commit()
            await callback.answer(f"{HABIT_NAMES[habit_type]} выключен")
        else:
            # Включаем — нужно выбрать время
            await callback.message.edit_text(
                f"⏰ *Выберите время для {HABIT_NAMES[habit_type]}*\n\n"
                "В это время будет создано ежедневное событие.",
                parse_mode="Markdown",
                reply_markup=get_habit_time_keyboard(habit_type)
            )
            await callback.answer()
            return

        # Обновляем UI
        status = _get_habit_status(user.id)
        await callback.message.edit_reply_markup(
            reply_markup=get_habit_calendar_keyboard(
                exercise_active=status["exercise"],
                eating_active=status["eating"]
            )
        )

    finally:
        session.close()


@router.callback_query(F.data.startswith("habit_time:"))
async def set_habit_time(callback: CallbackQuery):
    """Установить время для привычки и создать событие"""
    parts = callback.data.split(":")
    habit_type = parts[1]
    # time_str = parts[2]:parts[3] (например "18:00")
    time_str = f"{parts[2]}:{parts[3]}"

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    await _create_habit_event(callback, user, habit_type, time_str)


@router.callback_query(F.data.startswith("habit_custom_time:"))
async def start_custom_time_input(callback: CallbackQuery, state: FSMContext):
    """Начать ввод своего времени для привычки"""
    habit_type = callback.data.split(":")[1]

    await state.update_data(habit_type=habit_type)
    await state.set_state(HabitCalendarStates.selecting_time)

    await callback.message.edit_text(
        f"⏰ *Введите время для {HABIT_NAMES.get(habit_type, 'привычки')}*\n\n"
        "Формат: ЧЧ:ММ (например, 07:30 или 18:00)",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(HabitCalendarStates.selecting_time)
async def process_custom_time(message: Message, state: FSMContext):
    """Обработать введённое время"""
    data = await state.get_data()
    habit_type = data.get("habit_type")

    # Валидация формата времени
    time_str = message.text.strip()
    try:
        hour, minute = map(int, time_str.split(":"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError()
        time_str = f"{hour:02d}:{minute:02d}"
    except (ValueError, AttributeError):
        await message.answer(
            "❌ Неверный формат времени.\n"
            "Введите в формате ЧЧ:ММ (например, 07:30)"
        )
        return

    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await state.clear()
        return

    await state.clear()

    # Создаём фейковый callback для переиспользования логики
    class FakeCallback:
        def __init__(self):
            self.message = message

        async def answer(self, text=None, show_alert=False):
            if text:
                await message.answer(text)

    await _create_habit_event(FakeCallback(), user, habit_type, time_str)


async def _create_habit_event(callback, user, habit_type: str, time_str: str):
    """Создать recurring событие для привычки"""

    if not user.google_refresh_token_encrypted:
        await callback.answer("Google Calendar не подключён", show_alert=True)
        return

    # Загружаем calendar service
    calendar_service = GoogleCalendarService(user.id)
    if not calendar_service.load_credentials(user.google_refresh_token_encrypted):
        await callback.answer("Ошибка подключения к календарю", show_alert=True)
        return

    session = get_session()
    try:
        # Проверяем существующую привычку
        habit = session.query(HabitCalendarEvent).filter(
            HabitCalendarEvent.user_id == user.id,
            HabitCalendarEvent.habit_type == habit_type
        ).first()

        # Создаём событие в Google Calendar
        event_id = calendar_service.create_recurring_event(
            summary=HABIT_NAMES.get(habit_type, "Привычка"),
            start_time=time_str,
            duration_minutes=60,
            description=f"Привычка из Kaizen Bot.\nОтмечай выполнение в вечерней рефлексии!",
            calendar_id=user.google_calendar_id or "primary"
        )

        if not event_id:
            await callback.answer("Ошибка создания события", show_alert=True)
            return

        # Сохраняем или обновляем привычку
        if habit:
            habit.google_event_id = event_id
            habit.event_time = time_str
            habit.is_active = True
        else:
            habit = HabitCalendarEvent(
                user_id=user.id,
                habit_type=habit_type,
                google_event_id=event_id,
                event_time=time_str,
                is_active=True
            )
            session.add(habit)

        session.commit()

        # Успех!
        await callback.message.answer(
            f"✅ *{HABIT_NAMES.get(habit_type)} добавлен в календарь!*\n\n"
            f"⏰ Время: {time_str} (ежедневно)\n\n"
            f"Событие станет зелёным, когда отметишь\n"
            f"выполнение в вечерней рефлексии.",
            parse_mode="Markdown"
        )

        # Показываем обновлённое меню
        status = _get_habit_status(user.id)
        await callback.message.answer(
            "📅 *Привычки в календаре*",
            parse_mode="Markdown",
            reply_markup=get_habit_calendar_keyboard(
                exercise_active=status["exercise"],
                eating_active=status["eating"]
            )
        )

    except Exception as e:
        print(f"Error creating habit event: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)
    finally:
        session.close()
