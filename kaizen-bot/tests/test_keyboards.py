"""Tests for keyboard builders."""

import pytest
from unittest.mock import MagicMock

from src.keyboards.inline import (
    get_main_menu,
    get_task_completion_keyboard,
    get_inbox_keyboard,
    get_priority_keyboard,
    get_goals_keyboard,
    get_someday_keyboard,
    get_inbox_item_keyboard,
)


class TestMainMenu:
    """Tests for main menu keyboard."""

    def test_main_menu_has_all_buttons(self):
        """Test that main menu contains all expected buttons."""
        keyboard = get_main_menu()

        # Flatten all buttons
        all_buttons = []
        for row in keyboard.inline_keyboard:
            all_buttons.extend(row)

        button_texts = [btn.text for btn in all_buttons]

        assert any("Утренний" in text for text in button_texts)
        assert any("Вечерняя" in text for text in button_texts)
        assert any("Inbox" in text for text in button_texts)
        assert any("Статистика" in text for text in button_texts)
        assert any("Цели" in text for text in button_texts)
        assert any("Weekly Review" in text for text in button_texts)
        assert any("Настройки" in text for text in button_texts)


class TestTaskCompletionKeyboard:
    """Tests for task completion keyboard."""

    def test_shows_all_three_tasks(self):
        """Test that all tasks are displayed."""
        keyboard = get_task_completion_keyboard(
            task_1="Task 1",
            task_2="Task 2",
            task_3="Task 3"
        )

        buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        task_buttons = [btn for btn in buttons if btn.callback_data.startswith("toggle_task:")]

        assert len(task_buttons) == 3

    def test_shows_checkmarks_for_done_tasks(self):
        """Test that done tasks show checkmarks."""
        keyboard = get_task_completion_keyboard(
            task_1="Task 1",
            task_2="Task 2",
            task_3="Task 3",
            t1_done=True,
            t2_done=False,
            t3_done=True
        )

        buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        task_buttons = [btn for btn in buttons if btn.callback_data.startswith("toggle_task:")]

        assert task_buttons[0].text.startswith("")
        assert task_buttons[1].text.startswith("")
        assert task_buttons[2].text.startswith("")

    def test_truncates_long_task_names(self):
        """Test that long task names are truncated with ellipsis."""
        long_task = "This is a very long task name that exceeds forty characters limit"
        keyboard = get_task_completion_keyboard(
            task_1=long_task,
            task_2="Short",
            task_3="Also short"
        )

        buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        task_1_button = next(btn for btn in buttons if btn.callback_data == "toggle_task:1")

        assert "..." in task_1_button.text
        # Should be truncated to 40 chars + checkbox prefix + "..."
        assert len(task_1_button.text) < len(long_task)

    def test_skips_empty_tasks(self):
        """Test that empty/None tasks are not shown."""
        keyboard = get_task_completion_keyboard(
            task_1="Only task",
            task_2=None,
            task_3=""
        )

        buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        task_buttons = [btn for btn in buttons if btn.callback_data.startswith("toggle_task:")]

        assert len(task_buttons) == 1

    def test_has_done_button(self):
        """Test that keyboard has a 'Done' button."""
        keyboard = get_task_completion_keyboard("T1", "T2", "T3")

        buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        done_buttons = [btn for btn in buttons if btn.callback_data == "tasks_done"]

        assert len(done_buttons) == 1


class TestInboxKeyboard:
    """Tests for inbox keyboard with pagination."""

    def _create_mock_items(self, count):
        """Create mock inbox items."""
        items = []
        for i in range(count):
            item = MagicMock()
            item.id = i + 1
            item.text = f"Item {i + 1}" if i != 0 else "A" * 50  # First item is long
            items.append(item)
        return items

    def test_shows_items_on_first_page(self):
        """Test first page displays correct items."""
        items = self._create_mock_items(12)
        keyboard = get_inbox_keyboard(items, page=0, per_page=5)

        buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        item_buttons = [btn for btn in buttons if btn.callback_data.startswith("inbox_item:")]

        assert len(item_buttons) == 5

    def test_pagination_shows_next_only_on_first_page(self):
        """Test first page shows only next button."""
        items = self._create_mock_items(12)
        keyboard = get_inbox_keyboard(items, page=0, per_page=5)

        buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        nav_buttons = [btn for btn in buttons if btn.callback_data.startswith("inbox_page:")]

        # Should only have next button
        assert len(nav_buttons) == 1
        assert nav_buttons[0].text == "➡️"

    def test_pagination_shows_both_on_middle_page(self):
        """Test middle page shows both prev and next buttons."""
        items = self._create_mock_items(15)
        keyboard = get_inbox_keyboard(items, page=1, per_page=5)

        buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        nav_buttons = [btn for btn in buttons if btn.callback_data.startswith("inbox_page:")]

        assert len(nav_buttons) == 2
        texts = [btn.text for btn in nav_buttons]
        assert "⬅️" in texts
        assert "➡️" in texts

    def test_pagination_shows_prev_only_on_last_page(self):
        """Test last page shows only prev button."""
        items = self._create_mock_items(12)
        keyboard = get_inbox_keyboard(items, page=2, per_page=5)

        buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        nav_buttons = [btn for btn in buttons if btn.callback_data.startswith("inbox_page:")]

        # Should only have prev button (only 2 items on page 2)
        assert len(nav_buttons) == 1
        assert nav_buttons[0].text == "⬅️"

    def test_truncates_long_item_text(self):
        """Test that long item texts are truncated."""
        items = self._create_mock_items(3)
        keyboard = get_inbox_keyboard(items, page=0)

        buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        first_item = next(btn for btn in buttons if btn.callback_data == "inbox_item:1")

        # First item has 50 chars, should be truncated
        assert "..." in first_item.text

    def test_no_pagination_for_small_list(self):
        """Test no pagination buttons for small lists."""
        items = self._create_mock_items(3)
        keyboard = get_inbox_keyboard(items, page=0, per_page=5)

        buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        nav_buttons = [btn for btn in buttons if btn.callback_data.startswith("inbox_page:")]

        assert len(nav_buttons) == 0


