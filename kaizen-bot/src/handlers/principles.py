"""
Handler для ежемесячной оценки 25 принципов жизни

FSM Flow (по 5 принципов в день):
- День 1: принципы 1-5
- День 2: принципы 6-10
- День 3: принципы 11-15
- День 4: принципы 16-20
- День 5: принципы 21-25 → итоговый отчёт + награда
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.database.crud import get_user_by_telegram_id
from src.database.crud_principles import (
    get_all_principles, get_principles_for_day,
    get_or_create_monthly_assessment, get_current_assessment,
    get_last_completed_assessment, advance_assessment_day,
    save_principle_rating, complete_assessment,
    get_problem_zones, get_success_zones, compare_with_previous,
    get_ratings_for_day, count_rated_principles, get_assessment_history
)
from src.database.crud_rewards import get_reward_balance
from src.keyboards.inline_principles import (
    get_principles_main_menu, get_rating_keyboard,
    get_day_complete_keyboard, get_assessment_results_keyboard,
    get_history_keyboard, get_detail_keyboard
)
from src.keyboards.inline import get_main_menu

router = Router()


class AssessmentStates(StatesGroup):
    """Состояния оценки принципов"""
    rating_principle = State()


# ============ КОМАНДЫ ============

@router.message(Command("principles"))
async def cmd_principles(message: Message, state: FSMContext):
    """Команда /principles - начать оценку"""
    await state.clear()

    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Сначала используй /start")
        return

    current = get_current_assessment(user.id)
    last = get_last_completed_assessment(user.id)

    text = (
        "📊 *Оценка принципов жизни*\n\n"
        "25 принципов из твоего стандарта.\n"
        "Оценка проходит по 5 принципов в день (5 дней).\n\n"
    )

    if current:
        rated = count_rated_principles(current.id)
        text += f"📝 *Текущая оценка:* День {current.current_day}/5\n"
        text += f"✅ Оценено: {rated}/25 принципов\n\n"

    if last:
        avg = last.average_score / 10 if last.average_score else 0
        month_names = ["", "января", "февраля", "марта", "апреля", "мая",
                       "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
        text += f"📜 Последняя оценка: {month_names[last.month]} — {avg:.1f}/10"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_principles_main_menu(has_active=current is not None)
    )


@router.callback_query(F.data == "principles_show")
async def show_principles_menu(callback: CallbackQuery, state: FSMContext):
    """Показать меню принципов"""
    await state.clear()

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка")
        return

    current = get_current_assessment(user.id)
    last = get_last_completed_assessment(user.id)

    text = "📊 *Оценка принципов жизни*\n\n"

    if current:
        rated = count_rated_principles(current.id)
        text += f"📝 День {current.current_day}/5 | Оценено: {rated}/25\n\n"

    if last:
        avg = last.average_score / 10 if last.average_score else 0
        text += f"Последняя средняя оценка: {avg:.1f}/10"

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_principles_main_menu(has_active=current is not None)
    )
    await callback.answer()


# ============ НАЧАЛО/ПРОДОЛЖЕНИЕ ОЦЕНКИ ============

@router.callback_query(F.data.in_({"principles_start", "principles_continue"}))
async def start_or_continue_assessment(callback: CallbackQuery, state: FSMContext):
    """Начать или продолжить оценку принципов"""
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка")
        return

    # Получаем или создаём assessment
    assessment = get_or_create_monthly_assessment(user.id)
    current_day = assessment.current_day

    # Получаем принципы для текущего дня
    principles = get_principles_for_day(current_day)
    if not principles:
        await callback.answer("Нет принципов")
        return

    # Получаем уже оценённые принципы
    existing_ratings = get_ratings_for_day(assessment.id, current_day)
    ratings_dict = {r.principle_id: r.score for r in existing_ratings}

    await state.update_data(
        user_id=user.id,
        assessment_id=assessment.id,
        current_day=current_day,
        principles=[{"id": p.id, "number": p.number, "text": p.text} for p in principles],
        current_index=0,
        ratings=ratings_dict
    )

    await state.set_state(AssessmentStates.rating_principle)
    await show_current_principle(callback.message, state)
    await callback.answer()


async def show_current_principle(message, state: FSMContext):
    """Показать текущий принцип для оценки"""
    data = await state.get_data()
    principles = data.get("principles", [])
    current_index = data.get("current_index", 0)
    current_day = data.get("current_day", 1)
    ratings = data.get("ratings", {})

    if current_index >= len(principles):
        # Все принципы дня оценены
        await finish_day(message, state)
        return

    principle = principles[current_index]
    principle_id = principle["id"]
    current_rating = ratings.get(principle_id)

    # Глобальный номер принципа
    global_num = (current_day - 1) * 5 + current_index + 1

    text = (
        f"📊 *День {current_day}/5 — Принцип {current_index + 1}/5*\n"
        f"_(#{global_num} из 25)_\n\n"
        f"_{principle['text']}_\n\n"
        "Оцени по шкале 1-10:"
    )

    if current_rating:
        text += f"\n\n_Текущая оценка: {current_rating}_"

    try:
        await message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_rating_keyboard(
                principle_id,
                current_index,
                len(principles),
                current_rating
            )
        )
    except Exception:
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=get_rating_keyboard(
                principle_id,
                current_index,
                len(principles),
                current_rating
            )
        )


# ============ ОЦЕНКА ============

@router.callback_query(F.data.startswith("principle_rate:"), AssessmentStates.rating_principle)
async def rate_principle(callback: CallbackQuery, state: FSMContext):
    """Оценить принцип"""
    parts = callback.data.split(":")
    principle_id = int(parts[1])
    score = int(parts[2])

    data = await state.get_data()
    ratings = data.get("ratings", {})
    ratings[principle_id] = score

    # Сохраняем в БД
    save_principle_rating(data["assessment_id"], principle_id, score)

    # Обновляем state и переходим к следующему
    await state.update_data(
        ratings=ratings,
        current_index=data["current_index"] + 1
    )

    await callback.answer(f"Оценка: {score}/10")
    await show_current_principle(callback.message, state)


@router.callback_query(F.data == "principle_prev", AssessmentStates.rating_principle)
async def prev_principle(callback: CallbackQuery, state: FSMContext):
    """Вернуться к предыдущему принципу"""
    data = await state.get_data()
    current_index = data.get("current_index", 0)

    if current_index > 0:
        await state.update_data(current_index=current_index - 1)
        await show_current_principle(callback.message, state)

    await callback.answer()


@router.callback_query(F.data == "principle_skip", AssessmentStates.rating_principle)
async def skip_principle(callback: CallbackQuery, state: FSMContext):
    """Пропустить принцип"""
    data = await state.get_data()
    await state.update_data(current_index=data["current_index"] + 1)
    await show_current_principle(callback.message, state)
    await callback.answer("Пропущено")


@router.callback_query(F.data == "principles_cancel")
async def cancel_assessment(callback: CallbackQuery, state: FSMContext):
    """Отмена оценки (прогресс сохраняется)"""
    await state.clear()

    await callback.message.edit_text(
        "📊 Оценка приостановлена.\n"
        "Прогресс сохранён — можешь продолжить позже.",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )
    await callback.answer()


# ============ ЗАВЕРШЕНИЕ ДНЯ ============

async def finish_day(message, state: FSMContext):
    """Завершение дня оценки"""
    data = await state.get_data()
    current_day = data.get("current_day", 1)
    assessment_id = data.get("assessment_id")
    user_id = data.get("user_id")

    is_last_day = current_day >= 5

    if is_last_day:
        # Завершаем всю оценку
        await finish_assessment(message, state)
    else:
        # Переходим к следующему дню
        advance_assessment_day(assessment_id)

        rated = count_rated_principles(assessment_id)

        text = (
            f"✅ *День {current_day} завершён!*\n\n"
            f"Оценено: {rated}/25 принципов\n\n"
            f"Завтра продолжим с принципами {current_day * 5 + 1}-{(current_day + 1) * 5}."
        )

        await state.clear()

        try:
            await message.edit_text(
                text,
                parse_mode="Markdown",
                reply_markup=get_day_complete_keyboard(current_day, is_last_day=False)
            )
        except Exception:
            await message.answer(
                text,
                parse_mode="Markdown",
                reply_markup=get_day_complete_keyboard(current_day, is_last_day=False)
            )


async def finish_assessment(message, state: FSMContext):
    """Завершение всей оценки и показ результатов"""
    data = await state.get_data()
    assessment_id = data.get("assessment_id")
    user_id = data.get("user_id")

    # Завершаем assessment
    assessment = complete_assessment(assessment_id)

    # Награда за оценку
    from src.database.crud_rewards import grant_monthly_assessment_reward
    reward_amount = grant_monthly_assessment_reward(user_id, assessment_id)

    # Получаем аналитику
    problem_zones = get_problem_zones(assessment_id)
    success_zones = get_success_zones(assessment_id)
    comparison = compare_with_previous(user_id, assessment_id)

    avg = assessment.average_score / 10 if assessment.average_score else 0

    text = (
        "🎉 *Оценка завершена!*\n\n"
        f"📊 Средняя оценка: *{avg:.1f}/10*\n"
    )

    # Сравнение с прошлым месяцем
    if comparison.get("has_previous"):
        diff = comparison["diff"]
        if diff > 0:
            text += f"📈 Прогресс: +{diff:.1f} к прошлому месяцу\n"
        elif diff < 0:
            text += f"📉 Изменение: {diff:.1f} к прошлому месяцу\n"
        else:
            text += "➡️ Без изменений к прошлому месяцу\n"

    # Проблемные зоны (кратко)
    if problem_zones:
        text += "\n🔴 *Проблемные зоны (< 7):*\n"
        for zone in problem_zones[:3]:
            short_text = zone['text'][:35] + "..." if len(zone['text']) > 35 else zone['text']
            text += f"  • #{zone['number']}: {zone['score']}/10\n"

    # Успешные зоны (кратко)
    if success_zones:
        text += "\n🟢 *Сильные стороны (9-10):*\n"
        for zone in success_zones[:3]:
            text += f"  • #{zone['number']}: {zone['score']}/10\n"

    # Награда
    if reward_amount > 0:
        balance = get_reward_balance(user_id)
        text += f"\n\n💰 *+{reward_amount}₽* за оценку принципов!"
        text += f"\n📊 Баланс: {balance}₽"

    await state.clear()

    try:
        await message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_assessment_results_keyboard(assessment_id)
        )
    except Exception:
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=get_assessment_results_keyboard(assessment_id)
        )


# ============ ИСТОРИЯ И ДЕТАЛИ ============

@router.callback_query(F.data == "principles_history")
async def show_history(callback: CallbackQuery):
    """Показать историю оценок"""
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка")
        return

    assessments = get_assessment_history(user.id, limit=6)

    if not assessments:
        text = "📜 *История оценок*\n\nПока нет завершённых оценок."
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_principles_main_menu()
        )
    else:
        text = "📜 *История оценок*\n\nВыбери месяц для просмотра:"
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_history_keyboard(assessments)
        )

    await callback.answer()


@router.callback_query(F.data.startswith("principles_detail:"))
async def show_detail(callback: CallbackQuery):
    """Показать детали оценки"""
    assessment_id = int(callback.data.split(":")[1])

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка")
        return

    from src.database.crud_principles import get_all_ratings
    from src.database.models import MonthlyAssessment, get_session

    session = get_session()
    try:
        assessment = session.query(MonthlyAssessment).filter(
            MonthlyAssessment.id == assessment_id
        ).first()

        if not assessment:
            await callback.answer("Оценка не найдена")
            return

        avg = assessment.average_score / 10 if assessment.average_score else 0

        month_names = ["", "Январь", "Февраль", "Март", "Апрель", "Май",
                       "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

        text = (
            f"📊 *{month_names[assessment.month]} {assessment.year}*\n\n"
            f"Средняя оценка: *{avg:.1f}/10*\n"
        )

        ratings = get_all_ratings(assessment_id)
        if ratings:
            text += f"Оценено принципов: {len(ratings)}/25\n"

    finally:
        session.close()

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_detail_keyboard(assessment_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("principles_problems:"))
async def show_problems(callback: CallbackQuery):
    """Показать проблемные зоны"""
    assessment_id = int(callback.data.split(":")[1])

    problems = get_problem_zones(assessment_id)

    if problems:
        text = "🔴 *Проблемные зоны (< 7):*\n\n"
        for zone in problems:
            text += f"*#{zone['number']}* ({zone['score']}/10)\n"
            text += f"_{zone['text']}_\n\n"
    else:
        text = "🟢 Отлично! Нет проблемных зон."

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_detail_keyboard(assessment_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("principles_success:"))
async def show_success(callback: CallbackQuery):
    """Показать сильные стороны"""
    assessment_id = int(callback.data.split(":")[1])

    success = get_success_zones(assessment_id)

    if success:
        text = "🟢 *Сильные стороны (9-10):*\n\n"
        for zone in success:
            text += f"*#{zone['number']}* ({zone['score']}/10)\n"
            text += f"_{zone['text']}_\n\n"
    else:
        text = "📊 Пока нет принципов с оценкой 9-10."

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_detail_keyboard(assessment_id)
    )
    await callback.answer()
