"""
Handler для пользовательских задач с наградами (@whysasha методика)

Пользователь создаёт задачи (например, "Тренировка в зале") с произвольной наградой.
При выполнении задачи начисляется награда в фонд наград.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.database.crud import get_user_by_telegram_id, get_unified_tasks
from src.database.crud_rewards import add_reward, get_reward_balance
from src.database.models import get_session, DailyEntry
from src.database.crud_user_tasks import (
    add_user_task,
    get_user_tasks,
    get_user_task,
    update_user_task,
    delete_user_task,
    complete_user_task,
    get_task_completions_today,
    get_task_history,
    get_user_stats_today
)
from src.keyboards.inline_user_tasks import (
    get_tasks_main_menu,
    get_task_view_keyboard,
    get_task_type_keyboard,
    get_task_category_keyboard,
    get_task_delete_confirm_keyboard,
    get_cancel_keyboard,
    get_task_history_keyboard
)
from src.keyboards.inline import get_main_menu


def _get_tasks_keyboard_data(user_id: int):
    """
    Вспомогательная функция для получения данных для клавиатуры задач.
    Возвращает tuple: (tasks, completions_today, stats_today, inbox_tasks, daily_entry)
    """
    unified = get_unified_tasks(user_id, filter_type="all")
    tasks = unified["user_tasks"]
    inbox_tasks = unified["inbox_tasks"]
    daily_entry = unified["daily_entry"]

    stats_today = get_user_stats_today(user_id)

    completions_today = {}
    for task in tasks:
        count = get_task_completions_today(user_id, task.id)
        completions_today[task.id] = count

    return tasks, completions_today, stats_today, inbox_tasks, daily_entry

router = Router()


class UserTaskStates(StatesGroup):
    """Состояния для управления задачами"""
    adding_name = State()
    adding_reward = State()
    adding_type = State()
    adding_category = State()
    editing_name = State()
    editing_reward = State()


# ============ MAIN MENU ============

@router.message(Command("tasks"))
async def cmd_tasks(message: Message):
    """Команда /tasks — показать unified список задач"""
    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Сначала используй /start")
        return

    # Получить unified данные
    unified = get_unified_tasks(user.id, filter_type="all")
    tasks = unified["user_tasks"]
    inbox_tasks = unified["inbox_tasks"]
    daily_entry = unified["daily_entry"]

    stats_today = get_user_stats_today(user.id)

    # Подсчитать выполнения за сегодня
    completions_today = {}
    for task in tasks:
        count = get_task_completions_today(user.id, task.id)
        completions_today[task.id] = count

    text = "📋 *Мои задачи*\n\n"

    # Подсчитать задачи дня
    daily_count = 0
    daily_done = 0
    if daily_entry:
        for i in range(1, 4):
            if getattr(daily_entry, f"task_{i}"):
                daily_count += 1
                if getattr(daily_entry, f"task_{i}_done"):
                    daily_done += 1

    total_count = len(tasks) + len(inbox_tasks) + daily_count

    if total_count > 0:
        if daily_count > 0:
            text += f"📅 Задачи дня: {daily_done}/{daily_count}\n"
        if tasks:
            text += f"⭕ Мои задачи: {len(tasks)}\n"
        if inbox_tasks:
            text += f"📥 Inbox: {len(inbox_tasks)}\n"
        text += "\n_Нажми на задачу, чтобы отметить выполнение_"
    else:
        text += "Список пуст!\n\n"
        text += "_Заполни утренний кайдзен или добавь задачи_"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_tasks_main_menu(
            tasks,
            completions_today,
            stats_today,
            inbox_tasks=inbox_tasks,
            daily_entry=daily_entry,
            filter_type="all"
        )
    )


@router.callback_query(F.data == "tasks_show")
async def show_tasks(callback: CallbackQuery, state: FSMContext):
    """Главное меню задач (unified)"""
    await state.clear()

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка: пользователь не найден")
        return

    # Unified данные
    unified = get_unified_tasks(user.id, filter_type="all")
    tasks = unified["user_tasks"]
    inbox_tasks = unified["inbox_tasks"]
    daily_entry = unified["daily_entry"]

    stats_today = get_user_stats_today(user.id)

    completions_today = {}
    for task in tasks:
        count = get_task_completions_today(user.id, task.id)
        completions_today[task.id] = count

    text = "📋 *Мои задачи*\n\n"

    # Подсчитать задачи дня
    daily_count = 0
    daily_done = 0
    if daily_entry:
        for i in range(1, 4):
            if getattr(daily_entry, f"task_{i}"):
                daily_count += 1
                if getattr(daily_entry, f"task_{i}_done"):
                    daily_done += 1

    total_count = len(tasks) + len(inbox_tasks) + daily_count

    if total_count > 0:
        if daily_count > 0:
            text += f"📅 Задачи дня: {daily_done}/{daily_count}\n"
        if tasks:
            text += f"⭕ Мои задачи: {len(tasks)}\n"
        if inbox_tasks:
            text += f"📥 Inbox: {len(inbox_tasks)}\n"
        text += "\n_Нажми на задачу, чтобы отметить выполнение_"
    else:
        text += "Список пуст!"

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_tasks_main_menu(
            tasks,
            completions_today,
            stats_today,
            inbox_tasks=inbox_tasks,
            daily_entry=daily_entry,
            filter_type="all"
        )
    )
    await callback.answer()


@router.callback_query(F.data == "tasks_empty")
async def tasks_empty_hint(callback: CallbackQuery):
    """Подсказка при пустом списке"""
    await callback.answer(
        "Добавь задачи!\nПример: Тренировка в зале = 50₽",
        show_alert=True
    )


@router.callback_query(F.data == "tasks_stats_info")
async def tasks_stats_info(callback: CallbackQuery):
    """Информация о статистике за день"""
    await callback.answer(
        "Статистика выполненных задач за сегодня",
        show_alert=False
    )


@router.callback_query(F.data.startswith("tasks_filter:"))
async def filter_tasks(callback: CallbackQuery):
    """Фильтр задач: all / user_tasks / inbox / daily"""
    filter_type = callback.data.split(":")[1]

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка")
        return

    # Получить unified данные с фильтром
    unified = get_unified_tasks(user.id, filter_type=filter_type)
    tasks = unified["user_tasks"]
    inbox_tasks = unified["inbox_tasks"]
    daily_entry = unified["daily_entry"]

    stats_today = get_user_stats_today(user.id)

    completions_today = {}
    for task in tasks:
        count = get_task_completions_today(user.id, task.id)
        completions_today[task.id] = count

    text = "📋 *Мои задачи*\n\n"

    if filter_type == "daily":
        text = "📅 *Задачи дня*\n\n"
    elif filter_type == "user_tasks":
        text = "⭕ *Мои задачи*\n\n"
    elif filter_type == "inbox":
        text = "📥 *Inbox*\n\n"

    # Подсчёт задач
    daily_count = 0
    if daily_entry:
        for i in range(1, 4):
            if getattr(daily_entry, f"task_{i}"):
                daily_count += 1

    total_count = len(tasks) + len(inbox_tasks) + daily_count
    if total_count > 0:
        text += f"Задач: {total_count}"
    else:
        text += "Задач нет"

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_tasks_main_menu(
            tasks,
            completions_today,
            stats_today,
            inbox_tasks=inbox_tasks,
            daily_entry=daily_entry,
            filter_type=filter_type
        )
    )
    await callback.answer()


# ============ ADD TASK ============

@router.callback_query(F.data == "task_add")
async def start_add_task(callback: CallbackQuery, state: FSMContext):
    """Начало добавления задачи"""
    await state.set_state(UserTaskStates.adding_name)

    await callback.message.edit_text(
        "➕ *Добавление задачи*\n\n"
        "Напиши название задачи:\n"
        "_Например: Тренировка в зале, Прочитать 20 страниц, Медитация_",
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )


@router.message(UserTaskStates.adding_name)
async def process_task_name(message: Message, state: FSMContext):
    """Обработка названия задачи"""
    name = message.text.strip()

    if len(name) > 200:
        await message.answer("Название слишком длинное (макс. 200 символов)")
        return

    await state.update_data(task_name=name)
    await state.set_state(UserTaskStates.adding_reward)

    await message.answer(
        f"✅ Название: *{name}*\n\n"
        "Теперь укажи награду в рублях:\n"
        "_Сколько ты заработаешь за выполнение этой задачи?_\n\n"
        "Примеры: 30, 50, 100",
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )


@router.message(UserTaskStates.adding_reward)
async def process_task_reward(message: Message, state: FSMContext):
    """Обработка награды за задачу"""
    try:
        reward = int(message.text.strip())
        if reward <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("Введи положительное число")
        return

    data = await state.get_data()
    await state.update_data(task_reward=reward)
    await state.set_state(UserTaskStates.adding_type)

    await message.answer(
        f"✅ Задача: *{data['task_name']}*\n"
        f"💰 Награда: *{reward}₽*\n\n"
        "Выбери тип задачи:",
        parse_mode="Markdown",
        reply_markup=get_task_type_keyboard()
    )


@router.callback_query(F.data.startswith("task_type:"))
async def process_task_type(callback: CallbackQuery, state: FSMContext):
    """Обработка типа задачи"""
    task_type = callback.data.split(":")[1]
    is_recurring = task_type == "recurring"

    await state.update_data(task_is_recurring=is_recurring)
    await state.set_state(UserTaskStates.adding_category)

    type_text = "повторяющаяся" if is_recurring else "одноразовая"
    data = await state.get_data()

    await callback.message.edit_text(
        f"✅ Задача: *{data['task_name']}*\n"
        f"💰 Награда: *{data['task_reward']}₽*\n"
        f"🔄 Тип: *{type_text}*\n\n"
        "Выбери категорию (необязательно):",
        parse_mode="Markdown",
        reply_markup=get_task_category_keyboard()
    )


@router.callback_query(F.data.startswith("task_category:"))
async def process_task_category(callback: CallbackQuery, state: FSMContext):
    """Обработка категории задачи"""
    category = callback.data.split(":")[1]

    if category == "skip":
        category = None

    await save_task(callback.message, state, callback.from_user.id, category)


async def save_task(message, state: FSMContext, telegram_id: int, category: str | None):
    """Сохранение задачи"""
    data = await state.get_data()
    await state.clear()

    user = get_user_by_telegram_id(telegram_id)
    if not user:
        return

    task = add_user_task(
        user_id=user.id,
        name=data['task_name'],
        reward_amount=data['task_reward'],
        is_recurring=data['task_is_recurring'],
        category=category
    )

    type_text = "Повторяющаяся" if task.is_recurring else "Одноразовая"
    category_emoji = {
        "sport": "🏃",
        "learning": "📚",
        "personal": "🌱",
        "work": "💼"
    }

    text = (
        "🎉 *Задача создана!*\n\n"
        f"📝 {task.name}\n"
        f"💰 Награда: {task.reward_amount}₽\n"
        f"🔄 Тип: {type_text}\n"
    )

    if category:
        emoji = category_emoji.get(category, "📁")
        text += f"{emoji} Категория: {category}\n"

    text += "\n_Теперь выполняй задачу и зарабатывай награды!_"

    tasks, completions_today, stats_today, inbox_tasks, daily_entry = _get_tasks_keyboard_data(user.id)

    await message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_tasks_main_menu(
            tasks, completions_today, stats_today,
            inbox_tasks=inbox_tasks, daily_entry=daily_entry
        )
    )


# ============ COMPLETE TASK ============

@router.callback_query(F.data.startswith("task_complete:"))
async def complete_task(callback: CallbackQuery):
    """Отметить задачу как выполненную"""
    task_id = int(callback.data.split(":")[1])
    user = get_user_by_telegram_id(callback.from_user.id)

    if not user:
        await callback.answer("Ошибка")
        return

    result = complete_user_task(user.id, task_id)

    if result["success"]:
        task = get_user_task(task_id)
        type_text = "Отлично!" if task and task.is_recurring else "Задача выполнена и архивирована!"

        text = (
            f"🎉 *{type_text}*\n\n"
            f"💰 +{result['reward']}₽ за выполнение!\n"
            f"📊 Баланс: {result['balance']}₽\n\n"
            f"_{result['message']}_"
        )
    else:
        text = f"ℹ️ {result['message']}"

    # Обновляем список задач
    tasks, completions_today, stats_today, inbox_tasks, daily_entry = _get_tasks_keyboard_data(user.id)

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_tasks_main_menu(
            tasks, completions_today, stats_today,
            inbox_tasks=inbox_tasks, daily_entry=daily_entry
        )
    )


@router.callback_query(F.data == "task_already_completed")
async def task_already_completed(callback: CallbackQuery):
    """Информация о уже выполненной задаче"""
    await callback.answer(
        "Задача уже выполнена сегодня!\nЗавтра сможешь выполнить снова.",
        show_alert=True
    )


# ============ VIEW TASK ============

@router.callback_query(F.data.startswith("task_view:"))
async def view_task(callback: CallbackQuery):
    """Просмотр задачи с деталями"""
    task_id = int(callback.data.split(":")[1])
    task = get_user_task(task_id)

    if not task:
        await callback.answer("Задача не найдена")
        return

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        return

    # Проверить, выполнена ли сегодня
    completions_today = get_task_completions_today(user.id, task_id)
    already_completed = completions_today > 0

    # История выполнений
    history = get_task_history(task_id, limit=100)
    total_completions = len(history)

    type_text = "Повторяющаяся" if task.is_recurring else "Одноразовая"
    category_emoji = {
        "sport": "🏃 Спорт и здоровье",
        "learning": "📚 Обучение",
        "personal": "🌱 Личное развитие",
        "work": "💼 Работа над проектами"
    }

    text = (
        f"📝 *{task.name}*\n\n"
        f"💰 Награда: {task.reward_amount}₽\n"
        f"🔄 Тип: {type_text}\n"
    )

    if task.category:
        category_text = category_emoji.get(task.category, task.category)
        text += f"📁 Категория: {category_text}\n"

    text += f"\n📊 Выполнений всего: {total_completions}"

    if task.is_recurring:
        if already_completed:
            text += "\n✅ Выполнено сегодня"
        else:
            text += "\n⭕ Можно выполнить сегодня"

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_task_view_keyboard(task_id, already_completed, task.is_recurring)
    )


# ============ TASK HISTORY ============

@router.callback_query(F.data.startswith("task_history:"))
async def show_task_history(callback: CallbackQuery):
    """История выполнений задачи"""
    task_id = int(callback.data.split(":")[1])
    task = get_user_task(task_id)

    if not task:
        await callback.answer("Задача не найдена")
        return

    history = get_task_history(task_id, limit=10)

    text = f"📊 *История: {task.name}*\n\n"

    if history:
        for completion in history:
            date_str = completion.completed_at.strftime("%d.%m.%Y %H:%M")
            text += f"✅ {date_str} — +{task.reward_amount}₽\n"
    else:
        text += "_Задача ещё не выполнялась_"

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_task_history_keyboard(task_id)
    )


# ============ EDIT TASK ============

@router.callback_query(F.data.startswith("task_edit:"))
async def start_edit_task(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования задачи"""
    task_id = int(callback.data.split(":")[1])
    task = get_user_task(task_id)

    if not task:
        await callback.answer("Задача не найдена")
        return

    await state.set_state(UserTaskStates.editing_name)
    await state.update_data(
        editing_task_id=task_id,
        old_name=task.name,
        old_reward=task.reward_amount
    )

    await callback.message.edit_text(
        f"✏️ *Редактирование задачи*\n\n"
        f"Текущее название: {task.name}\n\n"
        "Введи новое название или отправь точку (.) чтобы оставить:",
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )


@router.message(UserTaskStates.editing_name)
async def process_edit_name(message: Message, state: FSMContext):
    """Обработка нового названия"""
    data = await state.get_data()
    new_name = message.text.strip()

    if new_name == ".":
        new_name = data['old_name']

    await state.update_data(new_name=new_name)
    await state.set_state(UserTaskStates.editing_reward)

    await message.answer(
        f"✅ Название: {new_name}\n\n"
        f"Текущая награда: {data['old_reward']}₽\n\n"
        "Введи новую награду или точку (.) чтобы оставить:",
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )


@router.message(UserTaskStates.editing_reward)
async def process_edit_reward(message: Message, state: FSMContext):
    """Обработка новой награды"""
    data = await state.get_data()

    if message.text.strip() == ".":
        new_reward = data['old_reward']
    else:
        try:
            new_reward = int(message.text.strip())
            if new_reward <= 0:
                raise ValueError()
        except ValueError:
            await message.answer("Введи положительное число")
            return

    # Сохраняем
    update_user_task(
        data['editing_task_id'],
        name=data['new_name'],
        reward_amount=new_reward
    )
    await state.clear()

    user = get_user_by_telegram_id(message.from_user.id)
    tasks, completions_today, stats_today, inbox_tasks, daily_entry = _get_tasks_keyboard_data(user.id)

    await message.answer(
        f"✅ *Задача обновлена!*\n\n"
        f"📝 {data['new_name']}\n"
        f"💰 {new_reward}₽",
        parse_mode="Markdown",
        reply_markup=get_tasks_main_menu(
            tasks, completions_today, stats_today,
            inbox_tasks=inbox_tasks, daily_entry=daily_entry
        )
    )


