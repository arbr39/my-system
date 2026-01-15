from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.database.crud import get_user_by_telegram_id, get_today_entry, update_evening_entry, update_habits
from src.keyboards.inline import get_task_completion_keyboard, get_skip_keyboard, get_main_menu

router = Router()


class EveningStates(StatesGroup):
    """Состояния вечерней рефлексии"""
    tasks_check = State()
    insight = State()
    improve = State()
    exercised = State()      # Занимался спортом?
    ate_well = State()       # Питание было в порядке?
    sleep_time = State()     # Во сколько планирует лечь


def get_yes_no_keyboard(prefix: str = "habit") -> InlineKeyboardMarkup:
    """Клавиатура Да/Нет для привычек"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=f"{prefix}_yes"),
        InlineKeyboardButton(text="❌ Нет", callback_data=f"{prefix}_no")
    )
    return builder.as_markup()


# Временное хранение состояния задач
task_states = {}


@router.callback_query(F.data == "evening_start")
async def start_evening(callback: CallbackQuery, state: FSMContext):
    """Начало вечерней рефлексии"""
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Сначала запусти /start")
        return

    entry = get_today_entry(user.id)

    if not entry or not entry.morning_completed:
        await callback.message.edit_text(
            "⚠️ Сначала заполни утренний кайдзен!",
            reply_markup=get_main_menu()
        )
        await callback.answer()
        return

    # Сохраняем данные
    await state.update_data(
        user_id=user.id,
        task_1=entry.task_1,
        task_2=entry.task_2,
        task_3=entry.task_3
    )

    # Инициализируем состояние задач
    task_states[callback.from_user.id] = {
        "t1": entry.task_1_done,
        "t2": entry.task_2_done,
        "t3": entry.task_3_done
    }

    await callback.message.edit_text(
        "🌙 *Вечерняя рефлексия*\n\n"
        "Отметь выполненные задачи:",
        parse_mode="Markdown",
        reply_markup=get_task_completion_keyboard(
            entry.task_1 or "", entry.task_2 or "", entry.task_3 or "",
            entry.task_1_done, entry.task_2_done, entry.task_3_done
        )
    )
    await state.set_state(EveningStates.tasks_check)
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_task:"), EveningStates.tasks_check)
async def toggle_task(callback: CallbackQuery, state: FSMContext):
    """Переключение статуса задачи"""
    task_num = callback.data.split(":")[1]
    user_id = callback.from_user.id

    if user_id not in task_states:
        task_states[user_id] = {"t1": False, "t2": False, "t3": False}

    # Переключаем
    key = f"t{task_num}"
    task_states[user_id][key] = not task_states[user_id][key]

    # Получаем данные
    data = await state.get_data()

    await callback.message.edit_reply_markup(
        reply_markup=get_task_completion_keyboard(
            data.get("task_1", ""), data.get("task_2", ""), data.get("task_3", ""),
            task_states[user_id]["t1"],
            task_states[user_id]["t2"],
            task_states[user_id]["t3"]
        )
    )
    await callback.answer()


@router.callback_query(F.data == "tasks_done", EveningStates.tasks_check)
async def tasks_done(callback: CallbackQuery, state: FSMContext):
    """Задачи отмечены, переходим к инсайту"""
    user_id = callback.from_user.id

    # Сохраняем состояние задач
    ts = task_states.get(user_id, {"t1": False, "t2": False, "t3": False})
    await state.update_data(
        task_1_done=ts["t1"],
        task_2_done=ts["t2"],
        task_3_done=ts["t3"]
    )

    await callback.message.edit_text(
        "💡 *Какой главный инсайт дня?*\n"
        "(Что понял, осознал, чему научился)",
        parse_mode="Markdown",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(EveningStates.insight)
    await callback.answer()


@router.message(EveningStates.insight)
async def process_insight(message: Message, state: FSMContext):
    """Обработка инсайта"""
    await state.update_data(insight=message.text)

    await message.answer(
        "🔧 *Что улучшить завтра?*\n"
        "(Одна вещь, которую сделаешь по-другому)",
        parse_mode="Markdown",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(EveningStates.improve)


@router.message(EveningStates.improve)
async def process_improve(message: Message, state: FSMContext):
    """Обработка улучшения, переход к трекеру привычек"""
    await state.update_data(improve=message.text)

    await message.answer(
        "🏃 *Занимался сегодня спортом?*",
        parse_mode="Markdown",
        reply_markup=get_yes_no_keyboard("exercise")
    )
    await state.set_state(EveningStates.exercised)


async def finish_evening(message: Message, state: FSMContext):
    """Завершение вечерней рефлексии"""
    data = await state.get_data()

    # Сохраняем рефлексию в БД
    update_evening_entry(
        user_id=data.get("user_id"),
        task_1_done=data.get("task_1_done", False),
        task_2_done=data.get("task_2_done", False),
        task_3_done=data.get("task_3_done", False),
        insight=data.get("insight", ""),
        improve=data.get("improve", "")
    )

    # Сохраняем привычки
    update_habits(
        user_id=data.get("user_id"),
        exercised=data.get("exercised"),
        ate_well=data.get("ate_well"),
        sleep_time=data.get("sleep_time", "")
    )

    # Подсчёт выполненных задач
    done_count = sum([
        data.get("task_1_done", False),
        data.get("task_2_done", False),
        data.get("task_3_done", False)
    ])
    total_tasks = sum([
        bool(data.get("task_1")),
        bool(data.get("task_2")),
        bool(data.get("task_3"))
    ])

    # Проверяем статус главной задачи (GTD priority)
    entry = get_today_entry(data.get("user_id"))
    priority_done = False
    priority_text = ""

    if entry and entry.priority_task:
        priority = entry.priority_task
        task_done_map = {
            1: data.get("task_1_done", False),
            2: data.get("task_2_done", False),
            3: data.get("task_3_done", False)
        }
        task_text_map = {
            1: data.get("task_1", ""),
            2: data.get("task_2", ""),
            3: data.get("task_3", "")
        }

        priority_done = task_done_map.get(priority, False)
        priority_text = task_text_map.get(priority, "")

    # === НАГРАДЫ за вечернюю рефлексию ===
    from src.database.crud_rewards import grant_evening_reflection_reward, get_reward_balance_by_telegram_id

    reward_breakdown = grant_evening_reflection_reward(
        user_id=data.get("user_id"),
        daily_entry_id=entry.id if entry else None,
        tasks_done=done_count,
        priority_done=priority_done,
        exercised=data.get("exercised", False),
        ate_well=data.get("ate_well", False)
    )

    # Формируем итоговое сообщение
    summary = "✅ *Вечерняя рефлексия завершена!*\n\n"
    summary += f"📊 Выполнено задач: {done_count}/{total_tasks}\n\n"

    # Статус главной задачи
    if entry and entry.priority_task:
        if priority_done:
            summary += f"⭐ *Главная задача: ВЫПОЛНЕНА!*\n_{priority_text}_\n\n"
        else:
            summary += f"⭐ *Главная задача: не выполнена*\n_{priority_text}_\n\n"

    if data.get("insight"):
        summary += f"💡 *Инсайт:* {data['insight']}\n\n"
    if data.get("improve"):
        summary += f"🔧 *Улучшить завтра:* {data['improve']}\n\n"

    # === Показываем детализацию наград ===
    if reward_breakdown.get("total", 0) > 0:
        summary += "💰 *Заработано сегодня:*\n"

        if reward_breakdown.get("evening"):
            summary += f"• Рефлексия: +{reward_breakdown['evening']}₽\n"
        if reward_breakdown.get("tasks"):
            summary += f"• Задачи ({done_count}): +{reward_breakdown['tasks']}₽\n"
        if reward_breakdown.get("priority"):
            summary += f"• Главная задача: +{reward_breakdown['priority']}₽\n"
        if reward_breakdown.get("exercise"):
            summary += f"• Спорт: +{reward_breakdown['exercise']}₽\n"
        if reward_breakdown.get("eating"):
            summary += f"• Питание: +{reward_breakdown['eating']}₽\n"

        balance = get_reward_balance_by_telegram_id(message.chat.id)
        summary += f"\n📊 *Итого: +{reward_breakdown['total']}₽* | Баланс: {balance}₽\n\n"

    # Привычки
    summary += "*Привычки сегодня:*\n"
    exercise_emoji = "✅" if data.get("exercised") else "❌"
    eating_emoji = "✅" if data.get("ate_well") else "❌"
    summary += f"{exercise_emoji} Спорт\n"
    summary += f"{eating_emoji} Питание\n"
    if data.get("sleep_time"):
        summary += f"🛏️ План лечь: {data['sleep_time']}\n"

    summary += "\n🌙 Отличная работа! Спокойной ночи!"

    await message.answer(summary, parse_mode="Markdown", reply_markup=get_main_menu())

    # Очищаем временные данные
    user_id = message.from_user.id if hasattr(message, 'from_user') else None
    if user_id and user_id in task_states:
        del task_states[user_id]

    await state.clear()


# Обработка трекера привычек
@router.callback_query(F.data.startswith("exercise_"), EveningStates.exercised)
async def process_exercise(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа о спорте"""
    exercised = callback.data == "exercise_yes"
    await state.update_data(exercised=exercised)

    await callback.message.edit_text(
        "🥗 *Питание сегодня было в порядке?*",
        parse_mode="Markdown",
        reply_markup=get_yes_no_keyboard("eating")
    )
    await state.set_state(EveningStates.ate_well)
    await callback.answer()


