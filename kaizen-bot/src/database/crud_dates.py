"""
CRUD операции для важных дат и напоминаний

Функционал:
- Хранение дней рождений, годовщин, событий
- Напоминания за N дней и в сам день
- Дедупликация напоминаний по году
"""
from datetime import datetime, date, timedelta
from src.database.models import ImportantDate, DateReminder, User, get_session


# Семейные дни рождения из my_standart.rst
FAMILY_BIRTHDAYS = [
    {"name": "Папа", "day": 25, "month": 9},
    {"name": "Мама", "day": 15, "month": 7},
    {"name": "Анна", "day": 17, "month": 9},
    {"name": "Арон", "day": 8, "month": 4},
    {"name": "Амелия", "day": 6, "month": 11},
    {"name": "Амир", "day": 30, "month": 5},
]


# ============ ИНИЦИАЛИЗАЦИЯ ============

def init_family_birthdays(user_id: int):
    """Инициализация семейных дней рождений для пользователя"""
    session = get_session()
    try:
        existing = session.query(ImportantDate).filter(
            ImportantDate.user_id == user_id
        ).count()

        if existing == 0:
            for birthday in FAMILY_BIRTHDAYS:
                date_obj = ImportantDate(
                    user_id=user_id,
                    day=birthday["day"],
                    month=birthday["month"],
                    date_type="birthday",
                    name=birthday["name"],
                    remind_days_before=1,
                    remind_on_day=True
                )
                session.add(date_obj)
            session.commit()
            print(f"[INIT] Added {len(FAMILY_BIRTHDAYS)} family birthdays for user {user_id}")
    finally:
        session.close()


# ============ CRUD ОПЕРАЦИИ ============

def create_important_date(
    user_id: int,
    name: str,
    day: int,
    month: int,
    year: int = None,
    date_type: str = "birthday",
    description: str = None,
    remind_days_before: int = 1,
    remind_on_day: bool = True
) -> ImportantDate:
    """Создать важную дату"""
    session = get_session()
    try:
        date_obj = ImportantDate(
            user_id=user_id,
            name=name,
            day=day,
            month=month,
            year=year,
            date_type=date_type,
            description=description,
            remind_days_before=remind_days_before,
            remind_on_day=remind_on_day
        )
        session.add(date_obj)
        session.commit()
        session.refresh(date_obj)
        return date_obj
    finally:
        session.close()


def get_user_dates(user_id: int, active_only: bool = True) -> list[ImportantDate]:
    """Получить все даты пользователя"""
    session = get_session()
    try:
        query = session.query(ImportantDate).filter(
            ImportantDate.user_id == user_id
        )
        if active_only:
            query = query.filter(ImportantDate.is_active == True)

        return query.order_by(
            ImportantDate.month,
            ImportantDate.day
        ).all()
    finally:
        session.close()


def get_important_date(date_id: int) -> ImportantDate | None:
    """Получить дату по ID"""
    session = get_session()
    try:
        return session.query(ImportantDate).filter(
            ImportantDate.id == date_id
        ).first()
    finally:
        session.close()


def update_important_date(
    date_id: int,
    name: str = None,
    day: int = None,
    month: int = None,
    remind_days_before: int = None,
    remind_on_day: bool = None
) -> ImportantDate | None:
    """Обновить дату"""
    session = get_session()
    try:
        date_obj = session.query(ImportantDate).filter(
            ImportantDate.id == date_id
        ).first()

        if date_obj:
            if name is not None:
                date_obj.name = name
            if day is not None:
                date_obj.day = day
            if month is not None:
                date_obj.month = month
            if remind_days_before is not None:
                date_obj.remind_days_before = remind_days_before
            if remind_on_day is not None:
                date_obj.remind_on_day = remind_on_day
            session.commit()
            session.refresh(date_obj)

        return date_obj
    finally:
        session.close()


