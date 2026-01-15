"""
Handler для системы наград (@whysasha методика)

Фонд наград - ядро системы мотивации:
- Награда только за результат
- Личный список наград
- Анти-кортизол: празднуем победы
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.database.crud import get_user_by_telegram_id
from src.database.crud_rewards import (
    get_or_create_reward_fund,
    get_reward_fund_by_telegram_id,
    get_reward_balance_by_telegram_id,
    get_reward_items,
    get_reward_item,
    add_reward_item,
    update_reward_item,
    delete_reward_item,
    spend_reward,
    get_recent_transactions,
    get_reward_stats,
    toggle_penalties,
    update_reward_rates
)
from src.keyboards.inline_rewards import (
    get_rewards_main_menu,
    get_reward_items_keyboard,
    get_reward_view_keyboard,
    get_spend_confirm_keyboard,
    get_delete_confirm_keyboard,
    get_history_keyboard,
    get_settings_keyboard,
    get_cancel_keyboard,
    get_skip_category_keyboard
)
from src.keyboards.inline import get_main_menu

router = Router()


class RewardStates(StatesGroup):
    """Состояния для управления наградами"""
    adding_name = State()
    adding_price = State()
    adding_category = State()
    editing_name = State()
    editing_price = State()
    editing_rate = State()


# ============ MAIN MENU ============

@router.message(Command("rewards"))
async def cmd_rewards(message: Message):
    """Команда /rewards - показать фонд наград"""
    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Сначала используй /start")
        return

    fund = get_or_create_reward_fund(user.id)
    stats = get_reward_stats(user.id)

    text = (
        "💰 *Фонд наград*\n\n"
        f"📊 Баланс: *{stats['balance']}₽*\n"
        f"📈 Всего заработано: {stats['total_earned']}₽\n"
        f"📉 Всего потрачено: {stats['total_spent']}₽\n\n"
        "_Награждай себя только за результат!_"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_rewards_main_menu(stats['balance'], stats['total_earned'])
    )


@router.callback_query(F.data == "rewards_show")
async def show_rewards(callback: CallbackQuery, state: FSMContext):
    """Показать главное меню наград"""
    await state.clear()

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка: пользователь не найден")
        return

    fund = get_or_create_reward_fund(user.id)
    stats = get_reward_stats(user.id)

    text = (
        "💰 *Фонд наград*\n\n"
        f"📊 Баланс: *{stats['balance']}₽*\n"
        f"📈 Всего заработано: {stats['total_earned']}₽\n"
        f"📉 Всего потрачено: {stats['total_spent']}₽\n\n"
        "_Награждай себя только за результат!_"
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_rewards_main_menu(stats['balance'], stats['total_earned'])
    )


@router.callback_query(F.data == "rewards_balance_info")
async def balance_info(callback: CallbackQuery):
    """Информация о балансе"""
    await callback.answer(
        "Баланс = заработано - потрачено.\n"
        "Трать только на награды из своего списка!",
        show_alert=True
    )


# ============ REWARD ITEMS LIST ============

@router.callback_query(F.data == "rewards_items")
async def show_reward_items(callback: CallbackQuery, state: FSMContext):
    """Показать список наград"""
    await state.clear()

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка")
        return

    balance = get_reward_balance_by_telegram_id(callback.from_user.id)
    items = get_reward_items(user.id)

    if items:
        text = (
            "🎁 *Твои награды*\n\n"
            f"💰 Баланс: {balance}₽\n\n"
            "_Выбери награду, чтобы потратить:_"
        )
    else:
        text = (
            "🎁 *Твои награды*\n\n"
            "📭 Список пуст!\n\n"
            "_Добавь награды, на которые будешь тратить заработанное._"
        )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_reward_items_keyboard(items, balance)
    )


@router.callback_query(F.data == "rewards_empty")
async def rewards_empty_hint(callback: CallbackQuery):
    """Подсказка при пустом списке"""
    await callback.answer(
        "Добавь награды!\nПример: Кофе = 150₽, Ресторан = 500₽",
        show_alert=True
    )


# ============ VIEW REWARD ============

@router.callback_query(F.data.startswith("reward_view:"))
async def view_reward(callback: CallbackQuery):
    """Просмотр награды"""
    item_id = int(callback.data.split(":")[1])
    item = get_reward_item(item_id)

    if not item:
        await callback.answer("Награда не найдена")
        return

    balance = get_reward_balance_by_telegram_id(callback.from_user.id)
    can_afford = balance >= item.price

    status = "✅ Можешь позволить!" if can_afford else f"❌ Не хватает {item.price - balance}₽"

    text = (
        f"🎁 *{item.name}*\n\n"
        f"💵 Цена: {item.price}₽\n"
    )

    if item.category:
        text += f"📁 Категория: {item.category}\n"

    text += (
        f"\n{status}\n"
        f"💰 Твой баланс: {balance}₽"
    )

    if item.times_purchased > 0:
        text += f"\n\n📊 Куплено раз: {item.times_purchased}"

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_reward_view_keyboard(item_id, can_afford)
    )


# ============ ADD REWARD ============

@router.callback_query(F.data == "reward_add")
async def start_add_reward(callback: CallbackQuery, state: FSMContext):
    """Начало добавления награды"""
    await state.set_state(RewardStates.adding_name)

    await callback.message.edit_text(
        "➕ *Добавление награды*\n\n"
        "Напиши название награды:\n"
        "_Например: Кофе, Пицца, Кино, Ресторан_",
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )


@router.message(RewardStates.adding_name)
async def process_reward_name(message: Message, state: FSMContext):
    """Обработка названия награды"""
    name = message.text.strip()

    if len(name) > 100:
        await message.answer("❌ Название слишком длинное (макс. 100 символов)")
        return

    await state.update_data(reward_name=name)
    await state.set_state(RewardStates.adding_price)

    await message.answer(
        f"✅ Название: *{name}*\n\n"
        "Теперь укажи цену в рублях:\n"
        "_Например: 150_",
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )


@router.message(RewardStates.adding_price)
async def process_reward_price(message: Message, state: FSMContext):
    """Обработка цены награды"""
    try:
        price = int(message.text.strip())
        if price <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введи положительное число")
        return

    await state.update_data(reward_price=price)
    await state.set_state(RewardStates.adding_category)

    data = await state.get_data()

    await message.answer(
        f"✅ Награда: *{data['reward_name']}* — {price}₽\n\n"
        "Укажи категорию (опционально):\n"
        "_Например: еда, развлечения, шоппинг_\n\n"
        "Или нажми кнопку, чтобы пропустить.",
        parse_mode="Markdown",
        reply_markup=get_skip_category_keyboard()
    )


@router.callback_query(F.data == "reward_skip_category")
async def skip_category(callback: CallbackQuery, state: FSMContext):
    """Пропустить категорию"""
    await save_reward(callback.message, state, callback.from_user.id, None)


@router.message(RewardStates.adding_category)
async def process_reward_category(message: Message, state: FSMContext):
    """Обработка категории награды"""
    category = message.text.strip()[:50] if message.text.strip() else None
    await save_reward(message, state, message.from_user.id, category)


async def save_reward(message_or_callback, state: FSMContext, telegram_id: int, category: str | None):
    """Сохранение награды"""
    data = await state.get_data()
    await state.clear()

    user = get_user_by_telegram_id(telegram_id)
    if not user:
        return

    item = add_reward_item(
        user_id=user.id,
        name=data['reward_name'],
        price=data['reward_price'],
        category=category
    )

    text = (
        "🎉 *Награда добавлена!*\n\n"
        f"🎁 {item.name} — {item.price}₽"
    )
    if category:
        text += f"\n📁 Категория: {category}"

    text += "\n\n_Теперь работай и зарабатывай на неё!_"

    balance = get_reward_balance_by_telegram_id(telegram_id)
    items = get_reward_items(user.id)

    if hasattr(message_or_callback, 'edit_text'):
        await message_or_callback.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_reward_items_keyboard(items, balance)
        )
    else:
        await message_or_callback.answer(
            text,
            parse_mode="Markdown",
            reply_markup=get_reward_items_keyboard(items, balance)
        )


# ============ SPEND REWARD ============

@router.callback_query(F.data.startswith("reward_spend:"))
async def confirm_spend(callback: CallbackQuery):
    """Подтверждение траты"""
    item_id = int(callback.data.split(":")[1])
    item = get_reward_item(item_id)

    if not item:
        await callback.answer("Награда не найдена")
        return

    balance = get_reward_balance_by_telegram_id(callback.from_user.id)

    if balance < item.price:
        await callback.answer(f"Недостаточно средств! Нужно {item.price}₽", show_alert=True)
        return

    await callback.message.edit_text(
        f"🎉 *Ты заслужил награду!*\n\n"
        f"🎁 {item.name} — {item.price}₽\n\n"
        f"💰 Баланс после: {balance - item.price}₽\n\n"
        "_Потратить?_",
        parse_mode="Markdown",
        reply_markup=get_spend_confirm_keyboard(item_id)
    )


@router.callback_query(F.data.startswith("reward_spend_confirm:"))
async def execute_spend(callback: CallbackQuery):
    """Выполнить трату"""
    item_id = int(callback.data.split(":")[1])
    user = get_user_by_telegram_id(callback.from_user.id)

    if not user:
        await callback.answer("Ошибка")
        return

    success, message, new_balance = spend_reward(user.id, item_id)
    item = get_reward_item(item_id)

    if success:
        text = (
            "🎊 *Поздравляю!*\n\n"
            f"Ты заработал и потратил на:\n"
            f"🎁 *{item.name}*\n\n"
            f"💰 Осталось: {new_balance}₽\n\n"
            "_Наслаждайся — ты это заслужил!_"
        )
    else:
        text = f"❌ {message}"

    stats = get_reward_stats(user.id)

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_rewards_main_menu(stats['balance'], stats['total_earned'])
    )


# ============ DELETE REWARD ============

@router.callback_query(F.data.startswith("reward_delete:"))
async def confirm_delete(callback: CallbackQuery):
    """Подтверждение удаления"""
    item_id = int(callback.data.split(":")[1])
    item = get_reward_item(item_id)

    if not item:
        await callback.answer("Награда не найдена")
        return

    await callback.message.edit_text(
        f"🗑 *Удалить награду?*\n\n"
        f"🎁 {item.name} — {item.price}₽\n\n"
        "_Это действие нельзя отменить_",
        parse_mode="Markdown",
        reply_markup=get_delete_confirm_keyboard(item_id)
    )


@router.callback_query(F.data.startswith("reward_delete_confirm:"))
async def execute_delete(callback: CallbackQuery):
    """Выполнить удаление"""
    item_id = int(callback.data.split(":")[1])

    success = delete_reward_item(item_id)

    if success:
        await callback.answer("✅ Награда удалена")
    else:
        await callback.answer("❌ Ошибка удаления")

    user = get_user_by_telegram_id(callback.from_user.id)
    balance = get_reward_balance_by_telegram_id(callback.from_user.id)
    items = get_reward_items(user.id)

    await callback.message.edit_text(
        "🎁 *Твои награды*\n\n"
        f"💰 Баланс: {balance}₽",
        parse_mode="Markdown",
        reply_markup=get_reward_items_keyboard(items, balance)
    )


# ============ EDIT REWARD ============

@router.callback_query(F.data.startswith("reward_edit:"))
async def start_edit_reward(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования награды"""
    item_id = int(callback.data.split(":")[1])
    item = get_reward_item(item_id)

    if not item:
        await callback.answer("Награда не найдена")
        return

    await state.set_state(RewardStates.editing_name)
    await state.update_data(editing_item_id=item_id, old_name=item.name, old_price=item.price)

    await callback.message.edit_text(
        f"✏️ *Редактирование*\n\n"
        f"Текущее название: {item.name}\n\n"
        "Введи новое название или отправь точку (.) чтобы оставить:",
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )


