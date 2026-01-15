from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.config import ADMIN_USER_ID
from src.database.crud import (
    get_user_by_telegram_id, create_report, get_all_reports,
    update_report_status
)
from src.keyboards.inline import get_main_menu

router = Router()


class ReportStates(StatesGroup):
    """Состояния создания репорта"""
    select_type = State()
    description = State()


REPORT_TYPES = {
    "bug": {"emoji": "🐛", "name": "Баг"},
    "idea": {"emoji": "💡", "name": "Идея"},
    "improvement": {"emoji": "🔧", "name": "Улучшение"}
}

STATUS_EMOJI = {
    "new": "🆕",
    "in_progress": "⏳",
    "done": "✅",
    "rejected": "❌"
}


def get_report_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа репорта"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🐛 Баг", callback_data="report_type:bug"),
        InlineKeyboardButton(text="💡 Идея", callback_data="report_type:idea"),
    )
    builder.row(
        InlineKeyboardButton(text="🔧 Улучшение", callback_data="report_type:improvement")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")
    )
    return builder.as_markup()


def get_report_status_keyboard(report_id: int) -> InlineKeyboardMarkup:
    """Клавиатура изменения статуса репорта"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏳ В работе", callback_data=f"report_status:{report_id}:in_progress"),
        InlineKeyboardButton(text="✅ Готово", callback_data=f"report_status:{report_id}:done"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"report_status:{report_id}:rejected"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="reports_list"),
    )
    return builder.as_markup()


@router.message(Command("report"))
async def cmd_report(message: Message, state: FSMContext):
    """Команда /report — создание нового репорта"""
    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Сначала запусти /start")
        return

    await state.update_data(user_id=user.id)

    await message.answer(
        "📝 *Новый репорт*\n\n"
        "Выбери тип:",
        parse_mode="Markdown",
        reply_markup=get_report_type_keyboard()
    )
    await state.set_state(ReportStates.select_type)


@router.callback_query(F.data.startswith("report_type:"), ReportStates.select_type)
async def select_report_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа репорта"""
    report_type = callback.data.split(":")[1]
    await state.update_data(report_type=report_type)

    type_info = REPORT_TYPES[report_type]

    await callback.message.edit_text(
        f"{type_info['emoji']} *{type_info['name']}*\n\n"
        "Опиши подробно:",
        parse_mode="Markdown"
    )
    await state.set_state(ReportStates.description)
    await callback.answer()


@router.message(ReportStates.description)
async def process_report_description(message: Message, state: FSMContext, bot: Bot):
    """Обработка описания репорта"""
    data = await state.get_data()

    # Сохраняем в БД
    report = create_report(
        user_id=data["user_id"],
        report_type=data["report_type"],
        description=message.text
    )

    type_info = REPORT_TYPES[data["report_type"]]

    # Подтверждение пользователю
    await message.answer(
        f"✅ *Репорт #{report.id} создан!*\n\n"
        f"Тип: {type_info['emoji']} {type_info['name']}\n"
        f"Описание: {message.text[:100]}{'...' if len(message.text) > 100 else ''}\n\n"
        "Спасибо! Я рассмотрю это.",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )

    # Уведомление админу
    if ADMIN_USER_ID:
        try:
            user = get_user_by_telegram_id(message.from_user.id)
            admin_text = (
                f"📬 *Новый репорт #{report.id}*\n\n"
                f"От: {user.first_name} (@{user.username})\n"
                f"Тип: {type_info['emoji']} {type_info['name']}\n\n"
                f"📝 {message.text}"
            )
            await bot.send_message(
                ADMIN_USER_ID,
                admin_text,
                parse_mode="Markdown",
                reply_markup=get_report_status_keyboard(report.id)
            )
        except Exception as e:
            print(f"Ошибка отправки уведомления админу: {e}")

    await state.clear()


@router.message(Command("reports"))
async def cmd_reports(message: Message):
    """Команда /reports — список всех репортов (для админа)"""
    if message.from_user.id != ADMIN_USER_ID:
        await message.answer("❌ Эта команда доступна только администратору.")
        return

    reports = get_all_reports()

    if not reports:
        await message.answer(
            "📋 *Репорты*\n\nПока нет репортов.",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
        return

    text = "📋 *Все репорты:*\n\n"
    for report in reports[:20]:  # Последние 20
        type_info = REPORT_TYPES.get(report.report_type, {"emoji": "❓", "name": "?"})
        status_emoji = STATUS_EMOJI.get(report.status, "❓")
        text += (
            f"{status_emoji} *#{report.id}* {type_info['emoji']} "
            f"{report.description[:40]}{'...' if len(report.description) > 40 else ''}\n"
        )

    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu())


@router.callback_query(F.data == "reports_list")
async def show_reports_list(callback: CallbackQuery):
    """Показать список репортов"""
    if callback.from_user.id != ADMIN_USER_ID:
        await callback.answer("Только для админа")
        return

    reports = get_all_reports()

    if not reports:
        await callback.message.edit_text(
            "📋 *Репорты*\n\nПока нет репортов.",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
    else:
        text = "📋 *Все репорты:*\n\n"
        for report in reports[:20]:
            type_info = REPORT_TYPES.get(report.report_type, {"emoji": "❓", "name": "?"})
            status_emoji = STATUS_EMOJI.get(report.status, "❓")
            text += (
                f"{status_emoji} *#{report.id}* {type_info['emoji']} "
                f"{report.description[:40]}{'...' if len(report.description) > 40 else ''}\n"
            )
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_main_menu())

    await callback.answer()


@router.callback_query(F.data.startswith("report_status:"))
async def change_report_status(callback: CallbackQuery):
    """Изменение статуса репорта"""
    if callback.from_user.id != ADMIN_USER_ID:
        await callback.answer("Только для админа")
        return

    parts = callback.data.split(":")
    report_id = int(parts[1])
    new_status = parts[2]

    report = update_report_status(report_id, new_status)

    if report:
        status_emoji = STATUS_EMOJI.get(new_status, "❓")
        await callback.message.edit_text(
            f"✅ Репорт #{report_id} обновлён\n\n"
            f"Новый статус: {status_emoji} {new_status}",
            reply_markup=get_main_menu()
        )
    else:
        await callback.message.edit_text("❌ Репорт не найден", reply_markup=get_main_menu())

    await callback.answer()
