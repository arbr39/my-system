---
paths:
  - "**/*.py"
---

# Python Style Guidelines

> Применяется ко всем Python файлам в my_system

## Type Hints

Всегда используй type hints:

```python
# ✅ Правильно
def get_reward_balance(user_id: int) -> int:
    return fund.balance

def grant_reward(user_id: int, amount: int, description: str = None) -> RewardTransaction:
    ...

# ❌ Неправильно
def get_reward_balance(user_id):
    return fund.balance
```

## Async/Await

Aiogram 3.x требует async везде:

```python
# ✅ Правильно
async def finish_morning(message: Message, state: FSMContext):
    reward = grant_morning_kaizen_reward(user_id)
    await message.answer(f"+{reward}₽")

# ❌ Неправильно
def finish_morning(message, state):  # Не async!
    ...
```

## Database Sessions

Всегда используй try/finally для закрытия сессий:

```python
# ✅ Правильно
def get_user(telegram_id: int) -> User | None:
    session = get_session()
    try:
        return session.query(User).filter(...).first()
    finally:
        session.close()

# ❌ Неправильно
def get_user(telegram_id):
    session = get_session()
    return session.query(User).filter(...).first()
    # Забыли закрыть сессию!
```

## String Formatting

Используй f-strings везде:

```python
# ✅ Правильно
summary += f"💰 +{reward}₽ за утренний кайдзен!"
summary += f"Баланс: {balance}₽"

# ❌ Неправильно
summary += "Reward: " + str(reward) + " rubles"
summary += "Balance: %d rubles" % balance
```

## Imports

Группировка:
1. Стандартная библиотека
2. Third-party (aiogram, sqlalchemy...)
3. Local imports (src.*)

```python
# ✅ Правильно
import asyncio
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message

from src.database.crud import get_user
from src.keyboards.inline import get_main_menu

# ❌ Неправильно - всё вперемешку
from src.database.crud import get_user
import asyncio
from aiogram import Router
```

## Docstrings

Только для неочевидных функций:

```python
# ✅ Docstring нужен
def grant_evening_reflection_reward(
    user_id: int,
    tasks_done: int,
    priority_done: bool,
    exercised: bool,
    ate_well: bool
) -> dict:
    """
    Начислить награды за вечернюю рефлексию.
    Returns: breakdown словарь с детализацией
    """
    ...

# ✅ Docstring НЕ нужен - код говорит сам за себя
def get_reward_balance(user_id: int) -> int:
    fund = get_or_create_reward_fund(user_id)
    return fund.balance
```

## Error Handling

Не подавляй ошибки без логирования:

```python
# ✅ Правильно
try:
    reward = grant_reward(user_id, amount)
except Exception as e:
    logger.error(f"Reward error: {e}")
    # или print для простых случаев
    print(f"Reward error: {e}")

# ❌ Неправильно
try:
    reward = grant_reward(user_id, amount)
except:
    pass  # Проглотили ошибку!
```

## Naming Conventions

- **Functions:** `snake_case`
- **Classes:** `PascalCase`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_leading_underscore`

```python
# ✅ Правильно
class RewardFund(Base):
    DEFAULT_MORNING_REWARD = 50

    def get_balance(self) -> int:
        return self._calculate_balance()

    def _calculate_balance(self) -> int:
        ...
```

## TODO Comments

Используй TODO для известных ограничений:

```python
# ✅ Правильно - конкретный TODO
def avg_time(times: list) -> str:
    # TODO: Обработка времени после полуночи (sleep_time "01:30" = 25:30?)
    # TODO: Заменить bare except на except ValueError
    ...

# ❌ Неправильно - слишком общий
def avg_time(times: list) -> str:
    # TODO: fix this
    ...
```
