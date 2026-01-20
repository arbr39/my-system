"""
Handler для ежедневного напоминания Quizlet английский
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.database.crud import get_user_by_telegram_id
from src.database.crud_rewards import grant_reward

router = Router()

QUIZLET_URL = "https://quizlet.com/ru/1037808774/crypto-magician-arkhip-flash-cards/"
QUIZLET_REWARD = 60


def get_quizlet_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для Quizlet напоминания"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="🔗 Открыть Quizlet",
        url=QUIZLET_URL
    ))

    builder.row(InlineKeyboardButton(
        text="✅ Выполнено",
        callback_data="quizlet_done"
    ))

    return builder.as_markup()


@router.callback_query(F.data == "quizlet_done")
async def quizlet_done(callback: CallbackQuery):
    """Отметить выполнение Quizlet английского"""
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка: пользователь не найден")
        return

    # Начислить награду
    try:
        transaction = grant_reward(
            user_id=user.id,
            amount=QUIZLET_REWARD,
            transaction_type="quizlet_english",
            description="Quizlet английский"
        )

        if transaction:
            await callback.message.edit_text(
                f"🎉 *Отлично!*\n\n"
                f"Ты позанимался английским через Quizlet!\n\n"
                f"💰 *+{QUIZLET_REWARD}₽* начислено в фонд наград",
                parse_mode="Markdown"
            )
            await callback.answer(f"✅ +{QUIZLET_REWARD}₽", show_alert=False)
        else:
            await callback.answer("❌ Ошибка начисления награды", show_alert=True)

    except Exception as e:
        print(f"Ошибка начисления награды за Quizlet: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