def delete_important_date(date_id: int) -> bool:
    """Soft delete даты"""
    session = get_session()
    try:
        date_obj = session.query(ImportantDate).filter(
            ImportantDate.id == date_id
        ).first()

        if date_obj:
            date_obj.is_active = False
            session.commit()
            return True
        return False
    finally:
        session.close()


# ============ НАПОМИНАНИЯ ============

def get_dates_for_reminder(days_ahead: int = 0) -> list[tuple]:
    """
    Получить даты для напоминаний на определённый день.

    Args:
        days_ahead: 0 = сегодня, 1 = завтра и т.д.

    Returns:
        list[(User, ImportantDate)] - пары пользователь + дата
    """
    session = get_session()
    try:
        today = date.today()
        target_date = today + timedelta(days=days_ahead)

        # Ищем даты на target_date
        dates = session.query(ImportantDate).filter(
            ImportantDate.is_active == True,
            ImportantDate.day == target_date.day,
            ImportantDate.month == target_date.month
        ).all()

        result = []
        for d in dates:
            # Проверяем, нужно ли напоминание
            should_remind = False
            if days_ahead == 0 and d.remind_on_day:
                should_remind = True
            elif days_ahead > 0 and days_ahead == d.remind_days_before:
                should_remind = True

            if should_remind:
                user = session.query(User).filter(User.id == d.user_id).first()
                if user:
                    result.append((user, d))

        return result
    finally:
        session.close()


def was_reminder_sent(date_id: int, reminder_type: str, year: int) -> bool:
    """Проверить, было ли отправлено напоминание в этом году"""
    session = get_session()
    try:
        return session.query(DateReminder).filter(
            DateReminder.important_date_id == date_id,
            DateReminder.reminder_type == reminder_type,
            DateReminder.year == year
        ).first() is not None
    finally:
        session.close()


def mark_reminder_sent(date_id: int, reminder_type: str, year: int):
    """Отметить, что напоминание отправлено"""
    session = get_session()
    try:
        reminder = DateReminder(
            important_date_id=date_id,
            reminder_type=reminder_type,
            year=year
        )
        session.add(reminder)
        session.commit()
    finally:
        session.close()


# ============ БЛИЖАЙШИЕ ДАТЫ ============

def get_upcoming_dates(user_id: int, days: int = 30) -> list[ImportantDate]:
    """
    Получить ближайшие даты за N дней.
    Сортирует по близости к текущей дате.
    """
    session = get_session()
    try:
        today = date.today()

        dates = session.query(ImportantDate).filter(
            ImportantDate.user_id == user_id,
            ImportantDate.is_active == True
        ).all()

        upcoming = []
        for d in dates:
            # Строим дату в этом году
            try:
                target = date(today.year, d.month, d.day)
            except ValueError:
                continue  # Невалидная дата (31 февраля и т.п.)

            # Если дата уже прошла, берём следующий год
            if target < today:
                try:
                    target = date(today.year + 1, d.month, d.day)
                except ValueError:
                    continue

            # Считаем дни до даты
            days_until = (target - today).days
            if 0 <= days_until <= days:
                upcoming.append((d, days_until))

        # Сортируем по близости
        upcoming.sort(key=lambda x: x[1])
        return [d for d, _ in upcoming]
    finally:
        session.close()


def get_todays_dates(user_id: int) -> list[ImportantDate]:
    """Получить даты на сегодня"""
    today = date.today()
    session = get_session()
    try:
        return session.query(ImportantDate).filter(
            ImportantDate.user_id == user_id,
            ImportantDate.is_active == True,
            ImportantDate.day == today.day,
            ImportantDate.month == today.month
        ).all()
    finally:
        session.close()


def count_user_dates(user_id: int) -> int:
    """Подсчитать количество дат пользователя"""
    session = get_session()
    try:
        return session.query(ImportantDate).filter(
            ImportantDate.user_id == user_id,
            ImportantDate.is_active == True
        ).count()
    finally:
        session.close()
