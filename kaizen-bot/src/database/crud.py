from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from src.database.models import (
    User, DailyEntry, Goal, Report, InboxItem, SomedayMaybe, WeeklyReview, UserTask, get_session
)


def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None) -> User:
    """Получить или создать пользователя"""
    session = get_session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name
            )
            session.add(user)
            session.commit()
            session.refresh(user)
        return user
    finally:
        session.close()


def get_user_by_telegram_id(telegram_id: int) -> User:
    """Получить пользователя по Telegram ID"""
    session = get_session()
    try:
        return session.query(User).filter(User.telegram_id == telegram_id).first()
    finally:
        session.close()


def get_today_entry(user_id: int) -> DailyEntry:
    """Получить запись на сегодня"""
    session = get_session()
    try:
        return session.query(DailyEntry).filter(
            DailyEntry.user_id == user_id,
            DailyEntry.entry_date == date.today()
        ).first()
    finally:
        session.close()


def create_today_entry(user_id: int) -> DailyEntry:
    """Создать запись на сегодня"""
    session = get_session()
    try:
        entry = DailyEntry(
            user_id=user_id,
            entry_date=date.today()
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return entry
    finally:
        session.close()


def get_or_create_today_entry(user_id: int) -> DailyEntry:
    """Получить или создать запись на сегодня"""
    entry = get_today_entry(user_id)
    if not entry:
        entry = create_today_entry(user_id)
    return entry


def update_morning_entry(user_id: int, energy_plus: str, energy_minus: str,
                         task_1: str, task_2: str, task_3: str) -> DailyEntry:
    """Обновить утреннюю запись"""
    session = get_session()
    try:
        entry = session.query(DailyEntry).filter(
            DailyEntry.user_id == user_id,
            DailyEntry.entry_date == date.today()
        ).first()

        if not entry:
            entry = DailyEntry(user_id=user_id, entry_date=date.today())
            session.add(entry)

        entry.energy_plus = energy_plus
        entry.energy_minus = energy_minus
        entry.task_1 = task_1
        entry.task_2 = task_2
        entry.task_3 = task_3
        entry.morning_completed = True
        entry.morning_time = datetime.now()

        session.commit()
        session.refresh(entry)
        return entry
    finally:
        session.close()


def update_evening_entry(user_id: int, task_1_done: bool, task_2_done: bool,
                         task_3_done: bool, insight: str, improve: str) -> DailyEntry:
    """Обновить вечернюю запись"""
    session = get_session()
    try:
        entry = session.query(DailyEntry).filter(
            DailyEntry.user_id == user_id,
            DailyEntry.entry_date == date.today()
        ).first()

        if not entry:
            entry = DailyEntry(user_id=user_id, entry_date=date.today())
            session.add(entry)

        entry.task_1_done = task_1_done
        entry.task_2_done = task_2_done
        entry.task_3_done = task_3_done
        entry.insight = insight
        entry.improve = improve
        entry.evening_completed = True
        entry.evening_time = datetime.now()

        session.commit()
        session.refresh(entry)
        return entry
    finally:
        session.close()


def get_week_entries(user_id: int) -> list[DailyEntry]:
    """Получить записи за последнюю неделю"""
    session = get_session()
    try:
        # TODO: >= возвращает 8 дней (today - 7 days включительно), а не 7
        # Исправить на > week_ago или days=6
        week_ago = date.today() - timedelta(days=7)
        return session.query(DailyEntry).filter(
            DailyEntry.user_id == user_id,
            DailyEntry.entry_date >= week_ago
        ).order_by(DailyEntry.entry_date.desc()).all()
    finally:
        session.close()


def get_week_stats(user_id: int) -> dict:
    """Получить статистику за неделю"""
    entries = get_week_entries(user_id)

    total_tasks = 0
    completed_tasks = 0
    energy_plus_list = []
    energy_minus_list = []
    insights = []

    for entry in entries:
        if entry.task_1:
            total_tasks += 1
            if entry.task_1_done:
                completed_tasks += 1
        if entry.task_2:
            total_tasks += 1
            if entry.task_2_done:
                completed_tasks += 1
        if entry.task_3:
            total_tasks += 1
            if entry.task_3_done:
                completed_tasks += 1

        if entry.energy_plus:
            energy_plus_list.append(entry.energy_plus)
        if entry.energy_minus:
            energy_minus_list.append(entry.energy_minus)
        if entry.insight:
            insights.append(entry.insight)

    return {
        "total_entries": len(entries),
        "morning_completed": sum(1 for e in entries if e.morning_completed),
        "evening_completed": sum(1 for e in entries if e.evening_completed),
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
        "energy_plus": energy_plus_list,
        "energy_minus": energy_minus_list,
        "insights": insights
    }


def get_all_users() -> list[User]:
    """Получить всех пользователей"""
    session = get_session()
    try:
        return session.query(User).all()
    finally:
        session.close()


# Работа с целями
def create_goal(user_id: int, title: str, category: str = None, description: str = None) -> Goal:
    """Создать цель"""
    session = get_session()
    try:
        goal = Goal(
            user_id=user_id,
            title=title,
            category=category,
            description=description
        )
        session.add(goal)
        session.commit()
        session.refresh(goal)
        return goal
    finally:
        session.close()


def get_user_goals(user_id: int, status: str = "active") -> list[Goal]:
    """Получить цели пользователя"""
    session = get_session()
    try:
        query = session.query(Goal).filter(Goal.user_id == user_id)
        if status:
            query = query.filter(Goal.status == status)
        return query.all()
    finally:
        session.close()


# Работа с репортами
def create_report(user_id: int, report_type: str, description: str) -> Report:
    """Создать репорт (баг/идея/улучшение)"""
    session = get_session()
    try:
        report = Report(
            user_id=user_id,
            report_type=report_type,
            description=description
        )
        session.add(report)
        session.commit()
        session.refresh(report)
        return report
    finally:
        session.close()


def get_all_reports(status: str = None) -> list[Report]:
    """Получить все репорты"""
    session = get_session()
    try:
        query = session.query(Report).order_by(Report.created_at.desc())
        if status:
            query = query.filter(Report.status == status)
        return query.all()
    finally:
        session.close()


def get_report_by_id(report_id: int) -> Report:
    """Получить репорт по ID"""
    session = get_session()
    try:
        return session.query(Report).filter(Report.id == report_id).first()
    finally:
        session.close()


def update_report_status(report_id: int, status: str) -> Report:
    """Обновить статус репорта"""
    session = get_session()
    try:
        report = session.query(Report).filter(Report.id == report_id).first()
        if report:
            report.status = status
            session.commit()
            session.refresh(report)
        return report
    finally:
        session.close()


# Работа с настройками пользователя
def update_user_settings(
    telegram_id: int,
    morning_hour: int = None,
    morning_minute: int = None,
    evening_hour: int = None,
    evening_minute: int = None,
    timezone: str = None,
    task_reminders_enabled: bool = None,
    task_reminder_hour: int = None,
    task_reminder_minute: int = None
) -> User:
    """Обновить настройки пользователя"""
    session = get_session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            if morning_hour is not None:
                user.morning_hour = morning_hour
            if morning_minute is not None:
                user.morning_minute = morning_minute
            if evening_hour is not None:
                user.evening_hour = evening_hour
            if evening_minute is not None:
                user.evening_minute = evening_minute
            if timezone is not None:
                user.timezone = timezone
            if task_reminders_enabled is not None:
                user.task_reminders_enabled = task_reminders_enabled
            if task_reminder_hour is not None:
                user.task_reminder_hour = task_reminder_hour
            if task_reminder_minute is not None:
                user.task_reminder_minute = task_reminder_minute
            session.commit()
            session.refresh(user)
        return user
    finally:
        session.close()


# Работа с привычками
def update_habits(user_id: int, sleep_time: str = None, wake_time: str = None,
                  exercised: bool = None, ate_well: bool = None) -> DailyEntry:
    """Обновить данные о привычках за сегодня"""
    session = get_session()
    try:
        entry = session.query(DailyEntry).filter(
            DailyEntry.user_id == user_id,
            DailyEntry.entry_date == date.today()
        ).first()

        if not entry:
            entry = DailyEntry(user_id=user_id, entry_date=date.today())
            session.add(entry)

        if sleep_time is not None:
            entry.sleep_time = sleep_time
        if wake_time is not None:
            entry.wake_time = wake_time
        if exercised is not None:
            entry.exercised = exercised
        if ate_well is not None:
            entry.ate_well = ate_well

        session.commit()
        session.refresh(entry)
        return entry
    finally:
        session.close()


def get_habits_stats(user_id: int) -> dict:
    """Получить статистику привычек за последние 30 дней"""
    session = get_session()
    try:
        month_ago = date.today() - timedelta(days=30)
        entries = session.query(DailyEntry).filter(
            DailyEntry.user_id == user_id,
            DailyEntry.entry_date >= month_ago
        ).order_by(DailyEntry.entry_date.desc()).all()

        # Подсчёт streak для спорта
        exercise_streak = 0
        for entry in entries:
            if entry.exercised:
                exercise_streak += 1
            else:
                break

        # Подсчёт streak для питания
        eating_streak = 0
        for entry in entries:
            if entry.ate_well:
                eating_streak += 1
            else:
                break

        # Статистика за неделю
        week_ago = date.today() - timedelta(days=7)
        week_entries = [e for e in entries if e.entry_date >= week_ago]

        week_exercise = sum(1 for e in week_entries if e.exercised)
        week_eating = sum(1 for e in week_entries if e.ate_well)

        # Среднее время сна и подъёма
        wake_times = [e.wake_time for e in week_entries if e.wake_time]
        sleep_times = [e.sleep_time for e in week_entries if e.sleep_time]

        def avg_time(times: list) -> str:
            # TODO: Добавить валидацию времени (0 <= h < 24, 0 <= m < 60)
            # TODO: Обработка времени после полуночи (sleep_time "01:30" = 25:30?)
            # TODO: Заменить bare except на except ValueError
            if not times:
                return "-"
            total_minutes = 0
            valid_count = 0
            for t in times:
                try:
                    h, m = map(int, t.split(":"))
                    total_minutes += h * 60 + m
                    valid_count += 1
                except:
                    continue
            if valid_count == 0:
                return "-"
            avg_min = total_minutes // valid_count
            return f"{avg_min // 60:02d}:{avg_min % 60:02d}"

        return {
            "exercise_streak": exercise_streak,
            "eating_streak": eating_streak,
            "week_exercise": week_exercise,
            "week_eating": week_eating,
            "avg_wake": avg_time(wake_times),
            "avg_sleep": avg_time(sleep_times),
            "total_entries": len(entries)
        }
    finally:
        session.close()


# ============ GTD INBOX ============

def create_inbox_item(user_id: int, text: str,
                      energy_level: str = None,
                      time_estimate: str = None) -> InboxItem:
    """Добавить задачу в inbox"""
    session = get_session()
    try:
        item = InboxItem(
            user_id=user_id,
            text=text,
            energy_level=energy_level,
            time_estimate=time_estimate
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        return item
    finally:
        session.close()


def get_user_inbox(user_id: int, status: str = "pending") -> list[InboxItem]:
    """Получить inbox пользователя"""
    session = get_session()
    try:
        query = session.query(InboxItem).filter(InboxItem.user_id == user_id)
        if status:
            query = query.filter(InboxItem.status == status)
        return query.order_by(InboxItem.created_at.desc()).all()
    finally:
        session.close()


def get_inbox_item(item_id: int) -> InboxItem:
    """Получить элемент inbox по ID"""
    session = get_session()
    try:
        return session.query(InboxItem).filter(InboxItem.id == item_id).first()
    finally:
        session.close()


def update_inbox_item(item_id: int, status: str = None,
                      energy_level: str = None,
                      time_estimate: str = None) -> InboxItem:
    """Обновить элемент inbox"""
    session = get_session()
    try:
        item = session.query(InboxItem).filter(InboxItem.id == item_id).first()
        if item:
            if status is not None:
                item.status = status
                if status == "processed":
                    item.processed_at = datetime.now()
            if energy_level is not None:
                item.energy_level = energy_level
            if time_estimate is not None:
                item.time_estimate = time_estimate
            session.commit()
            session.refresh(item)
        return item
    finally:
        session.close()


def delete_inbox_item(item_id: int) -> bool:
    """Удалить элемент inbox"""
    session = get_session()
    try:
        item = session.query(InboxItem).filter(InboxItem.id == item_id).first()
        if item:
            item.status = "deleted"
            session.commit()
            return True
        return False
    finally:
        session.close()


def get_inbox_count(user_id: int) -> int:
    """Количество необработанных задач в inbox"""
    session = get_session()
    try:
        return session.query(InboxItem).filter(
            InboxItem.user_id == user_id,
            InboxItem.status == "pending"
        ).count()
    finally:
        session.close()


def get_inbox_by_context(user_id: int,
                         energy_level: str = None,
                         time_estimate: str = None) -> list[InboxItem]:
    """Фильтрация inbox по контексту"""
    session = get_session()
    try:
        query = session.query(InboxItem).filter(
            InboxItem.user_id == user_id,
            InboxItem.status == "pending"
        )
        if energy_level:
            query = query.filter(InboxItem.energy_level == energy_level)
        if time_estimate:
            query = query.filter(InboxItem.time_estimate == time_estimate)
        return query.order_by(InboxItem.created_at.desc()).all()
    finally:
        session.close()


# ============ GTD SOMEDAY/MAYBE ============

def create_someday_item(user_id: int, text: str,
                        source_inbox_id: int = None) -> SomedayMaybe:
    """Добавить в 'когда-нибудь'"""
    session = get_session()
    try:
        item = SomedayMaybe(
            user_id=user_id,
            text=text,
            source_inbox_id=source_inbox_id
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        return item
    finally:
        session.close()


def get_user_someday(user_id: int) -> list[SomedayMaybe]:
    """Получить список 'когда-нибудь'"""
    session = get_session()
    try:
        return session.query(SomedayMaybe).filter(
            SomedayMaybe.user_id == user_id
        ).order_by(SomedayMaybe.created_at.desc()).all()
    finally:
        session.close()


def get_someday_item(item_id: int) -> SomedayMaybe:
    """Получить элемент someday по ID"""
    session = get_session()
    try:
        return session.query(SomedayMaybe).filter(SomedayMaybe.id == item_id).first()
    finally:
        session.close()


def move_inbox_to_someday(inbox_id: int) -> SomedayMaybe:
    """Переместить из inbox в someday"""
    session = get_session()
    try:
        inbox_item = session.query(InboxItem).filter(InboxItem.id == inbox_id).first()
        if not inbox_item:
            return None

        someday_item = SomedayMaybe(
            user_id=inbox_item.user_id,
            text=inbox_item.text,
            source_inbox_id=inbox_item.id
        )
        session.add(someday_item)

        inbox_item.status = "processed"
        inbox_item.processed_at = datetime.now()

        session.commit()
        session.refresh(someday_item)
        return someday_item
    finally:
        session.close()


def move_someday_to_inbox(someday_id: int) -> InboxItem:
    """Вернуть из someday в inbox (активировать)"""
    session = get_session()
    try:
        someday_item = session.query(SomedayMaybe).filter(SomedayMaybe.id == someday_id).first()
        if not someday_item:
            return None

        inbox_item = InboxItem(
            user_id=someday_item.user_id,
            text=someday_item.text
        )
        session.add(inbox_item)
        session.delete(someday_item)

        session.commit()
        session.refresh(inbox_item)
        return inbox_item
    finally:
        session.close()


def delete_someday_item(someday_id: int) -> bool:
    """Удалить из someday"""
    session = get_session()
    try:
        item = session.query(SomedayMaybe).filter(SomedayMaybe.id == someday_id).first()
        if item:
            session.delete(item)
            session.commit()
            return True
        return False
    finally:
        session.close()


def mark_someday_reviewed(someday_id: int) -> SomedayMaybe:
    """Отметить что просмотрено в ревью"""
    session = get_session()
    try:
        item = session.query(SomedayMaybe).filter(SomedayMaybe.id == someday_id).first()
        if item:
            item.last_reviewed = datetime.now()
            item.review_count += 1
            session.commit()
            session.refresh(item)
        return item
    finally:
        session.close()


# ============ GTD WEEKLY REVIEW ============

def create_weekly_review(user_id: int, review_date: date = None) -> WeeklyReview:
    """Создать weekly review"""
    session = get_session()
    try:
        if review_date is None:
            review_date = date.today()
        review = WeeklyReview(
            user_id=user_id,
            review_date=review_date
        )
        session.add(review)
        session.commit()
        session.refresh(review)
        return review
    finally:
        session.close()


def get_or_create_weekly_review(user_id: int) -> WeeklyReview:
    """Получить или создать текущий weekly review"""
    session = get_session()
    try:
        today = date.today()
        # TODO: Использовать is_(False) вместо == False для SQLAlchemy
        review = session.query(WeeklyReview).filter(
            WeeklyReview.user_id == user_id,
            WeeklyReview.review_date == today,
            WeeklyReview.completed == False
        ).first()

        if not review:
            review = WeeklyReview(user_id=user_id, review_date=today)
            session.add(review)
            session.commit()
            session.refresh(review)
        return review
    finally:
        session.close()


def update_weekly_review(review_id: int, **kwargs) -> WeeklyReview:
    """Обновить данные review"""
    session = get_session()
    try:
        review = session.query(WeeklyReview).filter(WeeklyReview.id == review_id).first()
        if review:
            for key, value in kwargs.items():
                if hasattr(review, key):
                    setattr(review, key, value)
            session.commit()
            session.refresh(review)
        return review
    finally:
        session.close()


def complete_weekly_review(review_id: int) -> WeeklyReview:
    """Завершить weekly review"""
    session = get_session()
    try:
        review = session.query(WeeklyReview).filter(WeeklyReview.id == review_id).first()
        if review:
            review.completed = True
            session.commit()
            session.refresh(review)
        return review
    finally:
        session.close()


def get_last_weekly_review(user_id: int) -> WeeklyReview:
    """Последний завершённый review"""
    session = get_session()
    try:
        return session.query(WeeklyReview).filter(
            WeeklyReview.user_id == user_id,
            WeeklyReview.completed == True
        ).order_by(WeeklyReview.review_date.desc()).first()
    finally:
        session.close()


# ============ GTD PRIORITY TASK ============

def update_priority_task(user_id: int, priority_task: int) -> DailyEntry:
    """Установить приоритетную задачу дня (1, 2 или 3)"""
    session = get_session()
    try:
        entry = session.query(DailyEntry).filter(
            DailyEntry.user_id == user_id,
            DailyEntry.entry_date == date.today()
        ).first()

        if entry:
            entry.priority_task = priority_task
            session.commit()
            session.refresh(entry)
        return entry
    finally:
        session.close()


def get_priority_task_stats(user_id: int, days: int = 7) -> dict:
    """Статистика выполнения приоритетных задач"""
    session = get_session()
    try:
        # TODO: >= возвращает days+1 записей, использовать > для точного количества
        start_date = date.today() - timedelta(days=days)
        entries = session.query(DailyEntry).filter(
            DailyEntry.user_id == user_id,
            DailyEntry.entry_date >= start_date,
            DailyEntry.priority_task.isnot(None)
        ).all()

        total = len(entries)
        completed = 0

        for entry in entries:
            priority = entry.priority_task
            if priority == 1 and entry.task_1_done:
                completed += 1
            elif priority == 2 and entry.task_2_done:
                completed += 1
            elif priority == 3 and entry.task_3_done:
                completed += 1

        return {
            "total": total,
            "completed": completed,
            "rate": (completed / total * 100) if total > 0 else 0
        }
    finally:
        session.close()


# ============ GOOGLE CALENDAR ============

def update_user_google_token(telegram_id: int, encrypted_token: str) -> User:
    """Сохранить зашифрованный Google refresh token"""
    session = get_session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            user.google_refresh_token_encrypted = encrypted_token
            user.calendar_sync_enabled = True
            session.commit()
            session.refresh(user)
        return user
    finally:
        session.close()


def get_user_google_token(telegram_id: int) -> str | None:
    """Получить зашифрованный token"""
    session = get_session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        return user.google_refresh_token_encrypted if user else None
    finally:
        session.close()


def disable_calendar_sync(telegram_id: int) -> bool:
    """Отключить синхронизацию и удалить токен"""
    session = get_session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            user.google_refresh_token_encrypted = None
            user.calendar_sync_enabled = False
            user.calendar_last_sync = None
            session.commit()
            return True
        return False
    finally:
        session.close()


def get_users_with_calendar_enabled() -> list[User]:
    """Получить пользователей с включённой синхронизацией"""
    session = get_session()
    try:
        return session.query(User).filter(
            User.calendar_sync_enabled == True,
            User.google_refresh_token_encrypted.isnot(None)
        ).all()
    finally:
        session.close()


def update_calendar_last_sync(telegram_id: int) -> User:
    """Обновить время последней синхронизации"""
    session = get_session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            user.calendar_last_sync = datetime.now()
            session.commit()
            session.refresh(user)
        return user
    finally:
        session.close()


def update_inbox_item_deadline(item_id: int, deadline: datetime) -> InboxItem:
    """Добавить дедлайн к задаче"""
    session = get_session()
    try:
        item = session.query(InboxItem).filter(InboxItem.id == item_id).first()
        if item:
            item.deadline = deadline
            session.commit()
            session.refresh(item)
        return item
    finally:
        session.close()


def update_inbox_event_id(item_id: int, event_id: str) -> InboxItem:
    """Связать inbox item с Google Calendar event"""
    session = get_session()
    try:
        item = session.query(InboxItem).filter(InboxItem.id == item_id).first()
        if item:
            item.google_event_id = event_id
            item.calendar_synced_at = datetime.now()
            session.commit()
            session.refresh(item)
        return item
    finally:
        session.close()


def get_inbox_items_with_deadline(user_id: int) -> list[InboxItem]:
    """Получить задачи с дедлайном для синхронизации"""
    session = get_session()
    try:
        return session.query(InboxItem).filter(
            InboxItem.user_id == user_id,
            InboxItem.status == "pending",
            InboxItem.deadline.isnot(None)
        ).all()
    finally:
        session.close()


def update_daily_entry_event_ids(
    user_id: int,
    task_1_event_id: str = None,
    task_2_event_id: str = None,
    task_3_event_id: str = None,
    priority_event_id: str = None
) -> DailyEntry:
    """Сохранить event IDs для задач дня"""
    session = get_session()
    try:
        entry = session.query(DailyEntry).filter(
            DailyEntry.user_id == user_id,
            DailyEntry.entry_date == date.today()
        ).first()

        if entry:
            if task_1_event_id:
                entry.task_1_event_id = task_1_event_id
            if task_2_event_id:
                entry.task_2_event_id = task_2_event_id
            if task_3_event_id:
                entry.task_3_event_id = task_3_event_id
            if priority_event_id:
                entry.priority_event_id = priority_event_id
            session.commit()
            session.refresh(entry)
        return entry
    finally:
        session.close()


def get_inbox_item_by_event_id(event_id: str) -> InboxItem | None:
    """Найти inbox item по Google Calendar event ID"""
    session = get_session()
    try:
        return session.query(InboxItem).filter(
            InboxItem.google_event_id == event_id
        ).first()
    finally:
        session.close()


# ============ UNIFIED TASKS VIEW ============

def get_unified_tasks(user_id: int, filter_type: str = "all") -> dict:
    """
    Получить объединённый список задач для unified view.

    Args:
        user_id: ID пользователя
        filter_type: "all" | "user_tasks" | "inbox" | "daily"

    Returns: {
        "user_tasks": list[UserTask],
        "inbox_tasks": list[InboxItem],
        "daily_entry": DailyEntry | None
    }
    """
    from datetime import date
    session = get_session()
    try:
        result = {"user_tasks": [], "inbox_tasks": [], "daily_entry": None}

        # Daily entry за сегодня (всегда получаем для unified view)
        if filter_type in ["all", "daily"]:
            result["daily_entry"] = session.query(DailyEntry).filter(
                DailyEntry.user_id == user_id,
                DailyEntry.entry_date == date.today(),
                DailyEntry.morning_completed == True
            ).first()

        # User tasks (active only)
        if filter_type in ["all", "user_tasks"]:
            result["user_tasks"] = session.query(UserTask).filter(
                UserTask.user_id == user_id,
                UserTask.is_active == True
            ).all()

        # Inbox tasks (pending only)
        if filter_type in ["all", "inbox"]:
            result["inbox_tasks"] = session.query(InboxItem).filter(
                InboxItem.user_id == user_id,
                InboxItem.status == "pending"
            ).all()

        return result
    finally:
        session.close()