# ============ DELETE TASK ============

@router.callback_query(F.data.startswith("task_delete:"))
async def confirm_delete_task(callback: CallbackQuery):
    """Подтверждение удаления задачи"""
    task_id = int(callback.data.split(":")[1])
    task = get_user_task(task_id)

    if not task:
        await callback.answer("Задача не найдена")
        return

    await callback.message.edit_text(
        f"🗑 *Удалить задачу?*\n\n"
        f"📝 {task.name}\n"
        f"💰 {task.reward_amount}₽\n\n"
        "_Это действие нельзя отменить_",
        parse_mode="Markdown",
        reply_markup=get_task_delete_confirm_keyboard(task_id)
    )


@router.callback_query(F.data.startswith("task_delete_confirm:"))
async def execute_delete_task(callback: CallbackQuery):
    """Удаление задачи (soft delete)"""
    task_id = int(callback.data.split(":")[1])

    success = delete_user_task(task_id)

    if success:
        await callback.answer("✅ Задача удалена")
    else:
        await callback.answer("❌ Ошибка удаления")

    user = get_user_by_telegram_id(callback.from_user.id)
    tasks, completions_today, stats_today, inbox_tasks, daily_entry = _get_tasks_keyboard_data(user.id)

    await callback.message.edit_text(
        "📋 *Мои задачи*\n\n"
        "_Задача удалена_",
        parse_mode="Markdown",
        reply_markup=get_tasks_main_menu(
            tasks, completions_today, stats_today,
            inbox_tasks=inbox_tasks, daily_entry=daily_entry
        )
    )


