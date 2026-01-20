"""
CRUD операции для системы наград (@whysasha методика)

Принципы:
- Награда ТОЛЬКО за измеримый результат
- Больше результат = больше награда
- Награда сразу после достижения
- Анти-кортизол: празднуем победы, не стыдим за провалы
"""
from datetime import datetime, date, timedelta
from src.database.models import (
    RewardFund, RewardTransaction, RewardItem,
    User, DailyEntry, WeeklyReview,
    get_session
)


# ============ REWARD FUND ============

def get_or_create_reward_fund(user_id: int) -> RewardFund:
    """Получить или создать фонд наград для пользователя"""
    session = get_session()
    try:
        fund = session.query(RewardFund).filter(
            RewardFund.user_id == user_id
        ).first()

        if not fund:
            fund = RewardFund(user_id=user_id)
            session.add(fund)
            session.commit()
            session.refresh(fund)

        return fund
    finally:
        session.close()


def get_reward_fund_by_telegram_id(telegram_id: int) -> RewardFund | None:
    """Получить фонд наград по telegram_id"""
    session = get_session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return None

        fund = session.query(RewardFund).filter(
            RewardFund.user_id == user.id
        ).first()

        if not fund:
            fund = RewardFund(user_id=user.id)
            session.add(fund)
            session.commit()
            session.refresh(fund)

        return fund
    finally:
        session.close()


def get_reward_balance(user_id: int) -> int:
    """Получить текущий баланс"""
    fund = get_or_create_reward_fund(user_id)
    return fund.balance if fund else 0


def get_reward_balance_by_telegram_id(telegram_id: int) -> int:
    """Получить баланс по telegram_id"""
    fund = get_reward_fund_by_telegram_id(telegram_id)
    return fund.balance if fund else 0


def update_reward_rates(user_id: int, **rates) -> RewardFund:
    """Обновить ставки наград"""
    session = get_session()
    try:
        fund = session.query(RewardFund).filter(
            RewardFund.user_id == user_id
        ).first()

        if fund:
            for key, value in rates.items():
                if hasattr(fund, f"rate_{key}"):
                    setattr(fund, f"rate_{key}", value)
            session.commit()
            session.refresh(fund)

        return fund
    finally:
        session.close()


def toggle_penalties(user_id: int, enabled: bool) -> RewardFund:
    """Включить/выключить штрафы"""
    session = get_session()
    try:
        fund = session.query(RewardFund).filter(
            RewardFund.user_id == user_id
        ).first()

        if fund:
            fund.penalties_enabled = enabled
            session.commit()
            session.refresh(fund)

        return fund
    finally:
        session.close()


# ============ TRANSACTIONS ============

def add_reward(
    user_id: int,
    amount: int,
    transaction_type: str,
    description: str = None,
    daily_entry_id: int = None,
    weekly_review_id: int = None,
    reward_item_id: int = None,
    inbox_item_id: int = None
) -> RewardTransaction:
    """Добавить награду в фонд"""
    session = get_session()
    try:
        fund = session.query(RewardFund).filter(
            RewardFund.user_id == user_id
        ).first()

        if not fund:
            fund = RewardFund(user_id=user_id)
            session.add(fund)
            session.commit()
            session.refresh(fund)

        # Обновляем баланс
        fund.balance += amount
        fund.total_earned += amount

        # Создаём транзакцию
        transaction = RewardTransaction(
            fund_id=fund.id,
            amount=amount,
            transaction_type=transaction_type,
            description=description,
            daily_entry_id=daily_entry_id,
            weekly_review_id=weekly_review_id,
            reward_item_id=reward_item_id,
            inbox_item_id=inbox_item_id
        )
        session.add(transaction)
        session.commit()
        session.refresh(transaction)

        return transaction
    finally:
        session.close()


