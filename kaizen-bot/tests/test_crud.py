"""Tests for database CRUD operations."""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, User, DailyEntry, Goal, InboxItem, SomedayMaybe, WeeklyReview
from src.database import crud


class TestSessionFixture:
    """Fixture that patches get_session for all tests."""

    @pytest.fixture(autouse=True)
    def setup_db(self):
        """Set up in-memory database and patch get_session."""
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session_factory = Session

        # Patch get_session to return a new session each time
        with patch.object(crud, 'get_session', self.session_factory):
            yield

    def get_session(self):
        return self.session_factory()


class TestUserCRUD(TestSessionFixture):
    """Tests for user-related CRUD operations."""

    def test_get_or_create_user_creates_new(self):
        """Test creating a new user."""
        user = crud.get_or_create_user(
            telegram_id=123456,
            username="testuser",
            first_name="Test"
        )

        assert user is not None
        assert user.telegram_id == 123456
        assert user.username == "testuser"
        assert user.first_name == "Test"

    def test_get_or_create_user_returns_existing(self):
        """Test that get_or_create returns existing user."""
        user1 = crud.get_or_create_user(telegram_id=123456, username="user1")
        user2 = crud.get_or_create_user(telegram_id=123456, username="user2")

        assert user1.id == user2.id
        # Username should NOT be updated on get
        assert user1.username == "user1"

    def test_get_user_by_telegram_id(self):
        """Test fetching user by telegram ID."""
        crud.get_or_create_user(telegram_id=999999, username="findme")

        user = crud.get_user_by_telegram_id(999999)
        assert user is not None
        assert user.username == "findme"

    def test_get_user_by_telegram_id_not_found(self):
        """Test that non-existent user returns None."""
        user = crud.get_user_by_telegram_id(000000)
        assert user is None

    def test_get_all_users(self):
        """Test fetching all users."""
        crud.get_or_create_user(telegram_id=111, username="user1")
        crud.get_or_create_user(telegram_id=222, username="user2")
        crud.get_or_create_user(telegram_id=333, username="user3")

        users = crud.get_all_users()
        assert len(users) == 3


class TestDailyEntryCRUD(TestSessionFixture):
    """Tests for daily entry CRUD operations."""

    def test_create_today_entry(self):
        """Test creating today's entry."""
        user = crud.get_or_create_user(telegram_id=123)
        entry = crud.create_today_entry(user.id)

        assert entry is not None
        assert entry.user_id == user.id
        assert entry.entry_date == date.today()

    def test_get_today_entry(self):
        """Test fetching today's entry."""
        user = crud.get_or_create_user(telegram_id=123)
        crud.create_today_entry(user.id)

        entry = crud.get_today_entry(user.id)
        assert entry is not None
        assert entry.entry_date == date.today()

    def test_get_or_create_today_entry_creates(self):
        """Test get_or_create creates entry if not exists."""
        user = crud.get_or_create_user(telegram_id=123)

        entry = crud.get_or_create_today_entry(user.id)
        assert entry is not None
        assert entry.entry_date == date.today()

    def test_get_or_create_today_entry_gets_existing(self):
        """Test get_or_create returns existing entry."""
        user = crud.get_or_create_user(telegram_id=123)
        entry1 = crud.create_today_entry(user.id)
        entry2 = crud.get_or_create_today_entry(user.id)

        assert entry1.id == entry2.id

    def test_update_morning_entry(self):
        """Test updating morning entry."""
        user = crud.get_or_create_user(telegram_id=123)

        entry = crud.update_morning_entry(
            user_id=user.id,
            energy_plus="Good sleep",
            energy_minus="Too much coffee",
            task_1="Task 1",
            task_2="Task 2",
            task_3="Task 3"
        )

        assert entry.energy_plus == "Good sleep"
        assert entry.energy_minus == "Too much coffee"
        assert entry.task_1 == "Task 1"
        assert entry.task_2 == "Task 2"
        assert entry.task_3 == "Task 3"
        assert entry.morning_completed is True
        assert entry.morning_time is not None

    def test_update_evening_entry(self):
        """Test updating evening entry."""
        user = crud.get_or_create_user(telegram_id=123)
        crud.update_morning_entry(user.id, "", "", "Task 1", "Task 2", "Task 3")

        entry = crud.update_evening_entry(
            user_id=user.id,
            task_1_done=True,
            task_2_done=False,
            task_3_done=True,
            insight="Great day",
            improve="Wake up earlier"
        )

        assert entry.task_1_done is True
        assert entry.task_2_done is False
        assert entry.task_3_done is True
        assert entry.insight == "Great day"
        assert entry.improve == "Wake up earlier"
        assert entry.evening_completed is True


