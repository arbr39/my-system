"""
GTD Weekly Review Handler - еженедельный обзор

Структурированный review: inbox → цели → someday → рефлексия → план на неделю.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.database.crud import (
    get_or_create_user, get_user_inbox, get_user_goals, get_user_someday,
    get_or_create_weekly_review, update_weekly_review, complete_weekly_review,
    update_inbox_item, move_inbox_to_someday, delete_inbox_item,
    get_inbox_count, mark_someday_reviewed
)
from src.keyboards.inline import (
    get_review_start_keyboard, get_review_inbox_keyboard,
    get_review_goals_keyboard, get_review_someday_keyboard,
    get_review_skip_keyboard, get_main_menu, get_back_keyboard
)

router = Router()


class ReviewStates(StatesGroup):
    """Состояния weekly review"""
    inbox_review = State()
    goals_review = State()
    someday_review = State()
    week_wins = State()
    week_learnings = State()
    week_plan = State()


# ============ Запуск Review ============

@router.message(Command("review"))
async def cmd_review(message: Message, state: FSMContext):
    """Команда /review - ручной запуск weekly review"""
    user = get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )

    inbox_count = get_inbox_count(user.id)

    await message.answer(
        "📋 *Weekly Review*\n\n"
        f"📥 В inbox: {inbox_count} задач\n\n"
        "Это важная часть GTD - еженедельный обзор.\n"
        "Займёт 10-15 минут.",
        parse_mode="Markdown",
        reply_markup=get_review_start_keyboard()
    )


@router.callback_query(F.data == "review_start")
async def callback_review_start(callback: CallbackQuery, state: FSMContext):
    """Показать стартовый экран review"""
    user = get_or_create_user(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.first_name
    )

    inbox_count = get_inbox_count(user.id)

    await callback.message.edit_text(
        "📋 *Weekly Review*\n\n"
        f"📥 В inbox: {inbox_count} задач\n\n"
        "Это важная часть GTD - еженедельный обзор.\n"
        "Займёт 10-15 минут.",
        parse_mode="Markdown",
        reply_markup=get_review_start_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "review_begin")
async def begin_review(callback: CallbackQuery, state: FSMContext):
    """Начать review - шаг 1: Inbox"""
    user = get_or_create_user(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.first_name
    )

    # Создаём или получаем review
    review = get_or_create_weekly_review(user.id)
    await state.update_data(user_id=user.id, review_id=review.id, inbox_processed=0)

    # Получаем inbox
    inbox_items = get_user_inbox(user.id)

    if not inbox_items:
        # Пропускаем inbox, идём к целям
        await show_goals_review(callback.message, state)
    else:
        await state.update_data(inbox_items=[item.id for item in inbox_items], inbox_index=0)
        await show_next_inbox_item(callback.message, state)

    await state.set_state(ReviewStates.inbox_review)
    await callback.answer()


# ============ Шаг 1: Inbox Review ============

async def show_next_inbox_item(message, state: FSMContext):
    """Показать следующий элемент inbox"""
    data = await state.get_data()
    inbox_ids = data.get("inbox_items", [])
    index = data.get("inbox_index", 0)

    if index >= len(inbox_ids):
        # Inbox закончился, идём к целям
        await show_goals_review(message, state)
        return

    from src.database.crud import get_inbox_item
    item = get_inbox_item(inbox_ids[index])

    if not item:
        # Элемент удалён, переходим к следующему
        await state.update_data(inbox_index=index + 1)
        await show_next_inbox_item(message, state)
        return

    remaining = len(inbox_ids) - index - 1

    try:
        await message.edit_text(
            f"📥 *Inbox Review* ({index + 1}/{len(inbox_ids)})\n\n"
            f"_{item.text}_\n\n"
            f"Что делаем с этой задачей?",
            parse_mode="Markdown",
            reply_markup=get_review_inbox_keyboard(item.id, remaining)
        )
    except:
        await message.answer(
            f"📥 *Inbox Review* ({index + 1}/{len(inbox_ids)})\n\n"
            f"_{item.text}_\n\n"
            f"Что делаем с этой задачей?",
            parse_mode="Markdown",
            reply_markup=get_review_inbox_keyboard(item.id, remaining)
        )


@router.callback_query(F.data.startswith("review_inbox_done:"), ReviewStates.inbox_review)
async def review_inbox_done(callback: CallbackQuery, state: FSMContext):
    """Элемент обработан"""
    item_id = int(callback.data.split(":")[1])
    update_inbox_item(item_id, status="processed")

    data = await state.get_data()
    processed = data.get("inbox_processed", 0) + 1
    await state.update_data(
        inbox_processed=processed,
        inbox_index=data.get("inbox_index", 0) + 1
    )

    await show_next_inbox_item(callback.message, state)
    await callback.answer("✅ Обработано")


@router.callback_query(F.data.startswith("review_inbox_someday:"), ReviewStates.inbox_review)
async def review_inbox_someday(callback: CallbackQuery, state: FSMContext):
    """Переместить в someday"""
    item_id = int(callback.data.split(":")[1])
    move_inbox_to_someday(item_id)

    data = await state.get_data()
    processed = data.get("inbox_processed", 0) + 1
    await state.update_data(
        inbox_processed=processed,
        inbox_index=data.get("inbox_index", 0) + 1
    )

    await show_next_inbox_item(callback.message, state)
    await callback.answer("📦 В 'Когда-нибудь'")


@router.callback_query(F.data.startswith("review_inbox_delete:"), ReviewStates.inbox_review)
async def review_inbox_delete(callback: CallbackQuery, state: FSMContext):
    """Удалить элемент"""
    item_id = int(callback.data.split(":")[1])
    delete_inbox_item(item_id)

    data = await state.get_data()
    processed = data.get("inbox_processed", 0) + 1
    await state.update_data(
        inbox_processed=processed,
        inbox_index=data.get("inbox_index", 0) + 1
    )

    await show_next_inbox_item(callback.message, state)
    await callback.answer("🗑 Удалено")


@router.callback_query(F.data == "review_inbox_next", ReviewStates.inbox_review)
async def review_inbox_next(callback: CallbackQuery, state: FSMContext):
    """Пропустить элемент"""
    data = await state.get_data()
    await state.update_data(inbox_index=data.get("inbox_index", 0) + 1)
    await show_next_inbox_item(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "review_inbox_finish", ReviewStates.inbox_review)
async def review_inbox_finish(callback: CallbackQuery, state: FSMContext):
    """Inbox закончен"""
    await show_goals_review(callback.message, state)
    await callback.answer()


# ============ Шаг 2: Goals Review ============

async def show_goals_review(message, state: FSMContext):
    """Показать обзор целей"""
    data = await state.get_data()
    goals = get_user_goals(data.get("user_id"))

    await state.set_state(ReviewStates.goals_review)

    if not goals:
        # Нет целей, пропускаем
        try:
            await message.edit_text(
                "🎯 *Цели*\n\n"
                "У тебя пока нет целей.\n"
                "Подумай о добавлении целей на неделе!",
                parse_mode="Markdown",
                reply_markup=get_back_keyboard()
            )
        except:
            await message.answer(
                "🎯 *Цели*\n\n"
                "У тебя пока нет целей.\n"
                "Подумай о добавлении целей на неделе!",
                parse_mode="Markdown",
                reply_markup=get_back_keyboard()
            )
        # Переходим к someday
        await show_someday_review(message, state)
    else:
        try:
            await message.edit_text(
                f"🎯 *Обзор целей* ({len(goals)})\n\n"
                "Просмотри свои цели. Актуальны ли они?\n"
                "Нужно ли что-то изменить?",
                parse_mode="Markdown",
                reply_markup=get_review_goals_keyboard(goals)
            )
        except:
            await message.answer(
                f"🎯 *Обзор целей* ({len(goals)})\n\n"
                "Просмотри свои цели. Актуальны ли они?\n"
                "Нужно ли что-то изменить?",
                parse_mode="Markdown",
                reply_markup=get_review_goals_keyboard(goals)
            )


@router.callback_query(F.data.startswith("review_goal:"), ReviewStates.goals_review)
async def review_goal_detail(callback: CallbackQuery, state: FSMContext):
    """Просмотр цели (пока заглушка)"""
    await callback.answer("Цель просмотрена")


@router.callback_query(F.data == "review_goals_done", ReviewStates.goals_review)
async def review_goals_done(callback: CallbackQuery, state: FSMContext):
    """Цели просмотрены"""
    data = await state.get_data()
    update_weekly_review(data.get("review_id"), goals_reviewed=True)

    await show_someday_review(callback.message, state)
    await callback.answer()


# ============ Шаг 3: Someday Review ============

async def show_someday_review(message, state: FSMContext):
    """Показать обзор someday"""
    data = await state.get_data()
    items = get_user_someday(data.get("user_id"))

    await state.set_state(ReviewStates.someday_review)

    if not items:
        # Нет someday, пропускаем к рефлексии
        await show_week_wins(message, state)
    else:
        try:
            await message.edit_text(
                f"💭 *Когда-нибудь/может быть* ({len(items)})\n\n"
                "Просмотри свои отложенные идеи.\n"
                "Может, что-то пора активировать?",
                parse_mode="Markdown",
                reply_markup=get_review_someday_keyboard(items)
            )
        except:
            await message.answer(
                f"💭 *Когда-нибудь/может быть* ({len(items)})\n\n"
                "Просмотри свои отложенные идеи.\n"
                "Может, что-то пора активировать?",
                parse_mode="Markdown",
                reply_markup=get_review_someday_keyboard(items)
            )


@router.callback_query(F.data.startswith("review_someday:"), ReviewStates.someday_review)
async def review_someday_item(callback: CallbackQuery, state: FSMContext):
    """Отметить someday как просмотренный"""
    item_id = int(callback.data.split(":")[1])
    mark_someday_reviewed(item_id)
    await callback.answer("Просмотрено")


@router.callback_query(F.data == "review_someday_done", ReviewStates.someday_review)
async def review_someday_done(callback: CallbackQuery, state: FSMContext):
    """Someday просмотрен"""
    await show_week_wins(callback.message, state)
    await callback.answer()


# ============ Шаг 4: Рефлексия - Победы недели ============

async def show_week_wins(message, state: FSMContext):
    """Спросить о победах недели"""
    await state.set_state(ReviewStates.week_wins)

    try:
        await message.edit_text(
            "🏆 *Победы недели*\n\n"
            "Что получилось на этой неделе?\n"
            "Какие достижения, даже маленькие?",
            parse_mode="Markdown",
            reply_markup=get_review_skip_keyboard()
        )
    except:
        await message.answer(
            "🏆 *Победы недели*\n\n"
            "Что получилось на этой неделе?\n"
            "Какие достижения, даже маленькие?",
            parse_mode="Markdown",
            reply_markup=get_review_skip_keyboard()
        )


@router.message(ReviewStates.week_wins)
async def process_week_wins(message: Message, state: FSMContext):
    """Сохранить победы недели"""
    data = await state.get_data()
    update_weekly_review(data.get("review_id"), week_wins=message.text)

    await state.set_state(ReviewStates.week_learnings)
    await message.answer(
        "📚 *Уроки недели*\n\n"
        "Чему научился на этой неделе?\n"
        "Что понял, осознал?",
        parse_mode="Markdown",
        reply_markup=get_review_skip_keyboard()
    )


@router.callback_query(F.data == "review_skip", ReviewStates.week_wins)
async def skip_week_wins(callback: CallbackQuery, state: FSMContext):
    """Пропустить победы"""
    await state.set_state(ReviewStates.week_learnings)
    await callback.message.edit_text(
        "📚 *Уроки недели*\n\n"
        "Чему научился на этой неделе?\n"
        "Что понял, осознал?",
        parse_mode="Markdown",
        reply_markup=get_review_skip_keyboard()
    )
    await callback.answer()


# ============ Шаг 5: Уроки недели ============

@router.message(ReviewStates.week_learnings)
async def process_week_learnings(message: Message, state: FSMContext):
    """Сохранить уроки недели"""
    data = await state.get_data()
    update_weekly_review(data.get("review_id"), week_learnings=message.text)

    await state.set_state(ReviewStates.week_plan)
    await message.answer(
        "📝 *План на следующую неделю*\n\n"
        "Какие главные задачи на следующую неделю?\n"
        "На чём сфокусироваться?",
        parse_mode="Markdown",
        reply_markup=get_review_skip_keyboard()
    )


@router.callback_query(F.data == "review_skip", ReviewStates.week_learnings)
async def skip_week_learnings(callback: CallbackQuery, state: FSMContext):
    """Пропустить уроки"""
    await state.set_state(ReviewStates.week_plan)
    await callback.message.edit_text(
        "📝 *План на следующую неделю*\n\n"
        "Какие главные задачи на следующую неделю?\n"
        "На чём сфокусироваться?",
        parse_mode="Markdown",
        reply_markup=get_review_skip_keyboard()
    )
    await callback.answer()


# ============ Шаг 6: План на неделю и завершение ============

@router.message(ReviewStates.week_plan)
async def process_week_plan(message: Message, state: FSMContext):
    """Сохранить план и завершить review"""
    data = await state.get_data()
    update_weekly_review(data.get("review_id"), week_plan=message.text)
    await finish_review(message, state)


@router.callback_query(F.data == "review_skip", ReviewStates.week_plan)
async def skip_week_plan(callback: CallbackQuery, state: FSMContext):
    """Пропустить план"""
    await callback.message.edit_text("⏳ Завершаю review...")
    await finish_review(callback.message, state)
    await callback.answer()


async def finish_review(message, state: FSMContext):
    """Завершение weekly review"""
    data = await state.get_data()

    # Завершаем review
    complete_weekly_review(data.get("review_id"))

    # === НАГРАДА за Weekly Review ===
    from src.database.crud_rewards import grant_weekly_review_reward, get_reward_balance_by_telegram_id

    reward_amount = grant_weekly_review_reward(
        user_id=data.get("user_id"),
        weekly_review_id=data.get("review_id")
    )

    # Формируем итог
    summary = "✅ *Weekly Review завершён!*\n\n"
    summary += f"📥 Обработано в inbox: {data.get('inbox_processed', 0)}\n"
    summary += f"🎯 Цели просмотрены\n"
    summary += f"💭 Someday просмотрен\n\n"

    # Показываем награду
    if reward_amount > 0:
        balance = get_reward_balance_by_telegram_id(message.chat.id)
        summary += f"💰 *+{reward_amount}₽* за Weekly Review!\n"
        summary += f"📊 Баланс: {balance}₽\n\n"

    summary += "Отличная работа! Ты готов к новой неделе!"

    try:
        await message.edit_text(summary, parse_mode="Markdown", reply_markup=get_main_menu())
    except:
        await message.answer(summary, parse_mode="Markdown", reply_markup=get_main_menu())

    await state.clear()
