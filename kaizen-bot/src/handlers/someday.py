"""
GTD Someday/Maybe Handler - список 'Когда-нибудь/может быть'

Для идей и задач без срочности, к которым вернёшься позже.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from src.database.crud import (
    get_or_create_user, get_user_someday, get_someday_item,
    move_someday_to_inbox, delete_someday_item
)
from src.keyboards.inline import (
    get_someday_keyboard, get_someday_empty_keyboard,
    get_someday_item_keyboard, get_main_menu
)

router = Router()


# ============ Команда /someday ============

@router.message(Command("someday"))
async def cmd_someday(message: Message):
    """Показать список 'когда-нибудь'"""
    user = get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    items = get_user_someday(user.id)

    if not items:
        await message.answer(
            "💭 *Когда-нибудь/может быть*\n\n"
            "Список пуст. Сюда попадают идеи из Inbox, "
            "к которым ты вернёшься когда-нибудь.",
            parse_mode="Markdown",
            reply_markup=get_someday_empty_keyboard()
        )
    else:
        await message.answer(
            f"💭 *Когда-нибудь/может быть* ({len(items)})\n\n"
            "Идеи, к которым вернёшься позже:",
            parse_mode="Markdown",
            reply_markup=get_someday_keyboard(items)
        )


@router.callback_query(F.data == "someday_show")
async def callback_someday_show(callback: CallbackQuery):
    """Показать список 'когда-нибудь' (callback)"""
    user = get_or_create_user(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.first_name
    )
    items = get_user_someday(user.id)

    if not items:
        await callback.message.edit_text(
            "💭 *Когда-нибудь/может быть*\n\n"
            "Список пуст. Сюда попадают идеи из Inbox, "
            "к которым ты вернёшься когда-нибудь.",
            parse_mode="Markdown",
            reply_markup=get_someday_empty_keyboard()
        )
    else:
        await callback.message.edit_text(
            f"💭 *Когда-нибудь/может быть* ({len(items)})\n\n"
            "Идеи, к которым вернёшься позже:",
            parse_mode="Markdown",
            reply_markup=get_someday_keyboard(items)
        )
    await callback.answer()


# ============ Просмотр элемента ============

@router.callback_query(F.data.startswith("someday_item:"))
async def show_someday_item(callback: CallbackQuery):
    """Показать элемент someday"""
    item_id = int(callback.data.split(":")[1])
    item = get_someday_item(item_id)

    if not item:
        await callback.answer("Идея не найдена", show_alert=True)
        return

    review_info = ""
    if item.review_count > 0:
        review_info = f"\n\n📊 Просмотрено раз: {item.review_count}"

    await callback.message.edit_text(
        f"💭 *Идея*\n\n"
        f"_{item.text}_"
        f"{review_info}\n\n"
        f"Что делаем?",
        parse_mode="Markdown",
        reply_markup=get_someday_item_keyboard(item.id)
    )
    await callback.answer()


# ============ Активация - вернуть в Inbox ============

@router.callback_query(F.data.startswith("someday_activate:"))
async def activate_someday(callback: CallbackQuery):
    """Вернуть из someday в inbox"""
    item_id = int(callback.data.split(":")[1])
    inbox_item = move_someday_to_inbox(item_id)

    if inbox_item:
        await callback.message.edit_text(
            "📥 *Перемещено в Inbox!*\n\n"
            "Теперь это активная задача.",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
    else:
        await callback.answer("Ошибка перемещения", show_alert=True)

    await callback.answer()


# ============ Удаление ============

@router.callback_query(F.data.startswith("someday_delete:"))
async def delete_someday(callback: CallbackQuery):
    """Удалить из someday"""
    item_id = int(callback.data.split(":")[1])
    delete_someday_item(item_id)

    await callback.message.edit_text(
        "🗑 *Удалено!*\n\n"
        "Идея убрана из списка.",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )
    await callback.answer()