def spend_reward(user_id: int, reward_item_id: int) -> tuple[bool, str, int]:
    """
    Потратить баланс на награду.
    Returns: (success, message, new_balance)
    """
    session = get_session()
    try:
        fund = session.query(RewardFund).filter(
            RewardFund.user_id == user_id
        ).first()

        if not fund:
            return False, "Фонд наград не найден", 0

        item = session.query(RewardItem).filter(
            RewardItem.id == reward_item_id,
            RewardItem.fund_id == fund.id,
            RewardItem.is_active == True
        ).first()

        if not item:
            return False, "Награда не найдена", fund.balance

        if fund.balance < item.price:
            return False, f"Недостаточно средств (нужно {item.price}₽, есть {fund.balance}₽)", fund.balance

        # Списываем
        fund.balance -= item.price
        fund.total_spent += item.price

        # Обновляем статистику награды
        item.times_purchased += 1
        item.last_purchased = datetime.now()

        # Создаём транзакцию
        transaction = RewardTransaction(
            fund_id=fund.id,
            amount=-item.price,
            transaction_type="reward_spent",
            description=f"Потрачено на: {item.name}",
            reward_item_id=item.id
        )
        session.add(transaction)
        session.commit()

        return True, f"Отлично! Ты заслужил: {item.name}", fund.balance
    finally:
        session.close()


def get_recent_transactions(user_id: int, limit: int = 10) -> list[RewardTransaction]:
    """Получить последние транзакции"""
    session = get_session()
    try:
        fund = session.query(RewardFund).filter(
            RewardFund.user_id == user_id
        ).first()

        if not fund:
            return []

        return session.query(RewardTransaction).filter(
            RewardTransaction.fund_id == fund.id
        ).order_by(RewardTransaction.created_at.desc()).limit(limit).all()
    finally:
        session.close()


# ============ REWARD ITEMS ============

def add_reward_item(
    user_id: int,
    name: str,
    price: int,
    category: str = None
) -> RewardItem:
    """Добавить награду в список пользователя"""
    session = get_session()
    try:
        fund = get_or_create_reward_fund(user_id)

        # Получаем fund снова в этой сессии
        fund = session.query(RewardFund).filter(
            RewardFund.user_id == user_id
        ).first()

        item = RewardItem(
            fund_id=fund.id,
            name=name,
            price=price,
            category=category
        )
        session.add(item)
        session.commit()
        session.refresh(item)

        return item
    finally:
        session.close()


def get_reward_items(user_id: int, active_only: bool = True) -> list[RewardItem]:
    """Получить список наград пользователя"""
    session = get_session()
    try:
        fund = session.query(RewardFund).filter(
            RewardFund.user_id == user_id
        ).first()

        if not fund:
            return []

        query = session.query(RewardItem).filter(RewardItem.fund_id == fund.id)

        if active_only:
            query = query.filter(RewardItem.is_active == True)

        return query.order_by(RewardItem.price.asc()).all()
    finally:
        session.close()


def get_reward_item(item_id: int) -> RewardItem | None:
    """Получить награду по ID"""
    session = get_session()
    try:
        return session.query(RewardItem).filter(RewardItem.id == item_id).first()
    finally:
        session.close()


def update_reward_item(
    item_id: int,
    name: str = None,
    price: int = None,
    category: str = None
) -> RewardItem | None:
    """Обновить награду"""
    session = get_session()
    try:
        item = session.query(RewardItem).filter(RewardItem.id == item_id).first()

        if item:
            if name:
                item.name = name
            if price:
                item.price = price
            if category is not None:
                item.category = category
            session.commit()
            session.refresh(item)

        return item
    finally:
        session.close()


def delete_reward_item(item_id: int) -> bool:
    """Soft delete награды"""
    session = get_session()
    try:
        item = session.query(RewardItem).filter(RewardItem.id == item_id).first()

        if item:
            item.is_active = False
            session.commit()
            return True

        return False
    finally:
        session.close()


# ============ REWARD GRANTING LOGIC ============

