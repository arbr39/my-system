from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, Boolean, Date, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from src.config import DATABASE_PATH

Base = declarative_base()


class User(Base):
    """Пользователь бота"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    timezone = Column(String(50), default="Europe/Moscow")
    morning_hour = Column(Integer, default=7)
    morning_minute = Column(Integer, default=0)
    evening_hour = Column(Integer, default=22)
    evening_minute = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Google Calendar интеграция
    google_refresh_token_encrypted = Column(Text)  # Зашифрованный refresh token
    google_calendar_id = Column(String(255), default="primary")  # ID календаря
    calendar_sync_enabled = Column(Boolean, default=False)
    calendar_last_sync = Column(DateTime)  # Время последней синхронизации

    # Настройки напоминаний о событиях календаря
    reminder_minutes_before = Column(Integer, default=15)  # За сколько минут напоминать (15/30/60)
    quiet_hours_start = Column(Integer, default=23)  # Начало тихих часов (0-23)
    quiet_hours_end = Column(Integer, default=7)  # Конец тихих часов (0-23)
    event_reminders_enabled = Column(Boolean, default=True)  # Напоминания о событиях включены

    # Настройки напоминаний о задачах дня
    task_reminders_enabled = Column(Boolean, default=True)
    task_reminder_hour = Column(Integer, default=14)
    task_reminder_minute = Column(Integer, default=0)

    # Отношения
    daily_entries = relationship("DailyEntry", back_populates="user")
    goals = relationship("Goal", back_populates="user")
    inbox_items = relationship("InboxItem", back_populates="user")
    someday_items = relationship("SomedayMaybe", back_populates="user")
    weekly_reviews = relationship("WeeklyReview", back_populates="user")
    reward_fund = relationship("RewardFund", back_populates="user", uselist=False)
    monthly_assessments = relationship("MonthlyAssessment", back_populates="user")
    important_dates = relationship("ImportantDate", back_populates="user")
    user_tasks = relationship("UserTask", back_populates="user")


class DailyEntry(Base):
    """Ежедневная запись (утро + вечер)"""
    __tablename__ = "daily_entries"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    entry_date = Column(Date, nullable=False)

    # Утренний кайдзен
    energy_plus = Column(Text)  # Что дало энергию вчера
    energy_minus = Column(Text)  # Что забрало энергию вчера
    task_1 = Column(String(500))
    task_2 = Column(String(500))
    task_3 = Column(String(500))
    priority_task = Column(Integer)  # 1, 2 или 3 - главная задача дня (GTD)
    morning_completed = Column(Boolean, default=False)
    morning_time = Column(DateTime)

    # Вечерняя рефлексия
    task_1_done = Column(Boolean, default=False)
    task_2_done = Column(Boolean, default=False)
    task_3_done = Column(Boolean, default=False)
    insight = Column(Text)  # Главный инсайт дня
    improve = Column(Text)  # Что улучшить завтра
    evening_completed = Column(Boolean, default=False)
    evening_time = Column(DateTime)

    # Трекер привычек
    # TODO: Добавить валидацию формата времени или использовать Time тип
    # TODO: Рассмотреть хранение как Integer (минуты с полуночи) для расчётов
    sleep_time = Column(String(10))      # "23:30" - во сколько лёг
    wake_time = Column(String(10))       # "07:15" - во сколько встал
    exercised = Column(Boolean)          # Занимался спортом?
    ate_well = Column(Boolean)           # Питание в порядке?

    # Google Calendar event IDs
    task_1_event_id = Column(String(255))  # ID события для task_1
    task_2_event_id = Column(String(255))  # ID события для task_2
    task_3_event_id = Column(String(255))  # ID события для task_3
    priority_event_id = Column(String(255))  # ID события для приоритетной задачи

    created_at = Column(DateTime, default=datetime.utcnow)

    # Отношения
    user = relationship("User", back_populates="daily_entries")


class Goal(Base):
    """Цели пользователя"""
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50))  # career, health, etc.
    status = Column(String(20), default="active")  # active, paused, completed
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="goals")


class Report(Base):
    """Баги, идеи и предложения по улучшению"""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    report_type = Column(String(20), nullable=False)  # bug, idea, improvement
    description = Column(Text, nullable=False)
    status = Column(String(20), default="new")  # new, in_progress, done, rejected
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class InboxItem(Base):
    """GTD Inbox - быстрый сбор задач и мыслей"""
    __tablename__ = "inbox_items"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)

    # Контексты (опционально)
    energy_level = Column(String(10))  # high, medium, low
    time_estimate = Column(String(10))  # 5min, 15min, 30min, 1hour

    # Дедлайн и Calendar sync
    deadline = Column(DateTime)  # Опциональный дедлайн
    google_event_id = Column(String(255))  # ID события в Google Calendar
    calendar_synced_at = Column(DateTime)  # Когда синхронизировано

    # Статус
    status = Column(String(20), default="pending")  # pending, processed, deleted
    processed_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="inbox_items")


class SomedayMaybe(Base):
    """Список 'Когда-нибудь/может быть' (GTD)"""
    __tablename__ = "someday_maybe"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)

    # Источник - из какого inbox пришло
    source_inbox_id = Column(Integer, ForeignKey("inbox_items.id"))

    # Для периодического ревью
    last_reviewed = Column(DateTime)
    review_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="someday_items")


class WeeklyReview(Base):
    """Еженедельный обзор (GTD Weekly Review)"""
    __tablename__ = "weekly_reviews"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Дата ревью (воскресенье)
    review_date = Column(Date, nullable=False)

    # Данные ревью
    inbox_processed = Column(Integer, default=0)  # Сколько обработано
    goals_reviewed = Column(Boolean, default=False)

    # Рефлексия
    week_wins = Column(Text)  # Победы недели
    week_learnings = Column(Text)  # Уроки недели
    week_plan = Column(Text)  # План на неделю

    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="weekly_reviews")


# ============ СИСТЕМА НАГРАД (@whysasha методика) ============

class RewardFund(Base):
    """Фонд наград пользователя - ядро системы мотивации"""
    __tablename__ = "reward_funds"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    # Баланс в рублях
    balance = Column(Integer, default=0)
    total_earned = Column(Integer, default=0)
    total_spent = Column(Integer, default=0)

    # Настройки
    is_active = Column(Boolean, default=True)
    penalties_enabled = Column(Boolean, default=False)  # Выключено по умолчанию

    # Настраиваемые ставки наград (в рублях)
    rate_morning_kaizen = Column(Integer, default=50)
    rate_evening_reflection = Column(Integer, default=50)
    rate_task_done = Column(Integer, default=20)
    rate_priority_task_bonus = Column(Integer, default=50)
    rate_exercise = Column(Integer, default=30)
    rate_eating_well = Column(Integer, default=20)
    rate_weekly_review = Column(Integer, default=100)
    rate_streak_bonus = Column(Integer, default=10)  # За каждый день стрика

    created_at = Column(DateTime, default=datetime.utcnow)

    # Отношения
    user = relationship("User", back_populates="reward_fund")
    transactions = relationship("RewardTransaction", back_populates="fund")
    reward_items = relationship("RewardItem", back_populates="fund")


class RewardTransaction(Base):
    """История транзакций фонда наград"""
    __tablename__ = "reward_transactions"

    id = Column(Integer, primary_key=True)
    fund_id = Column(Integer, ForeignKey("reward_funds.id"), nullable=False)

    # Сумма: положительная = заработано, отрицательная = потрачено
    amount = Column(Integer, nullable=False)

    # Тип транзакции
    transaction_type = Column(String(30), nullable=False)
    # Типы: morning_kaizen, evening_reflection, task_done, priority_task,
    #       exercise, eating_well, weekly_review, streak_bonus,
    #       reward_spent, penalty, manual_adjustment

    description = Column(String(255))

    # Связи (опционально)
    daily_entry_id = Column(Integer, ForeignKey("daily_entries.id"))
    weekly_review_id = Column(Integer, ForeignKey("weekly_reviews.id"))
    reward_item_id = Column(Integer, ForeignKey("reward_items.id"))
    inbox_item_id = Column(Integer, ForeignKey("inbox_items.id"))

    created_at = Column(DateTime, default=datetime.utcnow)

    # Отношения
    fund = relationship("RewardFund", back_populates="transactions")


class RewardItem(Base):
    """Награды пользователя - список того, на что можно потратить баллы"""
    __tablename__ = "reward_items"

    id = Column(Integer, primary_key=True)
    fund_id = Column(Integer, ForeignKey("reward_funds.id"), nullable=False)

    name = Column(String(100), nullable=False)  # "Кофе", "Ресторан"
    price = Column(Integer, nullable=False)  # Цена в рублях
    category = Column(String(50))  # Опционально: food, entertainment, self_care

    # Статистика использования
    times_purchased = Column(Integer, default=0)
    last_purchased = Column(DateTime)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Отношения
    fund = relationship("RewardFund", back_populates="reward_items")


# ============ СИСТЕМА ОЦЕНКИ ПРИНЦИПОВ ЖИЗНИ ============

class LifePrinciple(Base):
    """25 принципов жизни для ежемесячной оценки"""
    __tablename__ = "life_principles"

    id = Column(Integer, primary_key=True)
    number = Column(Integer, nullable=False)  # 1-25
    text = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)

    # Связь с оценками
    ratings = relationship("PrincipleRating", back_populates="principle")


class MonthlyAssessment(Base):
    """Ежемесячная оценка принципов (по 5 в день, 5 дней)"""
    __tablename__ = "monthly_assessments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Год и месяц оценки
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)  # 1-12

    # Прогресс (5 дней по 5 принципов)
    current_day = Column(Integer, default=1)  # 1-5

    # Агрегированные данные
    average_score = Column(Integer)  # 0-100 (умножено на 10 для точности)
    completed = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    # Отношения
    user = relationship("User", back_populates="monthly_assessments")
    ratings = relationship("PrincipleRating", back_populates="assessment")


class PrincipleRating(Base):
    """Оценка конкретного принципа"""
    __tablename__ = "principle_ratings"

    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("monthly_assessments.id"), nullable=False)
    principle_id = Column(Integer, ForeignKey("life_principles.id"), nullable=False)

    score = Column(Integer, nullable=False)  # 1-10

    created_at = Column(DateTime, default=datetime.utcnow)

    # Отношения
    assessment = relationship("MonthlyAssessment", back_populates="ratings")
    principle = relationship("LifePrinciple", back_populates="ratings")


# ============ ВАЖНЫЕ ДАТЫ И НАПОМИНАНИЯ ============

class ImportantDate(Base):
    """Важные даты (дни рождения, годовщины)"""
    __tablename__ = "important_dates"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Дата
    day = Column(Integer, nullable=False)    # 1-31
    month = Column(Integer, nullable=False)  # 1-12
    year = Column(Integer)                   # Опционально (год рождения для расчёта возраста)

    # Тип и описание
    date_type = Column(String(30), default="birthday")  # birthday, anniversary, custom
    name = Column(String(100), nullable=False)  # "Папа", "Мама", "Годовщина"
    description = Column(Text)

    # Напоминания
    remind_days_before = Column(Integer, default=1)  # За сколько дней напоминать
    remind_on_day = Column(Boolean, default=True)    # Напоминать в сам день

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Отношения
    user = relationship("User", back_populates="important_dates")
    reminders = relationship("DateReminder", back_populates="important_date")


class DateReminder(Base):
    """Отправленные напоминания о датах (для дедупликации)"""
    __tablename__ = "date_reminders"

    id = Column(Integer, primary_key=True)
    important_date_id = Column(Integer, ForeignKey("important_dates.id"), nullable=False)

    # Когда отправлено
    sent_at = Column(DateTime, default=datetime.utcnow)
    reminder_type = Column(String(20), nullable=False)  # "before", "on_day"
    year = Column(Integer, nullable=False)  # Год, за который отправлено (для годовой дедупликации)

    # Отношения
    important_date = relationship("ImportantDate", back_populates="reminders")


# ============ ПОЛЬЗОВАТЕЛЬСКИЕ ЗАДАЧИ С НАГРАДАМИ ============

class UserTask(Base):
    """Пользовательские задачи с наградами (@whysasha методика)"""
    __tablename__ = "user_tasks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Основная информация
    name = Column(String(200), nullable=False)
    reward_amount = Column(Integer, nullable=False)  # Сумма награды в рублях

    # Тип задачи
    is_recurring = Column(Boolean, default=True)  # True = повторяющаяся, False = одноразовая

    # Категория (опционально)
    category = Column(String(50))  # sport, learning, personal, work, etc.
    description = Column(Text)  # Опционально: ссылки, заметки

    # Статус
    is_active = Column(Boolean, default=True)  # False для архивных или удалённых
    completed_once = Column(Boolean, default=False)  # Для одноразовых задач

    # Google Calendar интеграция
    google_event_id = Column(String(255))  # ID события в Google Calendar
    calendar_time = Column(DateTime)  # Время события в календаре

    created_at = Column(DateTime, default=datetime.utcnow)

    # Отношения
    user = relationship("User")
    completions = relationship("UserTaskCompletion", back_populates="task")


class UserTaskCompletion(Base):
    """История выполнений пользовательских задач"""
    __tablename__ = "user_task_completions"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("user_tasks.id"), nullable=False)

    # Дата выполнения
    completed_at = Column(DateTime, default=datetime.utcnow)
    completion_date = Column(Date, default=date.today)  # Для подсчёта выполнений за день

    # Награда
    reward_transaction_id = Column(Integer, ForeignKey("reward_transactions.id"))

    # Отношения
    task = relationship("UserTask", back_populates="completions")


# ============ УМНЫЕ НАПОМИНАНИЯ И FOLLOW-UP ============

class CalendarEventReminder(Base):
    """Отслеживание напоминаний о событиях и follow-up"""
    __tablename__ = "calendar_event_reminders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Идентификация события
    google_event_id = Column(String(255), nullable=False)
    event_start = Column(DateTime, nullable=False)
    event_end = Column(DateTime)
    event_summary = Column(String(500))

    # Отслеживание напоминаний
    reminder_sent_at = Column(DateTime)  # Когда отправлено напоминание
    followup_sent_at = Column(DateTime)  # Когда отправлен follow-up
    followup_response = Column(Text)  # Action items от пользователя

    # Флаги исключений
    is_bot_created = Column(Boolean, default=False)  # Создано Kaizen Bot
    is_excluded = Column(Boolean, default=False)  # "focus", "обед" и т.д.

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class HabitCalendarEvent(Base):
    """Привычки в Google Calendar"""
    __tablename__ = "habit_calendar_events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Тип привычки
    habit_type = Column(String(30), nullable=False)  # "exercise", "eating"

    # Google Calendar событие
    google_event_id = Column(String(255))  # ID recurring события
    event_time = Column(String(10))  # "18:00" - время привычки

    # Статус
    is_active = Column(Boolean, default=True)
    last_completed_date = Column(Date)  # Последняя дата выполнения
    last_synced_at = Column(DateTime)  # Последняя синхронизация цвета

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


# Создание движка и сессии
engine = create_engine(f"sqlite:///{DATABASE_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)


def _get_column_type_sql(column):
    """Получить SQL тип колонки для ALTER TABLE"""
    from sqlalchemy import Integer, String, Text, Boolean, Date, DateTime

    col_type = type(column.type)
    if col_type == Integer:
        return "INTEGER"
    elif col_type == String:
        return f"VARCHAR({column.type.length or 255})"
    elif col_type == Text:
        return "TEXT"
    elif col_type == Boolean:
        return "BOOLEAN"
    elif col_type == Date:
        return "DATE"
    elif col_type == DateTime:
        return "DATETIME"
    else:
        return "TEXT"


def _auto_migrate():
    """Автоматическое добавление новых колонок в существующие таблицы"""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)

    for table_name, table in Base.metadata.tables.items():
        if not inspector.has_table(table_name):
            continue

        existing_columns = {col['name'] for col in inspector.get_columns(table_name)}
        model_columns = {col.name for col in table.columns}

        missing_columns = model_columns - existing_columns

        if missing_columns:
            with engine.connect() as conn:
                for col_name in missing_columns:
                    column = table.columns[col_name]
                    col_type = _get_column_type_sql(column)

                    sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"
                    conn.execute(text(sql))
                    print(f"[AUTO-MIGRATE] Added column: {table_name}.{col_name} ({col_type})")
                conn.commit()


def init_db():
    """Инициализация базы данных с автомиграцией"""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Сначала добавляем новые колонки в существующие таблицы
    if DATABASE_PATH.exists():
        _auto_migrate()

    # Затем создаём новые таблицы
    Base.metadata.create_all(engine)

    # Инициализация 25 принципов жизни
    from src.database.crud_principles import init_default_principles
    init_default_principles()


def get_session():
    """Получение сессии БД"""
    return SessionLocal()
