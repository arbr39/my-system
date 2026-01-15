"""
Google Calendar интеграция для kaizen-bot

OAuth2 авторизация (OOB flow) + CRUD операции с событиями
"""

from datetime import datetime, timedelta
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    ENCRYPTION_KEY,
    TIMEZONE
)

# Scopes для Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar.events']


def _get_fernet():
    """Получить Fernet для шифрования/дешифрования токенов"""
    if not ENCRYPTION_KEY:
        return None
    from cryptography.fernet import Fernet
    return Fernet(ENCRYPTION_KEY.encode())


class GoogleCalendarService:
    """Сервис для работы с Google Calendar API"""

    def __init__(self, user_id: int = None):
        self.user_id = user_id
        self.credentials: Optional[Credentials] = None
        self.service = None
        self._fernet = _get_fernet()

    # === OAuth2 ===

    def get_auth_url(self) -> tuple[str, str]:
        """
        Получить URL для авторизации (OOB flow)
        Returns: (auth_url, state)
        """
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            raise ValueError("Google OAuth credentials не настроены в .env")

        flow = Flow.from_client_config(
            {
                "installed": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=SCOPES,
            redirect_uri=GOOGLE_REDIRECT_URI
        )
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return auth_url, state

    def exchange_code(self, code: str, state: str) -> str:
        """
        Обменять authorization code на tokens
        Returns: encrypted refresh token
        """
        flow = Flow.from_client_config(
            {
                "installed": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=SCOPES,
            redirect_uri=GOOGLE_REDIRECT_URI,
            state=state
        )
        flow.fetch_token(code=code)
        credentials = flow.credentials

        if not credentials.refresh_token:
            raise ValueError("Не получен refresh token. Попробуйте ещё раз.")

        # Шифруем refresh token
        if self._fernet:
            encrypted = self._fernet.encrypt(credentials.refresh_token.encode())
            return encrypted.decode()
        return credentials.refresh_token

    def load_credentials(self, encrypted_refresh_token: str) -> bool:
        """Загрузить credentials из encrypted refresh token"""
        try:
            if self._fernet:
                refresh_token = self._fernet.decrypt(encrypted_refresh_token.encode()).decode()
            else:
                refresh_token = encrypted_refresh_token

            self.credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=GOOGLE_CLIENT_ID,
                client_secret=GOOGLE_CLIENT_SECRET,
                scopes=SCOPES
            )
            self.service = build('calendar', 'v3', credentials=self.credentials)
            return True
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return False

    # === Event CRUD ===

    def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime = None,
        description: str = None,
        calendar_id: str = "primary",
        is_priority: bool = False
    ) -> str:
        """
        Создать событие в календаре
        Returns: event_id
        """
        if not self.service:
            raise ValueError("Service не инициализирован. Вызовите load_credentials().")

        if end_time is None:
            end_time = start_time + timedelta(hours=1)

        # Цвет: 11 (красный) для приоритетной, 9 (синий) для обычной
        color_id = "11" if is_priority else "9"

        # Префикс для приоритетной задачи
        title = f"⭐ {summary}" if is_priority else f"[Kaizen] {summary}"

        event = {
            'summary': title,
            'description': description or "Создано через Kaizen Bot",
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': TIMEZONE,
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': TIMEZONE,
            },
            'colorId': color_id,
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 15},
                ],
            },
        }

        try:
            result = self.service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()
            return result['id']
        except HttpError as e:
            print(f"Error creating event: {e}")
            raise

    def update_event(
        self,
        event_id: str,
        summary: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        description: str = None,
        calendar_id: str = "primary"
    ) -> bool:
        """Обновить существующее событие"""
        if not self.service:
            return False

        try:
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()

            if summary:
                event['summary'] = summary
            if description:
                event['description'] = description
            if start_time:
                event['start'] = {
                    'dateTime': start_time.isoformat(),
                    'timeZone': TIMEZONE,
                }
            if end_time:
                event['end'] = {
                    'dateTime': end_time.isoformat(),
                    'timeZone': TIMEZONE,
                }

            self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            return True
        except HttpError as e:
            print(f"Error updating event: {e}")
            return False

    def delete_event(self, event_id: str, calendar_id: str = "primary") -> bool:
        """Удалить событие"""
        if not self.service:
            return False

        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            return True
        except HttpError as e:
            print(f"Error deleting event: {e}")
            return False

    def get_today_events(self, calendar_id: str = "primary") -> list:
        """Получить события на сегодня"""
        if not self.service:
            return []

        try:
            now = datetime.now()
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)

            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_of_day.isoformat() + 'Z',
                timeMax=end_of_day.isoformat() + 'Z',
                maxResults=50,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            return events_result.get('items', [])
        except HttpError as e:
            print(f"Error getting events: {e}")
            return []

    def get_event(self, event_id: str, calendar_id: str = "primary") -> dict | None:
        """Получить событие по ID"""
        if not self.service:
            return None

        try:
            return self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
        except HttpError:
            return None
