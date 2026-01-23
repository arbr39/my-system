"""
Handler для напоминаний о задачах дня
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery

from src.database.crud import get_user_by_telegram_id
from src.database.crud_rewards import add_reward, get_reward_balance
from src.database.models import get_session, DailyEntry

router = Router()


@router.callback_query(F.data.startswith("daily_task_done:"))
async def mark_daily_task_done(callback: CallbackQuery):
    """
    Отметить задачу как выполненную из напоминания.
    Callback format: daily_task_done:{entry_id}:{task_num}
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
            description=f"Задача {task_num}: {task_text[:50]}",
            daily_entry_id=entry.id
        )

        # Получить новый баланс
        balance = get_reward_balance(user.id)

        # Формируем ответ
        priority_msg = "\n⭐ *Главная задача дня!* +50₽ бонус" if is_priority else ""

        success_text = (
            f"🎉 *Отлично!*\n\n"
            f"✅ {task_text}\n\n"
            f"💰 +{total_reward}₽ за выполнение!{priority_msg}\n"
            f"📊 Баланс: {balance}₽"
        )

        # Проверить, все ли задачи выполнены
        tasks = [
            (1, entry.task_1, entry.task_1_done),
            (2, entry.task_2, entry.task_2_done),
            (3, entry.task_3, entry.task_3_done)
        ]

        completed_count = sum(1 for _, _, done in tasks if done)
        total_count = sum(1 for _, text, _ in tasks if text)

        if completed_count == total_count:
            success_text += "\n\n🌟 *Все задачи выполнены! Отличная работа!*"

        await callback.message.edit_text(
            success_text,
            parse_mode="Markdown"
        )
        await callback.answer("Награда начислена!")

    except Exception as e:
        print(f"Error marking task done: {e}")
        await callback.answer("Произошла ошибка")
    finally:
        session.close()
