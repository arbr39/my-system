import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Пути
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "kaizen.db"

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

# Расписание напоминаний
MORNING_HOUR = int(os.getenv("MORNING_HOUR", "7"))
MORNING_MINUTE = int(os.getenv("MORNING_MINUTE", "0"))
EVENING_HOUR = int(os.getenv("EVENING_HOUR", "22"))
EVENING_MINUTE = int(os.getenv("EVENING_MINUTE", "0"))

# Таймзона
TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")

# Google Calendar OAuth2
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "urn:ietf:wg:oauth:2.0:oob")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")  # Fernet key для шифрования токенов

# Проверка токена
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен! Создайте .env файл.")