@router.callback_query(F.data.startswith("eating_"), EveningStates.ate_well)
async def process_eating(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа о питании"""
    ate_well = callback.data == "eating_yes"
    await state.update_data(ate_well=ate_well)

    await callback.message.edit_text(
        "🛏️ *Во сколько планируешь лечь спать?*\n"
        "(Введи время, например: 23:00)",
        parse_mode="Markdown",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(EveningStates.sleep_time)
    await callback.answer()


@router.message(EveningStates.sleep_time)
async def process_sleep_time(message: Message, state: FSMContext):
    """Обработка времени сна и завершение"""
    await state.update_data(sleep_time=message.text.strip())
    await finish_evening(message, state)


# Обработка пропусков
@router.callback_query(F.data == "skip", EveningStates.insight)
async def skip_insight(callback: CallbackQuery, state: FSMContext):
    await state.update_data(insight="")
    await callback.message.edit_text(
        "🔧 *Что улучшить завтра?*",
        parse_mode="Markdown",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(EveningStates.improve)
    await callback.answer()


@router.callback_query(F.data == "skip", EveningStates.improve)
async def skip_improve(callback: CallbackQuery, state: FSMContext):
    await state.update_data(improve="")
    await callback.message.edit_text(
        "🏃 *Занимался сегодня спортом?*",
        parse_mode="Markdown",
        reply_markup=get_yes_no_keyboard("exercise")
    )
    await state.set_state(EveningStates.exercised)
    await callback.answer()


@router.callback_query(F.data == "skip", EveningStates.sleep_time)
async def skip_sleep_time(callback: CallbackQuery, state: FSMContext):
    await state.update_data(sleep_time="")
    await callback.message.edit_text("⏳ Сохраняю...")
    await finish_evening(callback.message, state)
    await callback.answer()