def grant_morning_kaizen_reward(user_id: int, daily_entry_id: int = None) -> int:
    """
    Начислить награду за утренний кайдзен.
    Returns: сумма награды
    """
    fund = get_or_create_reward_fund(user_id)
    if not fund or not fund.is_active:
        return 0

    amount = fund.rate_morning_kaizen

    add_reward(
        user_id=user_id,
        amount=amount,
        transaction_type="morning_kaizen",
        description="Утренний кайдзен завершён",
        daily_entry_id=daily_entry_id
    )

    return amount


def grant_evening_reflection_reward(
    user_id: int,
    daily_entry_id: int = None,
    tasks_done: int = 0,
    priority_done: bool = False,
    exercised: bool = False,
    ate_well: bool = False
) -> dict:
    """
    Начислить награды за вечернюю рефлексию.
    Returns: breakdown словарь с детализацией
    """
    fund = get_or_create_reward_fund(user_id)
    if not fund or not fund.is_active:
        return {"total": 0}

    breakdown = {}
    total = 0

    # Награда за вечернюю рефлексию
    amount = fund.rate_evening_reflection
    add_reward(
        user_id=user_id,
        amount=amount,
        transaction_type="evening_reflection",
        description="Вечерняя рефлексия завершена",
        daily_entry_id=daily_entry_id
    )
    breakdown["evening"] = amount
    total += amount

    # Награда за каждую выполненную задачу
    if tasks_done > 0:
        tasks_amount = tasks_done * fund.rate_task_done
        add_reward(
            user_id=user_id,
            amount=tasks_amount,
            transaction_type="task_done",
            description=f"Выполнено задач: {tasks_done}",
            daily_entry_id=daily_entry_id
        )
        breakdown["tasks"] = tasks_amount
        total += tasks_amount

    # Бонус за приоритетную задачу
    if priority_done:
        add_reward(
            user_id=user_id,
            amount=fund.rate_priority_task_bonus,
            transaction_type="priority_task",
            description="Главная задача дня выполнена!",
            daily_entry_id=daily_entry_id
        )
        breakdown["priority"] = fund.rate_priority_task_bonus
        total += fund.rate_priority_task_bonus

    # Награда за спорт
    if exercised:
        add_reward(
            user_id=user_id,
            amount=fund.rate_exercise,
            transaction_type="exercise",
            description="Тренировка выполнена",
            daily_entry_id=daily_entry_id
        )
        breakdown["exercise"] = fund.rate_exercise
        total += fund.rate_exercise

    # Награда за питание
    if ate_well:
        add_reward(
            user_id=user_id,
            amount=fund.rate_eating_well,
            transaction_type="eating_well",
            description="Хорошее питание",
            daily_entry_id=daily_entry_id
        )
        breakdown["eating"] = fund.rate_eating_well
        total += fund.rate_eating_well

    breakdown["total"] = total
    return breakdown


def grant_weekly_review_reward(user_id: int, weekly_review_id: int = None) -> int:
    """
    Начислить награду за Weekly Review.
    Returns: сумма награды
    """
    fund = get_or_create_reward_fund(user_id)
    if not fund or not fund.is_active:
        return 0

    amount = fund.rate_weekly_review

    add_reward(
        user_id=user_id,
        amount=amount,
        transaction_type="weekly_review",
        description="Weekly Review завершён",
        weekly_review_id=weekly_review_id
    )

    return amount


def grant_monthly_assessment_reward(user_id: int, assessment_id: int = None) -> int:
    """
    Начислить награду за ежемесячную оценку принципов.
    Использует rate_weekly_review как базу (100₽), так как это тоже большой ритуал.
    Returns: сумма награды
    """
    fund = get_or_create_reward_fund(user_id)
    if not fund or not fund.is_active:
        return 0

    # Используем rate_weekly_review (100₽ по умолчанию)
    amount = fund.rate_weekly_review

    add_reward(
        user_id=user_id,
        amount=amount,
        transaction_type="monthly_assessment",
        description="Ежемесячная оценка принципов завершена"
    )

    return amount