# ============ CANCEL ============

@router.callback_query(F.data == "task_cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        return

    tasks = get_user_tasks(user.id, active_only=True)
    stats_today = get_user_stats_today(user.id)
    completions_today = {}
    for t in tasks:
        count = get_task_completions_today(user.id, t.id)
        completions_today[t.id] = count

    tasks, completions_today, stats_today, inbox_tasks, daily_entry = _get_tasks_keyboard_data(user.id)

    await callback.message.edit_text(
        "📋 *Мои задачи*\n\n"
        "_Действие отменено_",
        parse_mode="Markdown",
        reply_markup=get_tasks_main_menu(
            tasks, completions_today, stats_today,
            inbox_tasks=inbox_tasks, daily_entry=daily_entry
        )
    )


# ============ DAILY TASKS (из утреннего кайдзена) ============

@router.callback_query(F.data.startswith("daily_task_complete:"))
async def complete_daily_task(callback: CallbackQuery):
    """
    Отметить задачу дня как выполненную.
    Callback format: daily_task_complete:{entry_id}:{task_num}
    """
    try:
        _, entry_id, task_num = callback.data.split(":")
        entry_id = int(entry_id)
        task_num = int(task_num)
    except (ValueError, IndexError):
        await callback.answer("Ошибка данных")
        return

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    session = get_session()
    try:
        entry = session.query(DailyEntry).filter(
            DailyEntry.id == entry_id,
            DailyEntry.user_id == user.id
        ).first()

        if not entry:
            await callback.answer("Запись не найдена")
            return

        # Проверить, не выполнена ли уже
        task_done_field = f"task_{task_num}_done"
        if getattr(entry, task_done_field):
            await callback.answer("Задача уже выполнена!", show_alert=True)
            return

        # Отметить как выполненную
        setattr(entry, task_done_field, True)
        session.commit()

        # Начислить награду
        task_text = getattr(entry, f"task_{task_num}")
        base_reward = 20

        # Проверить приоритетность
        is_priority = (entry.priority_task == task_num)
        priority_bonus = 50 if is_priority else 0
        total_reward = base_reward + priority_bonus

        add_reward(
            user_id=user.id,
            amount=total_reward,
            transaction_type="daily_task_done",
            description=f"Задача дня: {task_text[:50]}",
            daily_entry_id=entry.id
        )

        balance = get_reward_balance(user.id)

    except Exception as e:
        print(f"Error completing daily task: {e}")
        await callback.answer("Произошла ошибка")
        return
    finally:
        session.close()

    # Формируем сообщение
    priority_msg = "\n⭐ Главная задача дня! +50₽ бонус" if is_priority else ""

    # Получаем обновлённые данные для клавиатуры
    tasks, completions_today, stats_today, inbox_tasks, daily_entry = _get_tasks_keyboard_data(user.id)

    text = (
        f"🎉 *Отлично!*\n\n"
        f"✅ {task_text}\n\n"
        f"💰 +{total_reward}₽ за выполнение!{priority_msg}\n"
        f"📊 Баланс: {balance}₽"
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_tasks_main_menu(
            tasks, completions_today, stats_today,
            inbox_tasks=inbox_tasks, daily_entry=daily_entry
        )
    )
    await callback.answer("Награда начислена!")


@router.callback_query(F.data.startswith("daily_task_info:"))
async def daily_task_info(callback: CallbackQuery):
    """
    Информация о выполненной задаче дня.
    Callback format: daily_task_info:{entry_id}:{task_num}
    """
    await callback.answer(
        "✅ Задача уже выполнена сегодня!",
        show_alert=True
    )
