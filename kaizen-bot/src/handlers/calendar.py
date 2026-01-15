"""
Google Calendar интеграция - команды и настройки
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from src.database.crud import (
    get_user_by_telegram_id, get_or_create_user,
    update_user_google_token, disable_calendar_sync
)
from src.integrations.google_calendar import GoogleCalendarService
from src.keyboards.inline import get_main_menu
from src.config import GOOGLE_CLIENT_ID

router = Router()


class CalendarStates(StatesGroup):
    """Состояния OAuth flow"""
    waiting_for_code = State()


def get_calendar_keyboard(is_connected: bool) -> InlineKeyboardMarkup:
    """Клавиатура настроек календаря"""
    builder = InlineKeyboardBuilder()

    if is_connected:
        builder.row(InlineKeyboardButton(
            text="📆 События сегодня",
            callback_data="calendar_today"
        ))
        builder.row(InlineKeyboardButton(
            text="🔄 Синхронизировать",
            callback_data="calendar_sync_now"
        ))
        builder.row(InlineKeyboardButton(
            text="❌ Отключить",
            callback_data="calendar_disconnect"
        ))
    else:
        builder.row(InlineKeyboardButton(
            text="🔗 Подключить Google Calendar",
            callback_data="calendar_connect"
        ))

    builder.row(InlineKeyboardButton(
        text="🔙 Главное меню",
        callback_data="main_menu"
    ))
    return builder.as_markup()


def is_calendar_configured() -> bool:
    """Проверить настроены ли Google OAuth credentials"""
    return bool(GOOGLE_CLIENT_ID)


@router.message(Command("calendar"))
async def cmd_calendar(message: Message):
    """Команда /calendar - настройки интеграции"""
    if not is_calendar_configured():
        await message.answer(
            "📅 *Google Calendar*\n\n"
            "⚠️ Интеграция не настроена.\n\n"
            "Для настройки добавьте в `.env`:\n"
            "• `GOOGLE_CLIENT_ID`\n"
            "• `GOOGLE_CLIENT_SECRET`\n"
            "• `ENCRYPTION_KEY`",
            parse_mode="Markdown"
        )
        return

    user = get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )

    is_connected = bool(user.google_refresh_token_encrypted)
    status = "✅ Подключён" if is_connected else "❌ Не подключён"

    text = f"📅 *Google Calendar*\n\nСтатус: {status}\n\n"

    if is_connected:
        text += (
            "Синхронизируется:\n"
            "• Задачи дня (после утреннего кайдзена)\n"
            "• Главная задача выделена ⭐\n"
            "• Задачи с дедлайном из inbox"
        )
    else:
        text += (
            "Подключи календарь, чтобы:\n"
            "• Видеть задачи в Google Calendar\n"
            "• Получать напоминания\n"
            "• Планировать день визуально"
        )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_calendar_keyboard(is_connected)
    )


@router.callback_query(F.data == "calendar_show")
async def show_calendar_settings(callback: CallbackQuery):
    """Показать настройки календаря (из главного меню)"""
    if not is_calendar_configured():
        await callback.answer("Интеграция не настроена", show_alert=True)
        return

    user = get_user_by_telegram_id(callback.from_user.id)
    is_connected = bool(user and user.google_refresh_token_encrypted)
    status = "✅ Подключён" if is_connected else "❌ Не подключён"

    text = f"📅 *Google Calendar*\n\nСтатус: {status}"

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_calendar_keyboard(is_connected)
    )
    await callback.answer()


@router.callback_query(F.data == "calendar_connect")
async def start_calendar_connect(callback: CallbackQuery, state: FSMContext):
    """Начать OAuth flow"""
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Сначала запусти /start")
        return

    try:
        service = GoogleCalendarService(user.id)
        auth_url, auth_state = service.get_auth_url()
    except ValueError as e:
        await callback.answer(str(e), show_alert=True)
        return

    # Сохраняем state для валидации
    await state.update_data(oauth_state=auth_state)
    await state.set_state(CalendarStates.waiting_for_code)

    await callback.message.edit_text(
        "🔐 *Подключение Google Calendar*\n\n"
        "1️⃣ Перейди по ссылке ниже\n"
        "2️⃣ Войди в Google аккаунт\n"
        "3️⃣ Разреши доступ к календарю\n"
        "4️⃣ Скопируй код и отправь мне\n\n"
        f"🔗 [Авторизация в Google]({auth_url})\n\n"
        "_Код выглядит примерно так: 4/0AfJo..._",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="❌ Отмена", callback_data="calendar_cancel")
        ).as_markup(),
        disable_web_page_preview=True
    )
    await callback.answer()


@router.message(CalendarStates.waiting_for_code)
async def process_oauth_code(message: Message, state: FSMContext):
    """Обработка OAuth code от пользователя"""
    code = message.text.strip()
    data = await state.get_data()
    oauth_state = data.get("oauth_state")

    user = get_user_by_telegram_id(message.from_user.id)
    service = GoogleCalendarService(user.id)

    try:
        encrypted_token = service.exchange_code(code, oauth_state)
        update_user_google_token(message.from_user.id, encrypted_token)

        await state.clear()
        await message.answer(
            "✅ *Google Calendar подключён!*\n\n"
            "Теперь твои задачи будут синхронизироваться:\n"
            "• После утреннего кайдзена — задачи дня\n"
            "• Главная задача выделена ⭐\n\n"
            "Используй /calendar для управления.",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
    except Exception as e:
        error_msg = str(e)
        if "invalid_grant" in error_msg.lower():
            error_msg = "Код устарел или уже использован"

        await message.answer(
            f"❌ Ошибка авторизации: {error_msg}\n\n"
            "Попробуй ещё раз через /calendar",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
        await state.clear()


@router.callback_query(F.data == "calendar_cancel")
async def cancel_calendar_connect(callback: CallbackQuery, state: FSMContext):
    """Отмена OAuth flow"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Подключение отменено.",
        reply_markup=get_main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "calendar_disconnect")
