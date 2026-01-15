"""
GTD Inbox Handler - быстрый сбор и обработка задач

Любой текст без команды автоматически попадает в inbox.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.database.crud import (
    get_or_create_user, get_user_inbox, get_inbox_item, create_inbox_item,
    update_inbox_item, delete_inbox_item, move_inbox_to_someday,
    get_inbox_by_context, get_inbox_count
)
from src.keyboards.inline import (
    get_inbox_keyboard, get_inbox_empty_keyboard, get_inbox_item_keyboard,
    get_two_minute_keyboard, get_energy_keyboard, get_time_estimate_keyboard,
    get_inbox_filter_keyboard, get_filter_energy_keyboard, get_filter_time_keyboard,
    get_inbox_done_keyboard, get_main_menu
)

router = Router()


class InboxStates(StatesGroup):
    """Состояния обработки inbox"""
    processing = State()
    two_minute_check = State()
    adding_energy = State()
    adding_time = State()


# ============ Команда /inbox ============

@router.message(Command("inbox"))
async def cmd_inbox(message: Message):
    """Показать inbox"""
    user = get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    await show_inbox_list(message, user.id)


@router.callback_query(F.data == "inbox_show")
async def callback_inbox_show(callback: CallbackQuery, state: FSMContext):
    """Показать inbox (callback)"""
    await state.clear()
    user = get_or_create_user(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.first_name
    )
    items = get_user_inbox(user.id)

    if not items:
        await callback.message.edit_text(
            "📥 *Inbox пуст!*\n\n"
            "Отправь мне любой текст, и он автоматически попадёт сюда.",
            parse_mode="Markdown",
            reply_markup=get_inbox_empty_keyboard()
        )
    else:
        await callback.message.edit_text(
            f"📥 *Inbox* ({len(items)} задач)\n\n"
            "Выбери задачу для обработки:",
            parse_mode="Markdown",
            reply_markup=get_inbox_keyboard(items)
        )
    await callback.answer()


async def show_inbox_list(message: Message, user_id: int, page: int = 0):
    """Показать список inbox"""
    items = get_user_inbox(user_id)

    if not items:
        await message.answer(
            "📥 *Inbox пуст!*\n\n"
            "Отправь мне любой текст, и он автоматически попадёт сюда.",
            parse_mode="Markdown",
            reply_markup=get_inbox_empty_keyboard()
        )
    else:
        await message.answer(
            f"📥 *Inbox* ({len(items)} задач)\n\n"
            "Выбери задачу для обработки:",
            parse_mode="Markdown",
            reply_markup=get_inbox_keyboard(items, page)
        )


# ============ Пагинация ============

@router.callback_query(F.data.startswith("inbox_page:"))
async def inbox_pagination(callback: CallbackQuery):
    """Пагинация inbox"""
    page = int(callback.data.split(":")[1])
    user = get_or_create_user(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.first_name
    )
    items = get_user_inbox(user.id)

    await callback.message.edit_text(
        f"📥 *Inbox* ({len(items)} задач)\n\n"
        "Выбери задачу для обработки:",
        parse_mode="Markdown",
        reply_markup=get_inbox_keyboard(items, page)
    )
    await callback.answer()


# ============ Просмотр элемента ============

@router.callback_query(F.data.startswith("inbox_item:"))
async def show_inbox_item(callback: CallbackQuery):
    """Показать элемент inbox"""
    item_id = int(callback.data.split(":")[1])
    item = get_inbox_item(item_id)

    if not item:
        await callback.answer("Задача не найдена", show_alert=True)
        return

    # Контексты
    context_text = ""
    if item.energy_level:
        energy_map = {"high": "🔋🔋🔋", "medium": "🔋🔋", "low": "🔋"}
        context_text += f"\nЭнергия: {energy_map.get(item.energy_level, item.energy_level)}"
    if item.time_estimate:
        context_text += f"\nВремя: {item.time_estimate}"

    await callback.message.edit_text(
        f"📥 *Задача из Inbox*\n\n"
        f"_{item.text}_"
        f"{context_text}\n\n"
        f"Что делаем?",
        parse_mode="Markdown",
        reply_markup=get_inbox_item_keyboard(item.id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("inbox_quick_done:"))
async def quick_done_inbox_item(callback: CallbackQuery, state: FSMContext):
    """Быстрое выполнение задачи с начислением награды"""
    from src.database.crud_rewards import grant_inbox_task_reward, get_reward_balance
    from src.database.crud import get_user_by_telegram_id

    item_id = int(callback.data.split(":")[1])
    item = get_inbox_item(item_id)

    if not item:
        await callback.answer("Задача не найдена", show_alert=True)
        return

    # Защита от двойного начисления
    if item.status == "processed":
        await callback.answer("Задача уже выполнена!", show_alert=True)
        return

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка: пользователь не найден", show_alert=True)
        return

    # Начислить награду
    reward = grant_inbox_task_reward(
        user_id=user.id,
        inbox_item_id=item.id,
        time_estimate=item.time_estimate,
        energy_level=item.energy_level
    )

    # Пометить как processed
    update_inbox_item(item_id, status="processed")

    # Баланс
    balance = get_reward_balance(user.id)

    # Messaging (анти-кортизол: празднуем!)
    text = "✅ *Отлично! Задача выполнена!*\n\n"

    if reward["description"] != "Inbox задача выполнена":
        text += f"_{reward['description']}_\n"

    text += f"💰 Заработано: *{reward['total']}₽*\n\n"
    text += f"📊 Баланс: {balance}₽"

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )
    await callback.answer()


# ============ Обработка элемента ============

@router.callback_query(F.data.startswith("inbox_process:"))
async def process_inbox_item(callback: CallbackQuery, state: FSMContext):
    """Начать обработку элемента - правило 2 минут"""
    item_id = int(callback.data.split(":")[1])
    item = get_inbox_item(item_id)

    if not item:
        await callback.answer("Задача не найдена", show_alert=True)
        return

    await state.update_data(processing_item_id=item_id)
    await state.set_state(InboxStates.two_minute_check)

    await callback.message.edit_text(
        f"⚡ *Правило 2 минут*\n\n"
        f"Задача: _{item.text}_\n\n"
        f"Это займёт меньше 2 минут?",
        parse_mode="Markdown",
        reply_markup=get_two_minute_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "inbox_2min_yes", InboxStates.two_minute_check)
async def two_minute_yes(callback: CallbackQuery, state: FSMContext):
    """Задача < 2 минут - предложить сделать сейчас"""
    data = await state.get_data()
    item_id = data.get("processing_item_id")
    item = get_inbox_item(item_id)

    await callback.message.edit_text(
        f"⚡ *Сделай это СЕЙЧАС!*\n\n"
        f"_{item.text}_\n\n"
        f"Когда закончишь - нажми кнопку ниже.",
        parse_mode="Markdown",
        reply_markup=get_inbox_done_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "inbox_mark_done")
async def mark_inbox_done(callback: CallbackQuery, state: FSMContext):
    """Отметить задачу как выполненную (после правила 2 минут) + награда"""
    from src.database.crud_rewards import grant_inbox_task_reward, get_reward_balance
    from src.database.crud import get_user_by_telegram_id

    data = await state.get_data()
    item_id = data.get("processing_item_id")

    if item_id:
        item = get_inbox_item(item_id)
        user = get_user_by_telegram_id(callback.from_user.id)

        if item and user and item.status != "processed":
            # Начислить награду
            reward = grant_inbox_task_reward(
                user_id=user.id,
                inbox_item_id=item.id,
                time_estimate=item.time_estimate,
                energy_level=item.energy_level
            )

            # Обновить статус
            update_inbox_item(item_id, status="processed")

            # Баланс
            balance = get_reward_balance(user.id)

            # Messaging с наградой
            text = "✅ *Отлично! Задача выполнена и удалена из Inbox.*\n\n"
            if reward["description"] != "Inbox задача выполнена":
                text += f"_{reward['description']}_\n"
            text += f"💰 Заработано: *{reward['total']}₽*\n\n"
            text += f"📊 Баланс: {balance}₽"
        else:
            # Fallback
            if item:
                update_inbox_item(item_id, status="processed")
            text = "✅ *Отлично!* Задача выполнена и удалена из Inbox."
    else:
        text = "✅ *Отлично!* Задача выполнена и удалена из Inbox."

    await state.clear()
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "inbox_2min_no", InboxStates.two_minute_check)
async def two_minute_no(callback: CallbackQuery, state: FSMContext):
    """Задача > 2 минут - добавить контекст"""
    await state.set_state(InboxStates.adding_energy)

    await callback.message.edit_text(
        "🔋 *Сколько энергии нужно?*\n\n"
        "Выбери уровень энергии для этой задачи:",
        parse_mode="Markdown",
        reply_markup=get_energy_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("inbox_energy:"), InboxStates.adding_energy)
async def set_energy_level(callback: CallbackQuery, state: FSMContext):
    """Установить уровень энергии"""
    energy = callback.data.split(":")[1]
    data = await state.get_data()
    item_id = data.get("processing_item_id")

    if energy != "skip" and item_id:
        update_inbox_item(item_id, energy_level=energy)

    await state.set_state(InboxStates.adding_time)

    await callback.message.edit_text(
        "⏱ *Сколько времени займёт?*\n\n"
        "Выбери примерную оценку:",
        parse_mode="Markdown",
        reply_markup=get_time_estimate_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("inbox_time:"), InboxStates.adding_time)
async def set_time_estimate(callback: CallbackQuery, state: FSMContext):
    """Установить оценку времени"""
    time_est = callback.data.split(":")[1]
    data = await state.get_data()
    item_id = data.get("processing_item_id")

    if time_est != "skip" and item_id:
        update_inbox_item(item_id, time_estimate=time_est)

    await state.clear()

    await callback.message.edit_text(
        "✅ *Задача обработана!*\n\n"
        "Контексты добавлены. Задача осталась в Inbox для выполнения.",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )
    await callback.answer()


# ============ Удаление ============

@router.callback_query(F.data.startswith("inbox_delete:"))
async def delete_item(callback: CallbackQuery, state: FSMContext):
    """Удалить элемент из inbox"""
    await state.clear()
    item_id = int(callback.data.split(":")[1])
    delete_inbox_item(item_id)

    await callback.message.edit_text(
        "🗑 *Удалено!*",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )
    await callback.answer()


# ============ Переместить в Someday ============

@router.callback_query(F.data.startswith("inbox_someday:"))
async def move_to_someday(callback: CallbackQuery, state: FSMContext):
    """Переместить в 'когда-нибудь'"""
    await state.clear()
    item_id = int(callback.data.split(":")[1])
    move_inbox_to_someday(item_id)

    await callback.message.edit_text(
        "📦 *Перемещено в 'Когда-нибудь'!*\n\n"
        "Вернёшься к этому позже.",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )
    await callback.answer()


# ============ Фильтрация ============

@router.callback_query(F.data == "inbox_filter")
async def show_filter_menu(callback: CallbackQuery):
    """Меню фильтрации"""
    await callback.message.edit_text(
        "🔍 *Фильтрация Inbox*\n\n"
        "Выбери критерий:",
        parse_mode="Markdown",
        reply_markup=get_inbox_filter_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "inbox_filter_energy")
async def filter_energy_menu(callback: CallbackQuery):
    """Меню фильтра по энергии"""
    await callback.message.edit_text(
        "🔋 *Фильтр по энергии*\n\n"
        "Покажу задачи с выбранным уровнем:",
        parse_mode="Markdown",
        reply_markup=get_filter_energy_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "inbox_filter_time")
async def filter_time_menu(callback: CallbackQuery):
    """Меню фильтра по времени"""
    await callback.message.edit_text(
        "⏱ *Фильтр по времени*\n\n"
        "Покажу задачи с выбранной оценкой:",
        parse_mode="Markdown",
        reply_markup=get_filter_time_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("inbox_fe:"))
async def filter_by_energy(callback: CallbackQuery):
    """Фильтр по энергии"""
    energy = callback.data.split(":")[1]
    user = get_or_create_user(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.first_name
    )
    items = get_inbox_by_context(user.id, energy_level=energy)

    energy_map = {"high": "🔋🔋🔋 Высокая", "medium": "🔋🔋 Средняя", "low": "🔋 Низкая"}

    if not items:
        await callback.message.edit_text(
            f"📥 *Inbox* - {energy_map.get(energy, energy)}\n\n"
            "Нет задач с таким уровнем энергии.",
            parse_mode="Markdown",
            reply_markup=get_inbox_filter_keyboard()
        )
    else:
        await callback.message.edit_text(
            f"📥 *Inbox* - {energy_map.get(energy, energy)} ({len(items)})\n\n"
            "Выбери задачу:",
            parse_mode="Markdown",
            reply_markup=get_inbox_keyboard(items)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("inbox_ft:"))
async def filter_by_time(callback: CallbackQuery):
    """Фильтр по времени"""
    time_est = callback.data.split(":")[1]
    user = get_or_create_user(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.first_name
    )
    items = get_inbox_by_context(user.id, time_estimate=time_est)

    if not items:
        await callback.message.edit_text(
            f"📥 *Inbox* - {time_est}\n\n"
            "Нет задач с такой оценкой времени.",
            parse_mode="Markdown",
            reply_markup=get_inbox_filter_keyboard()
        )
    else:
        await callback.message.edit_text(
            f"📥 *Inbox* - {time_est} ({len(items)})\n\n"
            "Выбери задачу:",
            parse_mode="Markdown",
            reply_markup=get_inbox_keyboard(items)
        )
    await callback.answer()


# ============ Перехват текста - добавление в inbox ============
# ВАЖНО: Этот handler должен быть в самом конце и регистрироваться последним!

@router.message(F.text, StateFilter(None))
async def capture_to_inbox(message: Message, state: FSMContext):
    """Любой текст без команды -> в inbox (только когда нет активного FSM состояния)"""
    # Проверяем что не команда
    if message.text.startswith('/'):
        return

    # Добавляем в inbox
    user = get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )

    create_inbox_item(user.id, message.text)
    count = get_inbox_count(user.id)

    await message.answer(
        f"📥 *Добавлено в Inbox!*\n\n"
        f"_{message.text}_\n\n"
        f"Всего в inbox: {count}",
        parse_mode="Markdown"
    )
