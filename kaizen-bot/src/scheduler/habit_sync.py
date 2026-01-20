"""
Синхронизация выполнения привычек с Google Calendar.

Job sync_habit_completions() запускается ежедневно в 22:30
(после вечерней рефлексии) и обновляет цвет событий:
- Выполнено → зелёный (colorId: "10")
- Не выполнено → без изменений (нейтрально, без стыда!)
"""

from datetime import datetime, date

from src.database.models import get_session, HabitCalendarEvent, DailyEntry
from src.database.crud import get_all_users, get_today_entry
from src.integrations.google_calendar import GoogleCalendarService


# Цвета событий
COLOR_COMPLETED = "10"  # Зелёный — выполнено
COLOR_DEFAULT = "8"     # Серый — не выполнено (нейтрально)


async def sync_habit_completions():
    """
    Синхронизировать выполнение привычек с календарём.
    Вызывается ежедневно в 22:30 после вечерней рефлексии.
    """
    session = get_session()
    try:
        users = get_all_users()

        for user in users:
            # Пропускаем если календарь не подключён
            if not user.google_refresh_token_encrypted:
                continue
            if not user.calendar_sync_enabled:
                continue

            # Получаем привычки пользователя
            habit_events = session.query(HabitCalendarEvent).filter(
                HabitCalendarEvent.user_id == user.id,
                HabitCalendarEvent.is_active == True
            ).all()

            if not habit_events:
                continue

            # Загружаем calendar service
            calendar_service = GoogleCalendarService(user.id)
            if not calendar_service.load_credentials(user.google_refresh_token_encrypted):
                continue

            # Получаем сегодняшнюю запись
            entry = get_today_entry(user.id)
            if not entry:
                continue

            # Обновляем цвета для каждой привычки
            for habit_event in habit_events:
                if not habit_event.google_event_id:
                    continue

                # Определяем выполнена ли привычка
                is_completed = False
                if habit_event.habit_type == "exercise":
                    is_completed = entry.exercised == True
                elif habit_event.habit_type == "eating":
                    is_completed = entry.ate_well == True

                # Обновляем цвет только если выполнено (без стыда за невыполненное!)
                if is_completed:
                    success = calendar_service.update_event_color(
                        event_id=habit_event.google_event_id,
                        color_id=COLOR_COMPLETED,
                        calendar_id=user.google_calendar_id or "primary"
                    )

                    if success:
                        habit_event.last_completed_date = date.today()
                        habit_event.last_synced_at = datetime.now()
                        print(f"[HABIT SYNC] User {user.id}: {habit_event.habit_type} marked as completed (green)")

            session.commit()

    except Exception as e:
        print(f"Error in sync_habit_completions: {e}")
    finally:
        session.close()