@router.message(RewardStates.editing_name)
async def process_edit_name(message: Message, state: FSMContext):
    """Обработка нового названия"""
    data = await state.get_data()
    new_name = message.text.strip()

    if new_name == ".":
        new_name = data['old_name']

    await state.update_data(new_name=new_name)
    await state.set_state(RewardStates.editing_price)

    await message.answer(
        f"✅ Название: {new_name}\n\n"
        f"Текущая цена: {data['old_price']}₽\n\n"
        "Введи новую цену или точку (.) чтобы оставить:",
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )


@router.message(RewardStates.editing_price)
async def process_edit_price(message: Message, state: FSMContext):
    """Обработка новой цены"""
    data = await state.get_data()

    if message.text.strip() == ".":
        new_price = data['old_price']
    else:
        try:
            new_price = int(message.text.strip())
            if new_price <= 0:
                raise ValueError()
        except ValueError:
            await message.answer("❌ Введи положительное число")
            return

    # Сохраняем
    update_reward_item(data['editing_item_id'], name=data['new_name'], price=new_price)
    await state.clear()

    await message.answer(
        f"✅ *Награда обновлена!*\n\n"
        f"🎁 {data['new_name']} — {new_price}₽",
        parse_mode="Markdown",
        reply_markup=get_rewards_main_menu(
            get_reward_balance_by_telegram_id(message.from_user.id),
            0
        )
    )