def grant_inbox_task_reward(
    user_id: int,
    inbox_item_id: int,
    time_estimate: str | None,
    energy_level: str | None
) -> dict:
    """
    Начислить награду за выполнение inbox задачи.

    Награды соразмерны усилиям (@whysasha):
    - По времени: 5min=10₽, 15min=15₽, 30min=25₽, 1hour=40₽
    - Множитель энергии: low=×1.0, medium=×1.5, high=×2.0
    - Без контекста = 15₽

    Returns: {
        "base_amount": int,
        "energy_multiplier": float,
        "total": int,
        "description": str
    }
    """
    import math

    fund = get_or_create_reward_fund(user_id)
    if not fund or not fund.is_active:
        return {
            "base_amount": 0,
            "energy_multiplier": 1.0,
            "total": 0,
            "description": "Фонд неактивен"
        }

    # Базовая сумма по времени
    time_rewards = {
        "5min": 10,
        "15min": 15,
        "30min": 25,
        "1hour": 40
    }
    base_amount = time_rewards.get(time_estimate, 15)

    # Множитель по энергии
    energy_multipliers = {
        "low": 1.0,
        "medium": 1.5,
        "high": 2.0
    }
    multiplier = energy_multipliers.get(energy_level, 1.0)

    # Итоговая сумма (округление вверх)
    total = math.ceil(base_amount * multiplier)

    # Формирование description
    parts = []
    if time_estimate:
        parts.append(f"{time_estimate} ({base_amount}₽)")
    if energy_level and multiplier > 1.0:
        energy_emoji = {
            "high": "🔋🔋🔋",
            "medium": "🔋🔋",
            "low": "🔋"
        }
        parts.append(f"энергия {energy_emoji.get(energy_level, energy_level)} (×{multiplier})")

    description = " × ".join(parts) if parts else "Inbox задача выполнена"

    # Начисление награды
    add_reward(
        user_id=user_id,
        amount=total,
        transaction_type="inbox_task_done",
        description=description,
        inbox_item_id=inbox_item_id
    )

    return {
        "base_amount": base_amount,
        "energy_multiplier": multiplier,
        "total": total,
        "description": description
    }


def grant_streak_bonus(user_id: int, streak_days: int, streak_type: str) -> int:
    """
    Начислить бонус за стрик.
    streak_type: 'exercise', 'eating', 'morning', 'evening'
    Returns: сумма бонуса
    """
    fund = get_or_create_reward_fund(user_id)
    if not fund or not fund.is_active:
        return 0

    # Бонус растёт с длиной стрика
    amount = fund.rate_streak_bonus * streak_days

    add_reward(
        user_id=user_id,
        amount=amount,
        transaction_type="streak_bonus",
        description=f"Streak бонус ({streak_type}): {streak_days} дней подряд!"
    )

    return amount


# ============ STATISTICS ============

def get_reward_stats(user_id: int) -> dict:
    """Получить статистику наград"""
    session = get_session()
    try:
        fund = session.query(RewardFund).filter(
            RewardFund.user_id == user_id
        ).first()

        if not fund:
            return {
                "balance": 0,
                "total_earned": 0,
                "total_spent": 0,
                "transactions_count": 0
            }

        transactions_count = session.query(RewardTransaction).filter(
            RewardTransaction.fund_id == fund.id
        ).count()

        return {
            "balance": fund.balance,
            "total_earned": fund.total_earned,
            "total_spent": fund.total_spent,
            "transactions_count": transactions_count
        }
    finally:
        session.close()


def get_today_earnings(user_id: int) -> int:
    """Получить сумму заработанного сегодня"""
    session = get_session()
    try:
        fund = session.query(RewardFund).filter(
            RewardFund.user_id == user_id
        ).first()

        if not fund:
            return 0

        today = date.today()
        transactions = session.query(RewardTransaction).filter(
            RewardTransaction.fund_id == fund.id,
            RewardTransaction.amount > 0,
            RewardTransaction.created_at >= datetime.combine(today, datetime.min.time())
        ).all()

        return sum(t.amount for t in transactions)
    finally:
        session.close()


# Alias для универсального использования
grant_reward = add_reward
