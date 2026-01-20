import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import TIMEZONE, MORNING_HOUR, MORNING_MINUTE, EVENING_HOUR, EVENING_MINUTE
from src.database.crud import get_all_users, get_today_entry, get_week_stats, get_inbox_count
from src.keyboards.inline import get_main_menu, get_review_start_keyboard
from src.handlers.stats import format_week_report

# TODO: Добавить тесты для scheduler jobs (мок bot.send_message)
# TODO: Рассмотреть dependency injection вместо глобальной переменной bot
# Глобальная переменная для бота
bot = None
scheduler = AsyncIOScheduler(timezone=TIMEZONE)


def set_bot(bot_instance):
    """Установка экземпляра бота для отправки сообщений"""
    global bot
    bot = bot_instance


async def send_morning_reminder():
    """Утреннее напоминание"""
    if not bot:
        return

    users = get_all_users()
    for user in users:
        try:
            entry = get_today_entry(user.id)
            if not entry or not entry.morning_completed:
                await bot.send_message(
                    user.telegram_id,
                    "🌅 *Доброе утро!*\n\n"
                    "Пора заполнить утренний кайдзен.\n"
                    "3 задачи + рефлексия = продуктивный день!",
                    parse_mode="Markdown",
                    reply_markup=get_main_menu()
                )
        except Exception as e:
            print(f"Ошибка отправки утреннего напоминания пользователю {user.telegram_id}: {e}")


async def send_evening_reminder():
    """Вечернее напоминание (с напоминанием о планировании 22:00-22:30)"""
    if not bot:
        return

    users = get_all_users()
    for user in users:
        try:
            entry = get_today_entry(user.id)
            if entry and entry.morning_completed and not entry.evening_completed:
                await bot.send_message(
                    user.telegram_id,
                    "🌙 *Добрый вечер!*\n\n"
                    "Пора подвести итоги дня.\n"
                    "Отметь выполненные задачи и запиши инсайт!\n\n"
                    "_После рефлексии — планирование на завтра (22:00-22:30)_\n"
                    "_📋 Things 3 + Google Calendar_",
                    parse_mode="Markdown",
                    reply_markup=get_main_menu()
                )
        except Exception as e:
            print(f"Ошибка отправки вечернего напоминания пользователю {user.telegram_id}: {e}")


async def send_weekly_report():
    """Еженедельный отчёт (воскресенье)"""
    if not bot:
        return

    users = get_all_users()
    for user in users:
        try:
            stats = get_week_stats(user.id)
            if stats['total_entries'] > 0:
                report = "📅 *Еженедельный отчёт*\n\n"
                report += format_week_report(stats)
                report += "\n\n🚀 Отличная неделя! Продолжай в том же духе!"

                await bot.send_message(
                    user.telegram_id,
                    report,
                    parse_mode="Markdown",
                    reply_markup=get_main_menu()
                )
        except Exception as e:
            print(f"Ошибка отправки еженедельного отчёта пользователю {user.telegram_id}: {e}")


async def send_weekly_review_reminder():
    """Напоминание о Weekly Review (воскресенье, перед weekly_report)"""
    if not bot:
        return

    users = get_all_users()
    for user in users:
        try:
            inbox_count = get_inbox_count(user.id)

            await bot.send_message(
                user.telegram_id,
                "📋 *Время для Weekly Review!*\n\n"
                f"📥 В inbox: {inbox_count} задач\n\n"
                "Это важная часть GTD - еженедельный обзор.\n"
                "Займёт 10-15 минут.",
                parse_mode="Markdown",
                reply_markup=get_review_start_keyboard()
            )
        except Exception as e:
            print(f"Ошибка отправки review напоминания пользователю {user.telegram_id}: {e}")


async def send_birthday_reminders():
    """Отправка напоминаний о днях рождения (каждый день в 9:00)"""
    if not bot:
        return

    from datetime import date
    from src.database.crud_dates import (
        get_dates_for_reminder, was_reminder_sent, mark_reminder_sent
    )

    today = date.today()

    # Напоминания за 1 день
    for user, d in get_dates_for_reminder(days_ahead=1):
        if was_reminder_sent(d.id, "before", today.year):
            continue

        try:
            emoji = "🎂" if d.date_type == "birthday" else "📌"
            await bot.send_message(
                user.telegram_id,
                f"{emoji} *Напоминание!*\n\n"
                f"Завтра: *{d.name}*\n"
                f"Не забудь поздравить! 🎁",
                parse_mode="Markdown"
            )
            mark_reminder_sent(d.id, "before", today.year)
        except Exception as e:
            print(f"Birthday reminder error (before): {e}")

    # Напоминания в сам день
    for user, d in get_dates_for_reminder(days_ahead=0):
        if was_reminder_sent(d.id, "on_day", today.year):
            continue

        try:
            emoji = "🎂" if d.date_type == "birthday" else "📌"
            await bot.send_message(
                user.telegram_id,
                f"{emoji} *Сегодня!*\n\n"
                f"*{d.name}*\n"
                f"Поздравь! 🎉",
                parse_mode="Markdown"
            )
            mark_reminder_sent(d.id, "on_day", today.year)
        except Exception as e:
            print(f"Birthday reminder error (on_day): {e}")