# ============ HISTORY ============

@router.callback_query(F.data == "rewards_history")
@router.callback_query(F.data.startswith("rewards_history:"))
async def show_history(callback: CallbackQuery):
    """Показать историю транзакций"""
    page = 0
    if ":" in callback.data:
        page = int(callback.data.split(":")[1])

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка")
        return

    per_page = 10
    transactions = get_recent_transactions(user.id, limit=per_page + 1)

    # Пагинация
    has_more = len(transactions) > per_page
    transactions = transactions[:per_page]

    if not transactions:
        text = (
            "📜 *История транзакций*\n\n"
            "Пока пусто.\n"
            "_Заверши утренний или вечерний кайдзен, чтобы заработать первые рубли!_"
        )
    else:
        text = "📜 *История транзакций*\n\n"

        type_emojis = {
            "morning_kaizen": "🌅",
            "evening_reflection": "🌙",
            "task_done": "✅",
            "priority_task": "⭐",
            "exercise": "🏃",
            "eating_well": "🥗",
            "weekly_review": "📋",
            "streak_bonus": "🔥",
            "inbox_task_done": "📥",
            "reward_spent": "🎁",
            "penalty": "⚠️"
        }

        for t in transactions:
            emoji = type_emojis.get(t.transaction_type, "💰")
            sign = "+" if t.amount > 0 else ""
            date_str = t.created_at.strftime("%d.%m %H:%M")
            text += f"{emoji} {sign}{t.amount}₽ — {date_str}\n"

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_history_keyboard(has_more, page)
    )


