import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.config import BOT_TOKEN
from src.database.models import init_db
from src.handlers import start, morning, evening, stats, goals, settings, report, habits
from src.handlers import review, someday, inbox, calendar, rewards
from src.handlers import principles, dates, user_tasks
from src.scheduler.jobs import set_bot, setup_scheduler, start_scheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""

    # Инициализация БД
    logger.info("Инициализация базы данных...")
    init_db()

    # Создание бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(morning.router)
    dp.include_router(evening.router)
    dp.include_router(stats.router)
    dp.include_router(goals.router)
    dp.include_router(settings.router)
    dp.include_router(report.router)
    dp.include_router(habits.router)

    # GTD роутеры
    dp.include_router(review.router)
    dp.include_router(someday.router)
    dp.include_router(calendar.router)  # Google Calendar интеграция
    dp.include_router(rewards.router)  # Система наград (@whysasha)

    # Новые роутеры: принципы и даты
    dp.include_router(principles.router)  # Ежемесячная оценка принципов
    dp.include_router(dates.router)  # Важные даты и напоминания
    dp.include_router(user_tasks.router)  # Пользовательские задачи с наградами

    dp.include_router(inbox.router)  # ВАЖНО: Последним! Перехватывает любой текст

    # Настройка планировщика
    set_bot(bot)
    setup_scheduler()
    start_scheduler()

    # Запуск бота
    logger.info("Бот запущен!")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
