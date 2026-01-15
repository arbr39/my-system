"""Pytest fixtures for Kaizen Bot tests."""

import pytest
from datetime import date, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, User, DailyEntry, Goal, InboxItem, SomedayMaybe


@pytest.fixture
def engine():
    """In-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Database session for testing."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_user(session):
    """Create a sample user for testing."""
    user = User(
        telegram_id=123456789,
        username="testuser",
        first_name="Test"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def sample_daily_entry(session, sample_user):
    """Create a sample daily entry for testing."""
    entry = DailyEntry(
        user_id=sample_user.id,
        entry_date=date.today(),
        task_1="Task 1",
        task_2="Task 2",
        task_3="Task 3",
        morning_completed=True,
        morning_time=datetime.now()
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


@pytest.fixture
def week_entries(session, sample_user):
    """Create a week of daily entries for statistics testing."""
    entries = []
    for i in range(7):
        entry = DailyEntry(
            user_id=sample_user.id,
            entry_date=date.today() - timedelta(days=i),
            task_1=f"Day {i} Task 1",
            task_2=f"Day {i} Task 2",
            task_3=f"Day {i} Task 3",
            task_1_done=(i % 2 == 0),  # Alternating completion
            task_2_done=(i % 3 == 0),
            task_3_done=(i < 3),
            morning_completed=True,
            evening_completed=(i < 5),
            exercised=(i % 2 == 0),
            ate_well=(i < 4),
            wake_time="07:30" if i < 5 else None,
            sleep_time="23:00" if i < 5 else None,
        )
        session.add(entry)
        entries.append(entry)
    session.commit()
    return entries


@pytest.fixture
def sample_goals(session, sample_user):
    """Create sample goals for testing."""
    goals = [
        Goal(user_id=sample_user.id, title="Learn Python", status="active"),
        Goal(user_id=sample_user.id, title="Exercise daily", status="active"),
        Goal(user_id=sample_user.id, title="Old goal", status="completed"),
    ]
    for goal in goals:
        session.add(goal)
    session.commit()
    return goals


@pytest.fixture
def sample_inbox_items(session, sample_user):
    """Create sample inbox items for testing."""
    items = []
    for i in range(12):
        item = InboxItem(
            user_id=sample_user.id,
            text=f"Inbox item {i}" + ("x" * 50 if i == 0 else ""),
            energy_level=["high", "medium", "low"][i % 3],
            time_estimate=["5min", "15min", "30min", "1hour"][i % 4],
            status="pending" if i < 10 else "processed"
        )
        session.add(item)
        items.append(item)
    session.commit()
    return items


@pytest.fixture
def sample_someday_items(session, sample_user):
    """Create sample someday/maybe items for testing."""
    items = []
    for i in range(5):
        item = SomedayMaybe(
            user_id=sample_user.id,
            text=f"Someday item {i}"
        )
        session.add(item)
        items.append(item)
    session.commit()
    return items