# ============ SETTINGS ============

@router.callback_query(F.data == "rewards_settings")
async def show_settings(callback: CallbackQuery):
    """Показать настройки"""
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка")
        return

    fund = get_or_create_reward_fund(user.id)

    text = (
        "⚙️ *Настройки ставок*\n\n"
        "_Нажми на ставку, чтобы изменить._\n\n"
        "Текущие ставки показаны на кнопках."
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_settings_keyboard(fund)
    )


@router.callback_query(F.data == "toggle_penalties")
async def toggle_penalties_handler(callback: CallbackQuery):
    """Переключить штрафы"""
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        return

    fund = get_or_create_reward_fund(user.id)
    new_state = not fund.penalties_enabled

    toggle_penalties(user.id, new_state)

    status = "включены" if new_state else "выключены"
    await callback.answer(f"Штрафы {status}")

    # Обновляем меню
    fund = get_or_create_reward_fund(user.id)
    await callback.message.edit_reply_markup(
        reply_markup=get_settings_keyboard(fund)
    )


@router.callback_query(F.data.startswith("rate_edit:"))
async def start_edit_rate(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование ставки"""
    rate_name = callback.data.split(":")[1]

    rate_labels = {
        "morning_kaizen": "Утренний кайдзен",
        "evening_reflection": "Вечерняя рефлексия",
        "task_done": "За задачу",
        "priority_task_bonus": "Бонус за главную задачу",
        "exercise": "За спорт",
        "eating_well": "За питание",
        "weekly_review": "За Weekly Review"
    }

    label = rate_labels.get(rate_name, rate_name)

    await state.set_state(RewardStates.editing_rate)
    await state.update_data(rate_name=rate_name)

    await callback.message.edit_text(
        f"⚙️ *Изменение ставки*\n\n"
        f"Ставка: {label}\n\n"
        "Введи новое значение в рублях:",
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )


@router.message(RewardStates.editing_rate)
async def process_edit_rate(message: Message, state: FSMContext):
    """Сохранить новую ставку"""
    try:
        new_rate = int(message.text.strip())
        if new_rate < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введи неотрицательное число")
        return

    data = await state.get_data()
    user = get_user_by_telegram_id(message.from_user.id)

    if user:
        update_reward_rates(user.id, **{data['rate_name']: new_rate})

    await state.clear()

    await message.answer(
        f"✅ Ставка обновлена: {new_rate}₽",
        reply_markup=get_rewards_main_menu(
            get_reward_balance_by_telegram_id(message.from_user.id),
            0
        )
    )
