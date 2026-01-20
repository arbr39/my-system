"""
Handlers для Quick Action "📅 В календарь".

Обрабатывает добавление inbox items и user tasks в Google Calendar
с выбором времени через quick slots или ручной ввод.
"""

from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.database.models import get_session, InboxItem, UserTask
from src.database.crud import get_user_by_telegram_id, get_inbox_item
from src.database.crud_user_tasks import get_user_task
from src.integrations.google_calendar import GoogleCalendarService
from src.keyboards.inline_calendar import get_time_slots_keyboard
from src.keyboards.inline import get_inbox_item_keyboard
from src.keyboards.inline_user_tasks import get_task_view_keyboard

router = Router()


class CalendarActionStates(StatesGroup):
    """FSM состояния для добавления в календарь"""
    waiting_for_custom_time = State()


# === Inbox to Calendar ===

@router.callback_query(F.data.startswith("inbox_to_calendar:"))
async def inbox_to_calendar_start(callback: CallbackQuery):
    """Начать добавление inbox item в календарь"""
    item_id = int(callback.data.split(":")[1])

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    if not user.google_refresh_token_encrypted:
        await callback.answer("Сначала подключите Google Calendar через /calendar", show_alert=True)
        return

    item = get_inbox_item(item_id)
    if not item:
        await callback.answer("Элемент не найден", show_alert=True)
        return

    await callback.message.edit_text(
        f"📅 *Добавить в календарь*\n\n"
        f"_{item.text[:100]}{'...' if len(item.text) > 100 else ''}_\n\n"
        f"Выберите время:",
        parse_mode="Markdown",
        reply_markup=get_time_slots_keyboard("inbox", item_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("task_to_calendar:"))
async def task_to_calendar_start(callback: CallbackQuery):
    """Начать добавление user task в календарь"""
    task_id = int(callback.data.split(":")[1])

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    if not user.google_refresh_token_encrypted:
        await callback.answer("Сначала подключите Google Calendar через /calendar", show_alert=True)
        return

    task = get_user_task(user.id, task_id)
    if not task:
        await callback.answer("Задача не найдена", show_alert=True)
        return

    await callback.message.edit_text(
        f"📅 *Добавить в календарь*\n\n"
        f"*{task.name}* ({task.reward_amount}₽)\n\n"
        f"Выберите время:",
        parse_mode="Markdown",
        reply_markup=get_time_slots_keyboard("task", task_id)
    )
    await callback.answer()


# === Time slot selection ===

@router.callback_query(F.data.startswith("cal_slot:"))
async def handle_time_slot(callback: CallbackQuery):
    """Обработать выбор quick slot"""
    parts = callback.data.split(":")
    item_type = parts[1]  # "inbox" или "task"
    item_id = int(parts[2])
    day = parts[3]  # "today" или "tomorrow"
    hour = int(parts[4])

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    # Вычисляем datetime
    now = datetime.now()
    if day == "today":
        event_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    else:  # tomorrow
        event_time = (now + timedelta(days=1)).replace(hour=hour, minute=0, second=0, microsecond=0)

    await _create_calendar_event(callback, user, item_type, item_id, event_time)


@router.callback_query(F.data.startswith("cal_custom:"))
async def start_custom_time_input(callback: CallbackQuery, state: FSMContext):
    """Начать ввод произвольного времени"""
    parts = callback.data.split(":")
    item_type = parts[1]
    item_id = int(parts[2])

    await state.update_data(item_type=item_type, item_id=item_id)
    await state.set_state(CalendarActionStates.waiting_for_custom_time)

    await callback.message.edit_text(
        "⏰ *Введите дату и время*\n\n"
        "Формат: `ДД.ММ ЧЧ:ММ`\n"
        "Например: `25.01 14:30` или `завтра 10:00`",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(CalendarActionStates.waiting_for_custom_time)
async def process_custom_time(message: Message, state: FSMContext):
    """Обработать введённое время"""
    data = await state.get_data()
    item_type = data.get("item_type")
    item_id = data.get("item_id")

    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await state.clear()
        return

    # Парсим время
    event_time = _parse_datetime(message.text.strip())
    if not event_time:
        await message.answer(
            "❌ Не удалось распознать дату/время.\n"
            "Используйте формат: `25.01 14:30` или `завтра 10:00`",
            parse_mode="Markdown"
        )
        return

    await state.clear()

    # Создаём фейковый callback для переиспользования логики
    class FakeCallback:
        def __init__(self):
            self.message = message

        async def answer(self, text=None, show_alert=False):
            if text:
                await message.answer(text)

    await _create_calendar_event(FakeCallback(), user, item_type, item_id, event_time)


@router.callback_query(F.data.startswith("cal_cancel:"))
async def cancel_calendar_action(callback: CallbackQuery):
    """Отменить добавление в календарь"""
    parts = callback.data.split(":")
    item_type = parts[1]
    item_id = int(parts[2])

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    if item_type == "inbox":
        item = get_inbox_item(item_id)
        if item:
            await callback.message.edit_text(
                f"📥 *Inbox item*\n\n_{item.text}_",
                parse_mode="Markdown",
                reply_markup=get_inbox_item_keyboard(item_id)
            )
    else:
        task = get_user_task(user.id, item_id)
        if task:
            from src.database.crud_user_tasks import is_task_completed_today
            already_completed = is_task_completed_today(user.id, item_id)
            await callback.message.edit_text(
                f"📋 *{task.name}*\n\n"
                f"💰 Награда: {task.reward_amount}₽\n"
                f"🔄 {'Повторяющаяся' if task.is_recurring else 'Одноразовая'}",
                parse_mode="Markdown",
                reply_markup=get_task_view_keyboard(item_id, already_completed, task.is_recurring)
            )

    await callback.answer()


# === Helper functions ===

def _parse_datetime(text: str) -> datetime | None:
    """Парсить дату/время из текста"""
    text = text.lower().strip()
    now = datetime.now()

    # "завтра 10:00"
    if text.startswith("завтра"):
        time_part = text.replace("завтра", "").strip()
        try:
            hour, minute = map(int, time_part.split(":"))
            return (now + timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        except (ValueError, AttributeError):
            return None

    # "сегодня 14:30"
    if text.startswith("сегодня"):
        time_part = text.replace("сегодня", "").strip()
        try:
            hour, minute = map(int, time_part.split(":"))
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        except (ValueError, AttributeError):
            return None

    # "25.01 14:30"
    try:
        parts = text.split()
        if len(parts) == 2:
            date_part, time_part = parts
            day, month = map(int, date_part.split("."))
            hour, minute = map(int, time_part.split(":"))

            year = now.year
            # Если дата уже прошла в этом году, берём следующий год
            result = datetime(year, month, day, hour, minute)
            if result < now:
                result = datetime(year + 1, month, day, hour, minute)
            return result
    except (ValueError, AttributeError):
        pass

    return None


async def _create_calendar_event(callback, user, item_type: str, item_id: int, event_time: datetime):
    """Создать событие в Google Calendar"""

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
        # Получаем элемент
        if item_type == "inbox":
            item = session.query(InboxItem).filter(InboxItem.id == item_id).first()
            if not item:
                await callback.answer("Элемент не найден", show_alert=True)
                return
            summary = item.text[:100]
            description = f"Из Inbox | {item.text}"
        else:
            item = session.query(UserTask).filter(UserTask.id == item_id).first()
            if not item:
                await callback.answer("Задача не найдена", show_alert=True)
                return
            summary = item.name
            description = f"Задача из Kaizen Bot | Награда: {item.reward_amount}₽"

        # Создаём событие
        event_id = calendar_service.create_event(
            summary=summary,
            start_time=event_time,
            description=description,
            calendar_id=user.google_calendar_id or "primary",
            is_priority=False
        )

        # Сохраняем event_id
        if item_type == "inbox":
            item.google_event_id = event_id
            item.calendar_synced_at = datetime.now()
        else:
            item.google_event_id = event_id
            item.calendar_time = event_time

        session.commit()

        # Успех!
        time_str = event_time.strftime("%d.%m %H:%M")
        await callback.message.answer(
            f"✅ *Добавлено в Google Calendar!*\n\n"
            f"📅 {time_str}\n"
            f"_{summary}_",
            parse_mode="Markdown"
        )

    except Exception as e:
        print(f"Error creating calendar event: {e}")
        await callback.answer("Произошла ошибка при создании события", show_alert=True)
    finally:
        session.close()