async def disconnect_calendar(callback: CallbackQuery):
    """Отключить календарь"""
    disable_calendar_sync(callback.from_user.id)

    await callback.message.edit_text(
        "✅ Google Calendar отключён.\n\n"
        "Существующие события в календаре сохранятся.",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )
    await callback.answer("Отключено")


@router.callback_query(F.data == "calendar_today")
async def show_today_events(callback: CallbackQuery):
    """Показать события на сегодня"""
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user or not user.google_refresh_token_encrypted:
        await callback.answer("Календарь не подключён")
        return

    service = GoogleCalendarService(user.id)
    if not service.load_credentials(user.google_refresh_token_encrypted):
        await callback.answer("Ошибка авторизации. Переподключи календарь.", show_alert=True)
        return

    events = service.get_today_events()

    if not events:
        text = "📆 *События на сегодня*\n\nНет запланированных событий."
    else:
        text = "📆 *События на сегодня*\n\n"
        for event in events[:10]:
            start = event.get('start', {})
            time_str = ""
            if 'dateTime' in start:
                dt = start['dateTime']
                # Парсим время из ISO формата
                time_str = dt[11:16] + " "
            summary = event.get('summary', 'Без названия')
            text += f"• {time_str}{summary}\n"

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_calendar_keyboard(True)
    )
    await callback.answer()


@router.callback_query(F.data == "calendar_sync_now")
async def sync_calendar_now(callback: CallbackQuery):
    """Ручная синхронизация"""
    await callback.answer("Синхронизация...")

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user or not user.google_refresh_token_encrypted:
        await callback.message.edit_text(
            "❌ Календарь не подключён",
            reply_markup=get_main_menu()
        )
        return

    try:
        from src.scheduler.calendar_sync import sync_user_tasks_to_calendar
        success, message = await sync_user_tasks_to_calendar(user)

        if success:
            await callback.message.edit_text(
                f"✅ *Синхронизация завершена*\n\n{message}",
                parse_mode="Markdown",
                reply_markup=get_calendar_keyboard(True)
            )
        else:
            await callback.message.edit_text(
                f"❌ *Ошибка синхронизации*\n\n{message}",
                parse_mode="Markdown",
                reply_markup=get_calendar_keyboard(True)
            )
    except ImportError:
        await callback.message.edit_text(
            "⚠️ Модуль синхронизации недоступен",
            reply_markup=get_calendar_keyboard(True)
        )
