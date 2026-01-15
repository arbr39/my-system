from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.database.crud import get_user_by_telegram_id, get_user_goals, create_goal
from src.keyboards.inline import get_goals_keyboard, get_back_keyboard, get_main_menu

router = Router()


class GoalStates(StatesGroup):
    """Состояния добавления цели"""
    title = State()
    category = State()


@router.callback_query(F.data == "goals")
async def show_goals(callback: CallbackQuery):
    """Показать цели"""
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Сначала запусти /start")
        return

    goals = get_user_goals(user.id)

    if not goals:
        await callback.message.edit_text(
            "🎯 *Мои цели*\n\n"
            "У тебя пока нет целей.\n"
            "Добавь первую цель, чтобы отслеживать прогресс!",
            parse_mode="Markdown",
            reply_markup=get_goals_keyboard([])
        )
    else:
        text = "🎯 *Мои цели*\n\n"
        for goal in goals:
            status_emoji = {"active": "🎯", "paused": "⏸️", "completed": "✅"}.get(goal.status, "🎯")
            text += f"{status_emoji} {goal.title}\n"

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_goals_keyboard(goals)
        )

    await callback.answer()


@router.message(Command("goals"))
async def cmd_goals(message: Message):
    """Команда /goals"""
    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Сначала запусти /start")
        return

    goals = get_user_goals(user.id)

    if not goals:
        await message.answer(
            "🎯 *Мои цели*\n\nУ тебя пока нет целей.",
            parse_mode="Markdown",
            reply_markup=get_goals_keyboard([])
        )
    else:
        text = "🎯 *Мои цели*\n\n"
        for goal in goals:
            status_emoji = {"active": "🎯", "paused": "⏸️", "completed": "✅"}.get(goal.status, "🎯")
            text += f"{status_emoji} {goal.title}\n"

        await message.answer(text, parse_mode="Markdown", reply_markup=get_goals_keyboard(goals))


@router.callback_query(F.data == "add_goal")
async def add_goal_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления цели"""
    user = get_user_by_telegram_id(callback.from_user.id)
    await state.update_data(user_id=user.id)

    await callback.message.edit_text(
        "🎯 *Новая цель*\n\n"
        "Введи название цели:",
        parse_mode="Markdown"
    )
    await state.set_state(GoalStates.title)
    await callback.answer()


@router.message(GoalStates.title)
async def process_goal_title(message: Message, state: FSMContext):
    """Обработка названия цели"""
    data = await state.get_data()

    # Создаём цель
    goal = create_goal(
        user_id=data["user_id"],
        title=message.text,
        category="general"
    )

    await message.answer(
        f"✅ Цель добавлена!\n\n🎯 {goal.title}",
        reply_markup=get_main_menu()
    )
    await state.clear()


@router.callback_query(F.data.startswith("goal:"))
async def show_goal_detail(callback: CallbackQuery):
    """Показать детали цели"""
    goal_id = int(callback.data.split(":")[1])

    # Здесь можно добавить детальный просмотр и редактирование
    await callback.answer("Детали цели (в разработке)")