async def send_monthly_assessment_reminder():
    """Напоминание о ежемесячной оценке принципов (1-е число месяца)"""
    if not bot:
        return

    from src.keyboards.inline_principles import get_principles_start_keyboard

    users = get_all_users()
    for user in users:
        try:
            await bot.send_message(
                user.telegram_id,
                "📊 *Время для ежемесячной оценки!*\n\n"
                "Прошёл ещё один месяц. Пора оценить свои 25 принципов жизни.\n\n"
                "Оценка займёт 5 дней по 2 минуты в день.\n"
                "Это поможет отследить прогресс!",
                parse_mode="Markdown",
                reply_markup=get_principles_start_keyboard()
            )
        except Exception as e:
            print(f"Monthly assessment reminder error: {e}")


async def send_quizlet_reminder():
    """Напоминание Quizlet английский (каждый день в 21:30)"""
    if not bot:
        return

    from src.handlers.quizlet import get_quizlet_keyboard

    users = get_all_users()
    for user in users:
        try:
            await bot.send_message(
                user.telegram_id,
                "🇬🇧 *Quizlet английский*\n\n"
                "Пора заниматься английским!\n"
                "Открой Quizlet и позанимайся 10-15 минут.\n\n"
                "💰 Награда: *60₽*",
                parse_mode="Markdown",
                reply_markup=get_quizlet_keyboard()
            )
        except Exception as e:
            print(f"Quizlet reminder error: {e}")


def setup_scheduler():
    """Настройка планировщика"""
    # Утреннее напоминание
    scheduler.add_job(
        send_morning_reminder,
        CronTrigger(hour=MORNING_HOUR, minute=MORNING_MINUTE, timezone=TIMEZONE),
        id="morning_reminder",
        replace_existing=True
    )

    # Вечернее напоминание
    scheduler.add_job(
        send_evening_reminder,
        CronTrigger(hour=EVENING_HOUR, minute=EVENING_MINUTE, timezone=TIMEZONE),
        id="evening_reminder",
        replace_existing=True
    )

    # Weekly Review напоминание (воскресенье в 18:00, за 2 часа до отчёта)
    scheduler.add_job(
        send_weekly_review_reminder,
        CronTrigger(day_of_week="sun", hour=18, minute=0, timezone=TIMEZONE),
        id="weekly_review_reminder",
        replace_existing=True
    )

    # Еженедельный отчёт (воскресенье в 20:00)
    scheduler.add_job(
        send_weekly_report,
        CronTrigger(day_of_week="sun", hour=20, minute=0, timezone=TIMEZONE),
        id="weekly_report",
        replace_existing=True
    )

    # Синхронизация с Google Calendar (каждые 30 минут)
    scheduler.add_job(
        sync_calendars,
        CronTrigger(minute="*/30", timezone=TIMEZONE),
        id="calendar_sync",
        replace_existing=True
    )

    # Напоминания о днях рождения (каждый день в 9:00)
    scheduler.add_job(
        send_birthday_reminders,
        CronTrigger(hour=9, minute=0, timezone=TIMEZONE),
        id="birthday_reminders",
        replace_existing=True
    )

    # Напоминание о ежемесячной оценке принципов (1-е число месяца, 10:00)
    scheduler.add_job(
        send_monthly_assessment_reminder,
        CronTrigger(day=1, hour=10, minute=0, timezone=TIMEZONE),
        id="monthly_assessment_reminder",
        replace_existing=True
    )

    # Quizlet английский (каждый день в 21:30)
    scheduler.add_job(
        send_quizlet_reminder,
        CronTrigger(hour=21, minute=30, timezone=TIMEZONE),
        id="quizlet_reminder",
        replace_existing=True
    )

    return scheduler


async def sync_calendars():
    """Периодическая синхронизация с Google Calendar"""
    try:
        from src.scheduler.calendar_sync import poll_all_calendars
        await poll_all_calendars()
    except Exception as e:
        print(f"Calendar sync error: {e}")


def start_scheduler():
    """Запуск планировщика"""
    if not scheduler.running:
        scheduler.start()
        print(f"Scheduler started. Timezone: {TIMEZONE}")
        print(f"Morning reminder: {MORNING_HOUR}:{MORNING_MINUTE:02d}")
        print(f"Evening reminder: {EVENING_HOUR}:{EVENING_MINUTE:02d}")
        print("Weekly review reminder: Sunday 18:00")
        print("Weekly report: Sunday 20:00")
        print("Calendar sync: every 30 minutes")
        print("Birthday reminders: daily 09:00")
        print("Monthly assessment: 1st day of month 10:00")
        print("Quizlet reminder: daily 21:30")


def stop_scheduler():
    """Остановка планировщика"""
    if scheduler.running:
        scheduler.shutdown()
