"""
Умные напоминания о событиях календаря и follow-up триггеры.

Два job'а запускаются каждые 5 минут:
1. check_upcoming_events() — напоминания о предстоящих событиях
2. check_ended_events() — follow-up после завершения событий
"""

from datetime import datetime, timedelta
from typing import Optional

from src.database.models import get_session, User, CalendarEventReminder
from src.database.crud import get_users_with_calendar_enabled
from src.integrations.google_calendar import GoogleCalendarService
from src.keyboards.inline_calendar import get_followup_keyboard

# Глобальная переменная для бота (устанавливается из jobs.py)
bot = None


def set_bot(bot_instance):
    """Установка экземпляра бота"""
    global bot
    bot = bot_instance


# Слова для исключения из follow-up
EXCLUDED_KEYWORDS = [
    "focus", "фокус",
    "обед", "lunch",
    "перерыв", "break",
    "отдых", "rest",
    "[kaizen]", "⭐"
]

# Минимальная длительность события для follow-up (минуты)
MIN_EVENT_DURATION_MINUTES = 15


def _is_in_quiet_hours(user: User) -> bool:
    """Проверить, находимся ли в тихих часах пользователя"""
    now = datetime.now()
    current_hour = now.hour

    start = user.quiet_hours_start or 23
    end = user.quiet_hours_end or 7

    # Обработка перехода через полночь (23:00 - 07:00)
    if start > end:
        return current_hour >= start or current_hour < end
    else:
        return start <= current_hour < end


def _should_exclude_event(event: dict) -> bool:
    """Проверить, нужно ли исключить событие из follow-up"""
    summary = event.get('summary', '').lower()

    # Проверяем ключевые слова
    for keyword in EXCLUDED_KEYWORDS:
        if keyword.lower() in summary:
            return True

    # Проверяем длительность
    start_str = event.get('start', {}).get('dateTime')
    end_str = event.get('end', {}).get('dateTime')

    if start_str and end_str:
        try:
            start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            duration = (end - start).total_seconds() / 60

            if duration < MIN_EVENT_DURATION_MINUTES:
                return True
        except ValueError:
            pass

    return False


def _get_or_create_reminder(
    session,
    user_id: int,
    event: dict
) -> Optional[CalendarEventReminder]:
    """Получить или создать запись о напоминании"""
    event_id = event.get('id')
    if not event_id:
        return None

    # Ищем существующую запись
    reminder = session.query(CalendarEventReminder).filter(
        CalendarEventReminder.user_id == user_id,
        CalendarEventReminder.google_event_id == event_id
    ).first()

    if reminder:
        return reminder

    # Парсим время события
    start_str = event.get('start', {}).get('dateTime')
    end_str = event.get('end', {}).get('dateTime')

    start_time = None
    end_time = None

    if start_str:
        try:
            start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00')).replace(tzinfo=None)
        except ValueError:
            pass

    if end_str:
        try:
            end_time = datetime.fromisoformat(end_str.replace('Z', '+00:00')).replace(tzinfo=None)
        except ValueError:
            pass

    if not start_time:
        return None

    # Создаём новую запись
    is_bot_created = any(kw in event.get('summary', '').lower() for kw in ['[kaizen]', '⭐'])

    reminder = CalendarEventReminder(
        user_id=user_id,
        google_event_id=event_id,
        event_start=start_time,
        event_end=end_time,
        event_summary=event.get('summary', '')[:500],
        is_bot_created=is_bot_created,
        is_excluded=_should_exclude_event(event)
    )
    session.add(reminder)
    session.commit()

    return reminder


async def check_upcoming_events():
    """
    Проверить предстоящие события и отправить напоминания.
    Вызывается каждые 5 минут из APScheduler.
    """
    if not bot:
        return

    session = get_session()
    try:
        users = get_users_with_calendar_enabled()

        for user in users:
            # Пропускаем если напоминания выключены
            if not user.event_reminders_enabled:
                continue

            # Пропускаем если тихие часы
            if _is_in_quiet_hours(user):
                continue

            # Загружаем credentials
            if not user.google_refresh_token_encrypted:
                continue

            calendar_service = GoogleCalendarService(user.id)
            if not calendar_service.load_credentials(user.google_refresh_token_encrypted):
                continue

            # Получаем события в ближайшие N минут
            minutes_before = user.reminder_minutes_before or 15
            events = calendar_service.get_upcoming_events(
                minutes_ahead=minutes_before,
                calendar_id=user.google_calendar_id or "primary"
            )

            for event in events:
                reminder = _get_or_create_reminder(session, user.id, event)
                if not reminder:
                    continue

                # Пропускаем если уже напоминали
                if reminder.reminder_sent_at:
                    continue

                # Отправляем напоминание
                summary = event.get('summary', 'Событие')
                start_str = event.get('start', {}).get('dateTime', '')

                # Форматируем время
                time_str = ""
                if start_str:
                    try:
                        start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                        time_str = start.strftime("%H:%M")
                    except ValueError:
                        pass

                try:
                    await bot.send_message(
                        user.telegram_id,
                        f"📅 *Через {minutes_before} мин:* {summary}\n"
                        f"⏰ Начало: {time_str}",
                        parse_mode="Markdown"
                    )

                    # Отмечаем что напомнили
                    reminder.reminder_sent_at = datetime.now()
                    session.commit()

                except Exception as e:
                    print(f"Error sending reminder to user {user.telegram_id}: {e}")

    except Exception as e:
        print(f"Error in check_upcoming_events: {e}")
    finally:
        session.close()


async def check_ended_events():
    """
    Проверить завершившиеся события и отправить follow-up.
    Вызывается каждые 5 минут из APScheduler.
    """
    if not bot:
        return

    session = get_session()
    try:
        users = get_users_with_calendar_enabled()

        for user in users:
            # Пропускаем если тихие часы
            if _is_in_quiet_hours(user):
                continue

            if not user.google_refresh_token_encrypted:
                continue

            calendar_service = GoogleCalendarService(user.id)
            if not calendar_service.load_credentials(user.google_refresh_token_encrypted):
                continue

            # Получаем события завершившиеся за последние 10 минут
            events = calendar_service.get_recently_ended_events(
                minutes_past=10,
                calendar_id=user.google_calendar_id or "primary"
            )

            for event in events:
                reminder = _get_or_create_reminder(session, user.id, event)
                if not reminder:
                    continue

                # Пропускаем если уже отправляли follow-up
                if reminder.followup_sent_at:
                    continue

                # Пропускаем исключённые события (созданные ботом, "focus", короткие)
                if reminder.is_bot_created or reminder.is_excluded:
                    continue

                # Отправляем follow-up
                summary = event.get('summary', 'Событие')

                try:
                    await bot.send_message(
                        user.telegram_id,
                        f"✅ *Событие завершилось:* {summary}\n\n"
                        f"Есть action items для записи?",
                        parse_mode="Markdown",
                        reply_markup=get_followup_keyboard(reminder.id)
                    )

                    # Отмечаем что отправили follow-up
                    reminder.followup_sent_at = datetime.now()
                    session.commit()

                except Exception as e:
                    print(f"Error sending followup to user {user.telegram_id}: {e}")

    except Exception as e:
        print(f"Error in check_ended_events: {e}")
    finally:
        session.close()
