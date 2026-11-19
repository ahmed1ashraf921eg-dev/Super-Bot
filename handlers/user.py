from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS
from database.db import (
    get_button,
    get_buttons_by_parent,
    get_setting,
    get_user,
    upsert_user,
)
from keyboards.user_kb import build_menu_keyboard, build_pending_request_keyboard

router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _send_or_edit_menu(
    event: Message | CallbackQuery,
    parent_id: int | None = None,
    header_text: str | None = None,
) -> None:
    user_id = event.from_user.id
    buttons = get_buttons_by_parent(parent_id=parent_id)

    grandparent_id: int | None = None
    title_text = header_text
    if parent_id is not None:
        parent_btn = get_button(parent_id)
        if parent_btn:
            grandparent_id = parent_btn.get("parent_id")
            if not title_text:
                title_text = parent_btn.get("content_text") or f"📌 {parent_btn['title']}"

    if not title_text:
        title_text = get_setting("welcome_text", "أهلاً بك في البوت! اختر من القائمة التالية:")

    markup = build_menu_keyboard(
        buttons=buttons,
        parent_id=parent_id,
        grandparent_id=grandparent_id,
        is_admin=_is_admin(user_id),
    )

    if isinstance(event, Message):
        await event.answer(title_text, reply_markup=markup)
    else:
        await event.message.edit_text(title_text, reply_markup=markup)
        await event.answer()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user = message.from_user
    bot_mode = get_setting("bot_mode", "public")
    existing = get_user(user.id)

    if bot_mode == "private" and not _is_admin(user.id):
        if existing and existing["status"] == "active":
            await _send_or_edit_menu(message, parent_id=None)
            return

        status = existing["status"] if existing else "pending"
        upsert_user(
            user_id=user.id,
            full_name=user.full_name,
            username=user.username,
            status=status,
        )
        await message.answer(
            "🔒 البوت يعمل حالياً في الوضع الخاص، وتم تسجيل طلب انضمامك بانتظار موافقة الإدارة.",
            reply_markup=build_pending_request_keyboard(),
        )
        return

    upsert_user(
        user_id=user.id,
        full_name=user.full_name,
        username=user.username,
        status="active",
    )
    await _send_or_edit_menu(message, parent_id=None)


from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS
from database.db import (
    get_button,
    get_buttons_by_parent,
    get_setting,
    get_user,
    upsert_user,
)
from keyboards.user_kb import build_menu_keyboard, build_pending_request_keyboard

router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _send_or_edit_menu(
    event: Message | CallbackQuery,
    parent_id: int | None = None,
    header_text: str | None = None,
) -> None:
    user_id = event.from_user.id
    buttons = get_buttons_by_parent(parent_id=parent_id)

    grandparent_id: int | None = None
    title_text = header_text
    if parent_id is not None:
        parent_btn = get_button(parent_id)
        if parent_btn:
            grandparent_id = parent_btn.get("parent_id")
            if not title_text:
                title_text = parent_btn.get("content_text") or f"📌 {parent_btn['title']}"

    if not title_text:
        title_text = get_setting("welcome_text", "أهلاً بك في البوت! اختر من القائمة التالية:")

    markup = build_menu_keyboard(
        buttons=buttons,
        parent_id=parent_id,
        grandparent_id=grandparent_id,
        is_admin=_is_admin(user_id),
    )

    if isinstance(event, Message):
        await event.answer(title_text, reply_markup=markup)
    else:
        await event.message.edit_text(title_text, reply_markup=markup)
        await event.answer()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user = message.from_user
    bot_mode = get_setting("bot_mode", "public")
    existing = get_user(user.id)

    if bot_mode == "private" and not _is_admin(user.id):
        if existing and existing["status"] == "active":
            await _send_or_edit_menu(message, parent_id=None)
            return

        status = existing["status"] if existing else "pending"
        upsert_user(
            user_id=user.id,
            full_name=user.full_name,
            username=user.username,
            status=status,
        )
        await message.answer(
            "🔒 البوت يعمل حالياً في الوضع الخاص، وتم تسجيل طلب انضمامك بانتظار موافقة الإدارة.",
            reply_markup=build_pending_request_keyboard(),
        )
        return

    upsert_user(
        user_id=user.id,
        full_name=user.full_name,
        username=user.username,
        status="active",
    )
    await _send_or_edit_menu(message, parent_id=None)


@router.callback_query(F.data == "menu:root")
async def cb_menu_root(callback: CallbackQuery) -> None:
    await _send_or_edit_menu(callback, parent_id=None)


@router.callback_query(F.data.startswith("btn:"))
async def cb_open_button(callback: CallbackQuery) -> None:
    raw_id = callback.data.split(":", 1)[1]
    if not raw_id.isdigit():
        await callback.answer("زر غير صالح", show_alert=True)
        return

    btn_id = int(raw_id)
    btn = get_button(btn_id)
    if not btn:
        await callback.answer("هذا الزر غير موجود", show_alert=True)
        return

    children = get_buttons_by_parent(parent_id=btn_id)
    content = btn.get("content_text") or f"📌 {btn['title']}"

    if children:
        await _send_or_edit_menu(callback, parent_id=btn_id, header_text=content)
    else:
        grandparent_id = btn.get("parent_id")
        markup = build_menu_keyboard(
            buttons=[],
            parent_id=btn_id,
            grandparent_id=grandparent_id,
            is_admin=_is_admin(callback.from_user.id),
        )
        await callback.message.edit_text(content, reply_markup=markup)
        await callback.answer()


@router.callback_query(F.data == "req:check")
async def cb_check_request(callback: CallbackQuery) -> None:
    user = get_user(callback.from_user.id)
    if user and user["status"] == "active":
        await _send_or_edit_menu(callback, parent_id=None)
    else:
        await callback.answer("⏳ طلبك لا يزال قيد المراجعة لدى الإدارة.", show_alert=True)