class TestWeekStatsCRUD(TestSessionFixture):
    """Tests for weekly statistics calculation."""

    def _create_week_entries(self, user_id):
        """Helper to create week of entries."""
        session = self.get_session()
        for i in range(7):
            entry = DailyEntry(
                user_id=user_id,
                entry_date=date.today() - timedelta(days=i),
                task_1=f"Task 1 day {i}",
                task_2=f"Task 2 day {i}" if i < 5 else None,
                task_3=f"Task 3 day {i}" if i < 3 else None,
                task_1_done=(i % 2 == 0),
                task_2_done=(i < 3),
                task_3_done=(i == 0),
                morning_completed=True,
                evening_completed=(i < 5),
                energy_plus=f"Energy {i}" if i < 3 else None,
                insight=f"Insight {i}" if i < 2 else None
            )
            session.add(entry)
        session.commit()
        session.close()

    def test_get_week_entries(self):
        """Test fetching week entries."""
        user = crud.get_or_create_user(telegram_id=123)
        self._create_week_entries(user.id)

        entries = crud.get_week_entries(user.id)
        assert len(entries) == 7

    def test_get_week_stats_calculates_completion_rate(self):
        """Test completion rate calculation."""
        user = crud.get_or_create_user(telegram_id=123)
        self._create_week_entries(user.id)

        stats = crud.get_week_stats(user.id)

        assert stats["total_entries"] == 7
        assert stats["morning_completed"] == 7
        assert stats["evening_completed"] == 5
        assert stats["total_tasks"] > 0
        assert stats["completed_tasks"] > 0
        assert 0 <= stats["completion_rate"] <= 100

    def test_get_week_stats_empty(self):
        """Test stats with no entries."""
        user = crud.get_or_create_user(telegram_id=123)

        stats = crud.get_week_stats(user.id)

        assert stats["total_entries"] == 0
        assert stats["completion_rate"] == 0

    def test_get_week_stats_collects_insights(self):
        """Test that insights are collected."""
        user = crud.get_or_create_user(telegram_id=123)
        self._create_week_entries(user.id)

        stats = crud.get_week_stats(user.id)

        assert len(stats["insights"]) == 2  # Only 2 days have insights


class TestGoalsCRUD(TestSessionFixture):
    """Tests for goal CRUD operations."""

    def test_create_goal(self):
        """Test creating a goal."""
        user = crud.get_or_create_user(telegram_id=123)

        goal = crud.create_goal(
            user_id=user.id,
            title="Learn Python",
            category="career",
            description="Master the language"
        )

        assert goal is not None
        assert goal.title == "Learn Python"
        assert goal.category == "career"
        assert goal.status == "active"

    def test_get_user_goals_filters_by_status(self):
        """Test filtering goals by status."""
        user = crud.get_or_create_user(telegram_id=123)
        crud.create_goal(user.id, "Active goal 1")
        crud.create_goal(user.id, "Active goal 2")

        # Create completed goal directly
        session = self.get_session()
        completed = Goal(user_id=user.id, title="Completed", status="completed")
        session.add(completed)
        session.commit()
        session.close()

        active_goals = crud.get_user_goals(user.id, status="active")
        all_goals = crud.get_user_goals(user.id, status=None)

        assert len(active_goals) == 2
        assert len(all_goals) == 3


class TestInboxCRUD(TestSessionFixture):
    """Tests for GTD inbox operations."""

    def test_create_inbox_item(self):
        """Test creating inbox item."""
        user = crud.get_or_create_user(telegram_id=123)

        item = crud.create_inbox_item(
            user_id=user.id,
            text="Buy groceries",
            energy_level="low",
            time_estimate="15min"
        )

        assert item is not None
        assert item.text == "Buy groceries"
        assert item.energy_level == "low"
        assert item.time_estimate == "15min"
        assert item.status == "pending"

    def test_get_user_inbox_filters_status(self):
        """Test filtering inbox by status."""
        user = crud.get_or_create_user(telegram_id=123)
        crud.create_inbox_item(user.id, "Item 1")
        crud.create_inbox_item(user.id, "Item 2")
        item3 = crud.create_inbox_item(user.id, "Item 3")
        crud.update_inbox_item(item3.id, status="processed")

        pending = crud.get_user_inbox(user.id, status="pending")
        processed = crud.get_user_inbox(user.id, status="processed")

        assert len(pending) == 2
        assert len(processed) == 1

    def test_get_inbox_count(self):
        """Test counting pending inbox items."""
        user = crud.get_or_create_user(telegram_id=123)
        crud.create_inbox_item(user.id, "Item 1")
        crud.create_inbox_item(user.id, "Item 2")
        item3 = crud.create_inbox_item(user.id, "Item 3")
        crud.update_inbox_item(item3.id, status="processed")

        count = crud.get_inbox_count(user.id)
        assert count == 2

    def test_delete_inbox_item_sets_status(self):
        """Test that delete sets status to 'deleted'."""
        user = crud.get_or_create_user(telegram_id=123)
        item = crud.create_inbox_item(user.id, "To delete")

        result = crud.delete_inbox_item(item.id)

        assert result is True
        updated = crud.get_inbox_item(item.id)
        assert updated.status == "deleted"

    def test_get_inbox_by_context(self):
        """Test filtering inbox by energy/time context."""
        user = crud.get_or_create_user(telegram_id=123)
        crud.create_inbox_item(user.id, "High energy task", energy_level="high")
        crud.create_inbox_item(user.id, "Low energy task", energy_level="low")
        crud.create_inbox_item(user.id, "Quick task", time_estimate="5min")

        high_energy = crud.get_inbox_by_context(user.id, energy_level="high")
        quick_tasks = crud.get_inbox_by_context(user.id, time_estimate="5min")

        assert len(high_energy) == 1
        assert len(quick_tasks) == 1


