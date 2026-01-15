"""
CRUD операции для пользовательских задач с наградами (@whysasha методика)

Пользователь создаёт задачи (например, "Тренировка в зале") с произвольной наградой.
При выполнении задачи начисляется награда в фонд наград.
"""
from datetime import datetime, date
from src.database.models import (
    UserTask, UserTaskCompletion, User,
    get_session
)
from src.database.crud_rewards import add_reward


# ============ УПРАВЛЕНИЕ ЗАДАЧАМИ ============

def add_user_task(
    user_id: int,
    name: str,
    reward_amount: int,
    is_recurring: bool = True,
    category: str = None
) -> UserTask:
    """Создать новую пользовательскую задачу"""
    session = get_session()
    try:
        task = UserTask(
            user_id=user_id,
            name=name,
            reward_amount=reward_amount,
            is_recurring=is_recurring,
            category=category
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        return task
    finally:
        session.close()


def get_user_tasks(
    user_id: int,
    active_only: bool = True,
    category: str = None
) -> list[UserTask]:
    """Получить список задач пользователя"""
    session = get_session()
    try:
        query = session.query(UserTask).filter(UserTask.user_id == user_id)

        if active_only:
            query = query.filter(UserTask.is_active == True)

        if category:
            query = query.filter(UserTask.category == category)

        return query.order_by(UserTask.created_at.asc()).all()
    finally:
        session.close()


def get_user_task(task_id: int) -> UserTask | None:
    """Получить задачу по ID"""
    session = get_session()
    try:
        return session.query(UserTask).filter(UserTask.id == task_id).first()
    finally:
        session.close()


def update_user_task(
    task_id: int,
    name: str = None,
    reward_amount: int = None,
    category: str = None
) -> UserTask | None:
    """Обновить задачу"""
    session = get_session()
    try:
        task = session.query(UserTask).filter(UserTask.id == task_id).first()

        if task:
            if name is not None:
                task.name = name
            if reward_amount is not None:
                task.reward_amount = reward_amount
            if category is not None:
                task.category = category

            session.commit()
            session.refresh(task)

        return task
    finally:
        session.close()


def delete_user_task(task_id: int) -> bool:
    """Удалить задачу (soft delete)"""
    session = get_session()
    try:
        task = session.query(UserTask).filter(UserTask.id == task_id).first()

        if task:
            task.is_active = False
            session.commit()
            return True

        return False
    finally:
        session.close()


# ============ ВЫПОЛНЕНИЕ ЗАДАЧ ============

def complete_user_task(user_id: int, task_id: int) -> dict:
    """
    Отметить задачу как выполненную и начислить награду.

    Returns: {
        "success": bool,
        "message": str,
        "reward": int,
        "balance": int
    }
    """
    session = get_session()
    try:
        task = session.query(UserTask).filter(
            UserTask.id == task_id,
            UserTask.user_id == user_id,
            UserTask.is_active == True
        ).first()

        if not task:
            return {
                "success": False,
                "message": "Задача не найдена или неактивна",
                "reward": 0,
                "balance": 0
            }

        # Для одноразовых задач: проверить, не выполнена ли уже
        if not task.is_recurring and task.completed_once:
            return {
                "success": False,
                "message": "Задача уже выполнена",
                "reward": 0,
                "balance": 0
            }

        # Для повторяющихся задач: проверить, не выполнена ли уже сегодня
        if task.is_recurring:
            completions_today = get_task_completions_today(user_id, task_id)
            if completions_today > 0:
                return {
                    "success": False,
                    "message": "Задача уже выполнена сегодня",
                    "reward": 0,
                    "balance": 0
                }

        # Начислить награду
        reward_transaction = add_reward(
            user_id=user_id,
            amount=task.reward_amount,
            transaction_type="user_task_done",
            description=f"Задача: {task.name}"
        )

        # Создать запись о выполнении
        completion = UserTaskCompletion(
            task_id=task_id,
            reward_transaction_id=reward_transaction.id
        )
        session.add(completion)

        # Для одноразовых задач: пометить как выполненную и архивировать
        if not task.is_recurring:
            task.completed_once = True
            task.is_active = False

        session.commit()
        session.refresh(completion)

        # Получить новый баланс
        from src.database.crud_rewards import get_reward_balance
        new_balance = get_reward_balance(user_id)

        return {
            "success": True,
            "message": f"Отлично! +{task.reward_amount}₽ за {task.name}",
            "reward": task.reward_amount,
            "balance": new_balance
        }
    finally:
        session.close()


def get_task_completions_today(user_id: int, task_id: int) -> int:
    """Подсчёт выполнений задачи за сегодня"""
    session = get_session()
    try:
        task = session.query(UserTask).filter(
            UserTask.id == task_id,
            UserTask.user_id == user_id
        ).first()

        if not task:
            return 0

        today = date.today()
        count = session.query(UserTaskCompletion).filter(
            UserTaskCompletion.task_id == task_id,
            UserTaskCompletion.completion_date == today
        ).count()

        return count
    finally:
        session.close()


def get_task_history(task_id: int, limit: int = 10) -> list[UserTaskCompletion]:
    """История выполнений задачи"""
    session = get_session()
    try:
        return session.query(UserTaskCompletion).filter(
            UserTaskCompletion.task_id == task_id
        ).order_by(
            UserTaskCompletion.completed_at.desc()
        ).limit(limit).all()
    finally:
        session.close()


def get_user_stats_today(user_id: int) -> dict:
    """
    Статистика выполненных задач за сегодня.

    Returns: {
        "tasks_completed": int,
        "total_earned": int
    }
    """
    session = get_session()
    try:
        today = date.today()

        # Получить все задачи пользователя
        tasks = session.query(UserTask).filter(
            UserTask.user_id == user_id
        ).all()

        task_ids = [t.id for t in tasks]

        if not task_ids:
            return {
                "tasks_completed": 0,
                "total_earned": 0
            }

        # Получить выполнения за сегодня
        completions = session.query(UserTaskCompletion).filter(
            UserTaskCompletion.task_id.in_(task_ids),
            UserTaskCompletion.completion_date == today
        ).all()

        # Подсчитать заработанное
        total_earned = 0
        for completion in completions:
            task = session.query(UserTask).filter(
                UserTask.id == completion.task_id
            ).first()
            if task:
                total_earned += task.reward_amount

        return {
            "tasks_completed": len(completions),
            "total_earned": total_earned
        }
    finally:
        session.close()
