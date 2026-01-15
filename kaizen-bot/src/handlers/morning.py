from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.database.crud import (
    get_user_by_telegram_id, update_morning_entry, get_or_create_today_entry,
    get_user_goals, update_habits, update_priority_task
)
from src.keyboards.inline import get_skip_keyboard, get_main_menu, get_priority_keyboard

router = Router()


class MorningStates(StatesGroup):
    """Состояния утреннего кайдзена"""
    wake_time = State()      # Во сколько проснулся
    energy_plus = State()
    energy_minus = State()
    task_1 = State()
    task_2 = State()
    task_3 = State()
    priority_task = State()  # Выбор главной задачи (GTD)


@router.callback_query(F.data == "morning_start")
async def start_morning(callback: CallbackQuery, state: FSMContext):
    """Начало утреннего кайдзена"""
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Сначала запусти /start")
        return

    # Сохраняем user_id в состоянии
    await state.update_data(user_id=user.id)

    # Показываем цели пользователя
    goals = get_user_goals(user.id)
    goals_text = ""
    if goals:
        goals_text = "\n*Твои цели:*\n"
        for goal in goals[:3]:
            goals_text += f"🎯 {goal.title}\n"
        goals_text += "\n"

    await callback.message.edit_text(
        f"🌅 *Утренний кайдзен*\n\n"
        f"Давай начнём день правильно!{goals_text}\n"
        f"⏰ *Во сколько ты проснулся сегодня?*\n"
        f"(Введи время, например: 7:30)",
        parse_mode="Markdown",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(MorningStates.wake_time)
    await callback.answer()


@router.message(MorningStates.wake_time)
async def process_wake_time(message: Message, state: FSMContext):
    """Обработка времени подъёма"""
    # TODO: Добавить валидацию формата времени (HH:MM)
    # TODO: Добавить тесты для FSM flows (нужен pytest-aiogram)
    data = await state.get_data()

    # Сохраняем время подъёма
    update_habits(user_id=data["user_id"], wake_time=message.text.strip())
    await state.update_data(wake_time=message.text.strip())

    await message.answer(
        "❓ *Что вчера дало тебе энергию?*\n"
        "(Что вдохновило, порадовало, зарядило)",
        parse_mode="Markdown",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(MorningStates.energy_plus)


@router.message(MorningStates.energy_plus)
async def process_energy_plus(message: Message, state: FSMContext):
    """Обработка: что дало энергию"""
    await state.update_data(energy_plus=message.text)

    await message.answer(
        "❓ *Что вчера забрало энергию?*\n"
        "(Что раздражало, отнимало силы, мешало)",
        parse_mode="Markdown",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(MorningStates.energy_minus)


@router.message(MorningStates.energy_minus)
async def process_energy_minus(message: Message, state: FSMContext):
    """Обработка: что забрало энергию"""
    await state.update_data(energy_minus=message.text)

    await message.answer(
        "📝 *Задача #1 на сегодня*\n"
        "(Самая важная задача дня)",
        parse_mode="Markdown",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(MorningStates.task_1)


@router.message(MorningStates.task_1)
async def process_task_1(message: Message, state: FSMContext):
    """Обработка задачи 1"""
    await state.update_data(task_1=message.text)

    await message.answer(
        "📝 *Задача #2 на сегодня*",
        parse_mode="Markdown",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(MorningStates.task_2)


@router.message(MorningStates.task_2)
async def process_task_2(message: Message, state: FSMContext):
    """Обработка задачи 2"""
    await state.update_data(task_2=message.text)

    await message.answer(
        "📝 *Задача #3 на сегодня*",
        parse_mode="Markdown",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(MorningStates.task_3)


@router.message(MorningStates.task_3)
async def process_task_3(message: Message, state: FSMContext):
    """Обработка задачи 3 -> выбор приоритета"""
    await state.update_data(task_3=message.text)
    data = await state.get_data()

    # Показываем выбор главной задачи
    tasks_text = ""
    if data.get("task_1"):
        tasks_text += f"1️⃣ {data['task_1']}\n"
    if data.get("task_2"):
        tasks_text += f"2️⃣ {data['task_2']}\n"
    if data.get("task_3"):
        tasks_text += f"3️⃣ {data['task_3']}\n"

    if tasks_text:
        await message.answer(
            "⭐ *Какая задача ГЛАВНАЯ на сегодня?*\n\n"
            f"{tasks_text}\n"
            "Её ты делаешь ПЕРВОЙ, пока есть энергия!",
            parse_mode="Markdown",
            reply_markup=get_priority_keyboard(
                data.get("task_1", ""),
                data.get("task_2", ""),
                data.get("task_3", "")
            )
        )
        await state.set_state(MorningStates.priority_task)
    else:
        await finish_morning(message, state)


@router.callback_query(F.data.startswith("priority:"), MorningStates.priority_task)
async def process_priority(callback: CallbackQuery, state: FSMContext):
    """Выбор приоритетной задачи"""
    priority = int(callback.data.split(":")[1])
    await state.update_data(priority_task=priority)
    await callback.message.edit_text("⏳ Сохраняю...")
    await finish_morning(callback.message, state)
    await callback.answer()


async def finish_morning(message: Message, state: FSMContext):
    """Завершение утреннего кайдзена"""
    data = await state.get_data()

    # Сохраняем в БД
    update_morning_entry(
        user_id=data.get("user_id"),
        energy_plus=data.get("energy_plus", ""),
        energy_minus=data.get("energy_minus", ""),
        task_1=data.get("task_1", ""),
        task_2=data.get("task_2", ""),
        task_3=data.get("task_3", "")
    )

    # Сохраняем приоритетную задачу
    priority = data.get("priority_task")
    if priority:
        update_priority_task(data.get("user_id"), priority)

    # === НАГРАДА за утренний кайдзен ===
    from src.database.crud_rewards import grant_morning_kaizen_reward, get_reward_balance_by_telegram_id
    from src.database.crud import get_today_entry

    entry = get_today_entry(data.get("user_id"))
    reward_amount = grant_morning_kaizen_reward(
        user_id=data.get("user_id"),
        daily_entry_id=entry.id if entry else None
    )

    # Формируем итоговое сообщение
    summary = "✅ *Утренний кайдзен завершён!*\n\n"

    if data.get("energy_plus"):
        summary += f"⚡ *Энергия +:* {data['energy_plus']}\n"
    if data.get("energy_minus"):
        summary += f"🔋 *Энергия -:* {data['energy_minus']}\n"

    summary += "\n📋 *Задачи на сегодня:*\n"
    tasks = [data.get("task_1"), data.get("task_2"), data.get("task_3")]
    for i, task in enumerate(tasks, 1):
        if task:
            if priority == i:
                summary += f"⭐ *{task}* ← ГЛАВНАЯ\n"
            else:
                summary += f"⬜ {task}\n"

    # Добавляем информацию о награде
    if reward_amount > 0:
        balance = get_reward_balance_by_telegram_id(message.chat.id)
        summary += f"\n\n💰 *+{reward_amount}₽* за утренний кайдзен!"
        summary += f"\n📊 Баланс: {balance}₽"

    summary += "\n\n🌙 Вечером я напомню подвести итоги!"

    # Синхронизация с Google Calendar
    try:
        user = get_user_by_telegram_id(message.chat.id)
        if user and user.calendar_sync_enabled:
            from src.scheduler.calendar_sync import sync_after_morning_kaizen
            success, sync_msg = await sync_after_morning_kaizen(user)
            if success:
                summary += "\n\n📅 _Задачи добавлены в Google Calendar_"
    except Exception as e:
        print(f"Calendar sync error: {e}")

    await message.answer(summary, parse_mode="Markdown", reply_markup=get_main_menu())
    await state.clear()


# Обработка кнопки "Пропустить"
@router.callback_query(F.data == "skip", MorningStates.wake_time)
async def skip_wake_time(callback: CallbackQuery, state: FSMContext):
    await state.update_data(wake_time="")
    await callback.message.edit_text(
        "❓ *Что вчера дало тебе энергию?*\n"
        "(Что вдохновило, порадовало, зарядило)",
        parse_mode="Markdown",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(MorningStates.energy_plus)
    await callback.answer()


@router.callback_query(F.data == "skip", MorningStates.energy_plus)
async def skip_energy_plus(callback: CallbackQuery, state: FSMContext):
    await state.update_data(energy_plus="")
    await callback.message.edit_text(
        "❓ *Что вчера забрало энергию?*",
        parse_mode="Markdown",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(MorningStates.energy_minus)
    await callback.answer()


@router.callback_query(F.data == "skip", MorningStates.energy_minus)
async def skip_energy_minus(callback: CallbackQuery, state: FSMContext):
    await state.update_data(energy_minus="")
    await callback.message.edit_text(
        "📝 *Задача #1 на сегодня*",
        parse_mode="Markdown",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(MorningStates.task_1)
    await callback.answer()


@router.callback_query(F.data == "skip", MorningStates.task_1)
async def skip_task_1(callback: CallbackQuery, state: FSMContext):
    await state.update_data(task_1="")
    await callback.message.edit_text(
        "📝 *Задача #2 на сегодня*",
        parse_mode="Markdown",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(MorningStates.task_2)
    await callback.answer()


@router.callback_query(F.data == "skip", MorningStates.task_2)
async def skip_task_2(callback: CallbackQuery, state: FSMContext):
    await state.update_data(task_2="")
    await callback.message.edit_text(
        "📝 *Задача #3 на сегодня*",
        parse_mode="Markdown",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(MorningStates.task_3)
    await callback.answer()


@router.callback_query(F.data == "skip", MorningStates.task_3)
async def skip_task_3(callback: CallbackQuery, state: FSMContext):
    await state.update_data(task_3="")
    data = await state.get_data()

    # Показываем выбор главной задачи если есть хоть одна
    tasks_text = ""
    if data.get("task_1"):
        tasks_text += f"1️⃣ {data['task_1']}\n"
    if data.get("task_2"):
        tasks_text += f"2️⃣ {data['task_2']}\n"

    if tasks_text:
        await callback.message.edit_text(
            "⭐ *Какая задача ГЛАВНАЯ на сегодня?*\n\n"
            f"{tasks_text}\n"
            "Её ты делаешь ПЕРВОЙ!",
            parse_mode="Markdown",
            reply_markup=get_priority_keyboard(
                data.get("task_1", ""),
                data.get("task_2", ""),
                ""
            )
        )
        await state.set_state(MorningStates.priority_task)
    else:
        await callback.message.edit_text("⏳ Сохраняю...")
        await finish_morning(callback.message, state)
    await callback.answer()