class TestPriorityKeyboard:
    """Tests for priority task selection keyboard."""

    def test_shows_all_three_tasks(self):
        """Test that all three task buttons are shown."""
        keyboard = get_priority_keyboard("Task 1", "Task 2", "Task 3")

        buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        priority_buttons = [btn for btn in buttons if btn.callback_data.startswith("priority:")]

        assert len(priority_buttons) == 3

    def test_shows_task_text_in_buttons(self):
        """Test that task text is shown in buttons."""
        keyboard = get_priority_keyboard("Do laundry", "Buy groceries", "Call mom")

        buttons = [btn for row in keyboard.inline_keyboard for btn in row]

        texts = [btn.text for btn in buttons]
        assert any("Do laundry" in text for text in texts)
        assert any("Buy groceries" in text for text in texts)
        assert any("Call mom" in text for text in texts)

    def test_truncates_long_task_names(self):
        """Test that long task names are truncated."""
        long_task = "A" * 50
        keyboard = get_priority_keyboard(long_task, "Short", "Short")

        buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        first_button = next(btn for btn in buttons if btn.callback_data == "priority:1")

        assert "..." in first_button.text

    def test_shows_default_for_empty_tasks(self):
        """Test that empty tasks show default text."""
        keyboard = get_priority_keyboard("", "", "")

        buttons = [btn for row in keyboard.inline_keyboard for btn in row]

        # Should show "Задача 1", "Задача 2", "Задача 3" as defaults
        texts = [btn.text for btn in buttons]
        assert any("Задача 1" in text for text in texts)
        assert any("Задача 2" in text for text in texts)
        assert any("Задача 3" in text for text in texts)


class TestGoalsKeyboard:
    """Tests for goals keyboard."""

    def _create_mock_goals(self, statuses):
        """Create mock goals with given statuses."""
        goals = []
        for i, status in enumerate(statuses):
            goal = MagicMock()
            goal.id = i + 1
            goal.title = f"Goal {i + 1}"
            goal.status = status
            goals.append(goal)
        return goals

    def test_shows_correct_emoji_for_status(self):
        """Test that correct emoji is shown for each status."""
        goals = self._create_mock_goals(["active", "paused", "completed"])
        keyboard = get_goals_keyboard(goals)

        buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        goal_buttons = [btn for btn in buttons if btn.callback_data.startswith("goal:")]

        assert "" in goal_buttons[0].text  # active
        assert "" in goal_buttons[1].text  # paused
        assert "" in goal_buttons[2].text  # completed

    def test_has_add_and_back_buttons(self):
        """Test keyboard has add goal and back buttons."""
        goals = self._create_mock_goals(["active"])
        keyboard = get_goals_keyboard(goals)

        buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        callback_data = [btn.callback_data for btn in buttons]

        assert "add_goal" in callback_data
        assert "main_menu" in callback_data


class TestSomedayKeyboard:
    """Tests for someday/maybe keyboard."""

    def _create_mock_items(self, count):
        """Create mock someday items."""
        items = []
        for i in range(count):
            item = MagicMock()
            item.id = i + 1
            item.text = f"Someday item {i + 1}"
            items.append(item)
        return items

    def test_limits_to_10_items(self):
        """Test that only 10 items are shown."""
        items = self._create_mock_items(15)
        keyboard = get_someday_keyboard(items)

        buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        item_buttons = [btn for btn in buttons if btn.callback_data.startswith("someday_item:")]

        assert len(item_buttons) == 10

    def test_has_back_button(self):
        """Test keyboard has back to main menu button."""
        items = self._create_mock_items(3)
        keyboard = get_someday_keyboard(items)

        buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        back_buttons = [btn for btn in buttons if btn.callback_data == "main_menu"]

        assert len(back_buttons) == 1


class TestInboxItemKeyboard:
    """Tests for single inbox item actions keyboard."""

    def test_has_all_action_buttons(self):
        """Test keyboard has process, someday, delete, and back buttons."""
        keyboard = get_inbox_item_keyboard(item_id=42)

        buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        callback_data = [btn.callback_data for btn in buttons]

        assert "inbox_process:42" in callback_data
        assert "inbox_someday:42" in callback_data
        assert "inbox_delete:42" in callback_data
        assert "inbox_show" in callback_data