class TestSomedayCRUD(TestSessionFixture):
    """Tests for someday/maybe operations."""

    def test_create_someday_item(self):
        """Test creating someday item."""
        user = crud.get_or_create_user(telegram_id=123)

        item = crud.create_someday_item(user.id, "Learn guitar")

        assert item is not None
        assert item.text == "Learn guitar"
        assert item.review_count == 0

    def test_move_inbox_to_someday(self):
        """Test moving item from inbox to someday."""
        user = crud.get_or_create_user(telegram_id=123)
        inbox_item = crud.create_inbox_item(user.id, "Maybe later")

        someday_item = crud.move_inbox_to_someday(inbox_item.id)

        assert someday_item is not None
        assert someday_item.text == "Maybe later"
        assert someday_item.source_inbox_id == inbox_item.id

        # Check inbox item was processed
        updated_inbox = crud.get_inbox_item(inbox_item.id)
        assert updated_inbox.status == "processed"

    def test_move_someday_to_inbox(self):
        """Test activating someday item back to inbox."""
        user = crud.get_or_create_user(telegram_id=123)
        someday_item = crud.create_someday_item(user.id, "Time to do this")

        inbox_item = crud.move_someday_to_inbox(someday_item.id)

        assert inbox_item is not None
        assert inbox_item.text == "Time to do this"
        assert inbox_item.status == "pending"

        # Someday item should be deleted
        deleted = crud.get_someday_item(someday_item.id)
        assert deleted is None

    def test_mark_someday_reviewed(self):
        """Test marking someday item as reviewed."""
        user = crud.get_or_create_user(telegram_id=123)
        item = crud.create_someday_item(user.id, "Review me")

        crud.mark_someday_reviewed(item.id)
        crud.mark_someday_reviewed(item.id)

        updated = crud.get_someday_item(item.id)
        assert updated.review_count == 2
        assert updated.last_reviewed is not None


class TestPriorityTaskCRUD(TestSessionFixture):
    """Tests for priority task operations."""

    def test_update_priority_task(self):
        """Test setting priority task."""
        user = crud.get_or_create_user(telegram_id=123)
        crud.update_morning_entry(user.id, "", "", "Task 1", "Task 2", "Task 3")

        entry = crud.update_priority_task(user.id, priority_task=2)

        assert entry.priority_task == 2

    def test_get_priority_task_stats(self):
        """Test priority task statistics."""
        user = crud.get_or_create_user(telegram_id=123)

        # Create entries with priority tasks
        session = self.get_session()
        for i in range(5):
            entry = DailyEntry(
                user_id=user.id,
                entry_date=date.today() - timedelta(days=i),
                task_1="Task 1",
                task_2="Task 2",
                task_3="Task 3",
                task_1_done=(i < 3),  # First 3 days completed
                priority_task=1
            )
            session.add(entry)
        session.commit()
        session.close()

        stats = crud.get_priority_task_stats(user.id, days=7)

        assert stats["total"] == 5
        assert stats["completed"] == 3
        assert stats["rate"] == 60.0


class TestWeeklyReviewCRUD(TestSessionFixture):
    """Tests for weekly review operations."""

    def test_create_weekly_review(self):
        """Test creating weekly review."""
        user = crud.get_or_create_user(telegram_id=123)

        review = crud.create_weekly_review(user.id)

        assert review is not None
        assert review.review_date == date.today()
        assert review.completed is False

    def test_get_or_create_weekly_review(self):
        """Test get or create review."""
        user = crud.get_or_create_user(telegram_id=123)

        review1 = crud.get_or_create_weekly_review(user.id)
        review2 = crud.get_or_create_weekly_review(user.id)

        assert review1.id == review2.id

    def test_update_weekly_review(self):
        """Test updating review with kwargs."""
        user = crud.get_or_create_user(telegram_id=123)
        review = crud.create_weekly_review(user.id)

        updated = crud.update_weekly_review(
            review.id,
            week_wins="Finished project",
            week_learnings="Need more sleep",
            inbox_processed=5
        )

        assert updated.week_wins == "Finished project"
        assert updated.week_learnings == "Need more sleep"
        assert updated.inbox_processed == 5

    def test_complete_weekly_review(self):
        """Test completing review."""
        user = crud.get_or_create_user(telegram_id=123)
        review = crud.create_weekly_review(user.id)

        crud.complete_weekly_review(review.id)

        # Create another - should be new since previous is completed
        new_review = crud.get_or_create_weekly_review(user.id)
        assert new_review.id != review.id
