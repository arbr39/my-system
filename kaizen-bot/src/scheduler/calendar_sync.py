"""
Логика синхронизации с Google Calendar

Направления:
1. Bot -> Calendar: задачи дня + inbox с дедлайном
2. Calendar -> Bot: (будущая фича) polling изменений
"""

from datetime import datetime, date, timedelta

from src.database.crud import (
    get_today_entry,
    get_inbox_items_with_deadline,
    update_daily_entry_event_ids,
    update_inbox_event_id,
    update_calendar_last_sync,
    get_users_with_calendar_enabled
)
from src.integrations.google_calendar import GoogleCalendarService


async def sync_user_tasks_to_calendar(user) -> tuple[bool, str]:
    """
    Синхронизировать задачи пользователя в Google Calendar

    Args:
        user: объект User с google_refresh_token_encrypted

    Returns:
        (success, message)
    """
    if not user.google_refresh_token_encrypted:
        return False, "Календарь не подключён"

    try:
        service = GoogleCalendarService(user.id)
        if not service.load_credentials(user.google_refresh_token_encrypted):
            return False, "Не удалось загрузить credentials. Переподключи календарь."

        synced_count = 0
        calendar_id = user.google_calendar_id or "primary"

        # 1. Синхронизируем задачи дня (DailyEntry)
        entry = get_today_entry(user.id)
        if entry and entry.morning_completed:
            count = await _sync_daily_tasks(service, user, entry, calendar_id)
            synced_count += count

        # 2. Синхронизируем inbox с дедлайнами
        inbox_items = get_inbox_items_with_deadline(user.id)
        for item in inbox_items:
            if not item.google_event_id:  # ещё не синхронизировано
                try:
                    event_id = service.create_event(
                        summary=item.text[:100],  # ограничиваем длину
                        start_time=item.deadline,
                        description=f"Из Kaizen Inbox\nЭнергия: {item.energy_level or '-'}\nВремя: {item.time_estimate or '-'}",
                        calendar_id=calendar_id
                    )
                    update_inbox_event_id(item.id, event_id)
                    synced_count += 1
                except Exception as e:
                    print(f"Error syncing inbox item {item.id}: {e}")

        # Обновляем время последней синхронизации
        update_calendar_last_sync(user.telegram_id)

        if synced_count > 0:
            return True, f"Синхронизировано: {synced_count} событий"
        else:
            return True, "Нет новых задач для синхронизации"

    except Exception as e:
        return False, str(e)


async def _sync_daily_tasks(
    service: GoogleCalendarService,
    user,
    entry,
    calendar_id: str
) -> int:
    """
    Синхронизировать задачи дня в календарь

    Returns: количество созданных событий
    """
    synced = 0
    today = date.today()

    # Базовое время для задач: 9:00
    # Приоритетная задача: 8:00 (первое дело утра)
    base_time = datetime(today.year, today.month, today.day, 9, 0)
    priority_time = datetime(today.year, today.month, today.day, 8, 0)

    tasks = [
        (entry.task_1, entry.task_1_event_id, 1, "task_1_event_id"),
        (entry.task_2, entry.task_2_event_id, 2, "task_2_event_id"),
        (entry.task_3, entry.task_3_event_id, 3, "task_3_event_id"),
    ]

    event_ids = {}

    for task_text, existing_event_id, task_num, field_name in tasks:
        if not task_text:
            continue

        # Уже синхронизировано?
        if existing_event_id:
            continue

        is_priority = entry.priority_task == task_num

        try:
            # Время события: приоритетная в 8:00, остальные в 9:00, 10:00, 11:00
            if is_priority:
                start_time = priority_time
            else:
                # Смещаем обычные задачи чтобы не накладывались
                offset = (task_num - 1) * 60  # 0, 60, 120 минут
                start_time = base_time + timedelta(minutes=offset)

            event_id = service.create_event(
                summary=task_text[:100],
                start_time=start_time,
                end_time=start_time + timedelta(hours=1),
                is_priority=is_priority,
                description=f"Задача #{task_num} на {today.strftime('%d.%m.%Y')}"
            )
            event_ids[field_name] = event_id
            synced += 1

        except Exception as e:
            print(f"Error creating event for task {task_num}: {e}")

    # Сохраняем event IDs
    if event_ids:
        update_daily_entry_event_ids(user.id, **event_ids)

    return synced


async def sync_after_morning_kaizen(user) -> tuple[bool, str]:
    """
    Вызывается после завершения утреннего кайдзена

    Args:
        user: объект User

    Returns:
        (success, message)
    """
    if not user.calendar_sync_enabled:
        return False, "Синхронизация отключена"

    return await sync_user_tasks_to_calendar(user)


async def poll_all_calendars():
    """
    Периодический опрос календарей всех пользователей
    Вызывается из APScheduler

    TODO: Реализовать когда понадобится обратная синхронизация
    """
    users = get_users_with_calendar_enabled()

    for user in users:
        try:
            # Пока только синхронизируем бот -> календарь
            await sync_user_tasks_to_calendar(user)
        except Exception as e:
            print(f"Error polling calendar for user {user.telegram_id}: {e}")
