"""
Handler для важных дат и напоминаний

Функционал:
- Просмотр списка дат
- Добавление новых дат (FSM)
- Редактирование/удаление
- Ближайшие события
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.database.crud import get_user_by_telegram_id
from src.database.crud_dates import (
    get_user_dates, get_important_date, create_important_date,
    update_important_date, delete_important_date,
    get_upcoming_dates, init_family_birthdays
)
from src.keyboards.inline_dates import (
    get_dates_main_menu, get_dates_list_keyboard,
    get_date_view_keyboard, get_date_type_keyboard,
    get_month_keyboard, get_day_keyboard,
    get_cancel_keyboard, get_confirm_delete_keyboard
)
from src.keyboards.inline import get_main_menu

router = Router()


class DateStates(StatesGroup):
    """Состояния добавления даты"""
    adding_name = State()
    adding_type = State()
    adding_month = State()
    adding_day = State()


# ============ КОМАНДЫ ============

@router.message(Command("dates"))
async def cmd_dates(message: Message, state: FSMContext):
    """Команда /dates - показать важные даты"""
    await state.clear()

    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Сначала используй /start")
        return

    # Инициализация семейных дат при первом запуске
    init_family_birthdays(user.id)

    upcoming = get_upcoming_dates(user.id, days=30)

    text = "📅 *Важные даты*\n\n"

    if upcoming:
        text += "🔜 *Ближайшие события:*\n"
        month_names = ["", "янв", "фев", "мар", "апр", "мая",
                       "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
        for d in upcoming[:5]:
            emoji = "🎂" if d.date_type == "birthday" else "📌"
            text += f"{emoji} {d.name} — {d.day} {month_names[d.month]}\n"
    else:
        text += "_Нет ближайших событий_"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_dates_main_menu()
    )


@router.callback_query(F.data == "dates_show")
async def show_dates_menu(callback: CallbackQuery, state: FSMContext):
    """Показать меню дат"""
    await state.clear()

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка")
        return

    # Инициализация семейных дат
    init_family_birthdays(user.id)

    upcoming = get_upcoming_dates(user.id, days=30)

    text = "📅 *Важные даты*\n\n"

    if upcoming:
        text += "🔜 *Ближайшие события:*\n"
        month_names = ["", "янв", "фев", "мар", "апр", "мая",
                       "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
        for d in upcoming[:5]:
            emoji = "🎂" if d.date_type == "birthday" else "📌"
            text += f"{emoji} {d.name} — {d.day} {month_names[d.month]}\n"
    else:
        text += "_Нет ближайших событий_"

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_dates_main_menu()
    )
    await callback.answer()


# ============ СПИСОК ДАТА ============

@router.callback_query(F.data == "dates_list")
async def show_dates_list(callback: CallbackQuery):
    """Показать полный список дат"""
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка")
        return

    dates = get_user_dates(user.id)

    if dates:
        text = "📋 *Все важные даты:*\n\n"
        month_names = ["", "янв", "фев", "мар", "апр", "мая",
                       "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
        for d in dates:
            emoji = "🎂" if d.date_type == "birthday" else "📌"
            text += f"{emoji} {d.name} — {d.day} {month_names[d.month]}\n"
    else:
        text = "📋 *Все важные даты*\n\n_Список пуст_"

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_dates_list_keyboard(dates)
    )
    await callback.answer()


# ============ ПРОСМОТР ДАТЫ ============

@router.callback_query(F.data.startswith("date_view:"))
async def view_date(callback: CallbackQuery):
    """Просмотр конкретной даты"""
    date_id = int(callback.data.split(":")[1])
    d = get_important_date(date_id)

    if not d:
        await callback.answer("Дата не найдена")
        return

    month_names = ["", "января", "февраля", "марта", "апреля", "мая",
                   "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    type_names = {
        "birthday": "🎂 День рождения",
        "anniversary": "💍 Годовщина",
        "custom": "📌 Другое"
    }

    text = (
        f"📅 *{d.name}*\n\n"
        f"📆 Дата: {d.day} {month_names[d.month]}\n"
        f"🏷 Тип: {type_names.get(d.date_type, d.date_type)}\n"
    )

    if d.description:
        text += f"📝 {d.description}\n"

    text += "\n⏰ Напоминание: "
    parts = []
    if d.remind_days_before > 0:
        parts.append(f"за {d.remind_days_before} д.")
    if d.remind_on_day:
        parts.append("в сам день")
    text += " + ".join(parts) if parts else "выключено"

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_date_view_keyboard(date_id)
    )
    await callback.answer()


# ============ ДОБАВЛЕНИЕ ДАТЫ ============

@router.callback_query(F.data == "date_add")
async def start_add_date(callback: CallbackQuery, state: FSMContext):
    """Начать добавление даты"""
    await state.set_state(DateStates.adding_name)

    await callback.message.edit_text(
        "➕ *Добавление даты*\n\n"
        "Введи название:\n"
        "_Например: Мама, Папа, День свадьбы_",
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(DateStates.adding_name)
async def process_date_name(message: Message, state: FSMContext):
    """Обработка названия"""
    name = message.text.strip()[:100]
    await state.update_data(name=name)
    await state.set_state(DateStates.adding_type)

    await message.answer(
        f"✅ Название: *{name}*\n\n"
        "Выбери тип события:",
        parse_mode="Markdown",
        reply_markup=get_date_type_keyboard()
    )


@router.callback_query(F.data.startswith("date_type:"), DateStates.adding_type)
async def process_date_type(callback: CallbackQuery, state: FSMContext):
    """Обработка типа даты"""
    date_type = callback.data.split(":")[1]
    await state.update_data(date_type=date_type)
    await state.set_state(DateStates.adding_month)

    await callback.message.edit_text(
        "📅 Выбери месяц:",
        parse_mode="Markdown",
        reply_markup=get_month_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("date_month:"), DateStates.adding_month)
async def process_date_month(callback: CallbackQuery, state: FSMContext):
    """Обработка месяца"""
    month = int(callback.data.split(":")[1])
    await state.update_data(month=month)
    await state.set_state(DateStates.adding_day)

    month_names = ["", "января", "февраля", "марта", "апреля", "мая",
                   "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]

    await callback.message.edit_text(
        f"📅 Месяц: {month_names[month]}\n\n"
        "Выбери день:",
        parse_mode="Markdown",
        reply_markup=get_day_keyboard(month)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("date_day:"), DateStates.adding_day)
async def process_date_day(callback: CallbackQuery, state: FSMContext):
    """Обработка дня и сохранение"""
    day = int(callback.data.split(":")[1])
    data = await state.get_data()

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка")
        return

    # Сохраняем
    create_important_date(
        user_id=user.id,
        name=data["name"],
        day=day,
        month=data["month"],
        date_type=data["date_type"]
    )

    await state.clear()

    month_names = ["", "января", "февраля", "марта", "апреля", "мая",
                   "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]

    await callback.message.edit_text(
        f"✅ *Дата добавлена!*\n\n"
        f"📅 {data['name']} — {day} {month_names[data['month']]}",
        parse_mode="Markdown",
        reply_markup=get_dates_main_menu()
    )
    await callback.answer()


# ============ УДАЛЕНИЕ ============

@router.callback_query(F.data.startswith("date_delete:"))
async def confirm_delete_date(callback: CallbackQuery):
    """Подтверждение удаления"""
    date_id = int(callback.data.split(":")[1])
    d = get_important_date(date_id)

    if not d:
        await callback.answer("Дата не найдена")
        return

    await callback.message.edit_text(
        f"🗑 *Удалить дату?*\n\n"
        f"📅 {d.name}",
        parse_mode="Markdown",
        reply_markup=get_confirm_delete_keyboard(date_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("date_delete_confirm:"))
async def execute_delete_date(callback: CallbackQuery):
    """Выполнить удаление"""
    date_id = int(callback.data.split(":")[1])

    success = delete_important_date(date_id)

    if success:
        await callback.answer("✅ Удалено")
    else:
        await callback.answer("❌ Ошибка")

    # Возврат к списку
    user = get_user_by_telegram_id(callback.from_user.id)
    dates = get_user_dates(user.id)

    if dates:
        text = "📋 *Все важные даты:*"
    else:
        text = "📋 *Все важные даты*\n\n_Список пуст_"

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_dates_list_keyboard(dates)
    )


# ============ РЕДАКТИРОВАНИЕ ============

@router.callback_query(F.data.startswith("date_edit:"))
async def edit_date(callback: CallbackQuery):
    """Редактирование даты (пока упрощённо - показываем info)"""
    date_id = int(callback.data.split(":")[1])
    d = get_important_date(date_id)

    if not d:
        await callback.answer("Дата не найдена")
        return

    # Пока просто показываем, что редактирование доступно через удаление + создание
    await callback.answer(
        "Для изменения удали и создай заново",
        show_alert=True
    )


# ============ ОТМЕНА ============

@router.callback_query(F.data == "date_cancel")
async def cancel_date_action(callback: CallbackQuery, state: FSMContext):
    """Отмена действия"""
    await state.clear()

    user = get_user_by_telegram_id(callback.from_user.id)
    upcoming = get_upcoming_dates(user.id, days=30)

    text = "📅 *Важные даты*\n\n"
    if upcoming:
        text += "🔜 *Ближайшие события:*\n"
        month_names = ["", "янв", "фев", "мар", "апр", "мая",
                       "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
        for d in upcoming[:5]:
            emoji = "🎂" if d.date_type == "birthday" else "📌"
            text += f"{emoji} {d.name} — {d.day} {month_names[d.month]}\n"

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_dates_main_menu()
    )
    await callback.answer()
