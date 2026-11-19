import time
from typing import Any, Dict, List, Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS
from database.db import (
    add_button,
    get_button,
    get_buttons_by_parent,
    get_connection,
    get_setting,
    get_user,
    set_setting,
    set_user_status,
)
from keyboards.admin_kb import (
    build_admin_buttons_keyboard,
    build_admin_panel_keyboard,
    build_request_action_keyboard,
    build_single_button_manage_keyboard,
)

router = Router()


class AdminStates(StatesGroup):
    waiting_new_button_title = State()
    waiting_new_button_content = State()
    waiting_edit_button_content = State()
    waiting_dm_target_id = State()
    waiting_dm_text = State()


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def _get_pending_users() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE status = 'pending' ORDER BY created_at ASC;"
        ).fetchall()
        return [dict(r) for r in rows]


def _pause_subscriptions_for_private_mode() -> None:
    now_ts = int(time.time())
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT user_id, expires_at FROM users WHERE expires_at IS NOT NULL AND expires_at > ?;",
            (now_ts,),
        ).fetchall()
        for row in rows:
            remaining = max(0, int(row["expires_at"]) - now_ts)
            conn.execute(
                """
                UPDATE users
                SET paused_remaining_seconds = ?, expires_at = NULL
                WHERE user_id = ?;
                """,
                (remaining, row["user_id"]),
            )
        conn.commit()


def _resume_subscriptions_for_public_mode() -> None:
    now_ts = int(time.time())
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT user_id, paused_remaining_seconds
            FROM users
            WHERE paused_remaining_seconds IS NOT NULL;
            """,
        ).fetchall()
        for row in rows:
            new_expires_at = now_ts + int(row["paused_remaining_seconds"])
            conn.execute(
                """
                UPDATE users
                SET expires_at = ?, paused_remaining_seconds = NULL
                WHERE user_id = ?;
                """,
                (new_expires_at, row["user_id"]),
            )
        conn.commit()


def _swap_button_positions(btn_a: Dict[str, Any], btn_b: Dict[str, Any]) -> None:
    pos_a = int(btn_a.get("position", 0))
    pos_b = int(btn_b.get("position", 0))
    if pos_a == pos_b:
        pos_b = pos_a + 1
    with get_connection() as conn:
        conn.execute("UPDATE buttons SET position = ? WHERE id = ?;", (pos_b, btn_a["id"]))
        conn.execute("UPDATE buttons SET position = ? WHERE id = ?;", (pos_a, btn_b["id"]))
        conn.commit()


def _copy_button_recursive(source_btn_id: int, target_parent_id: Optional[int]) -> Optional[int]:
    src = get_button(source_btn_id)
    if not src:
        return None
    new_id = add_button(
        title=f"{src['title']} (نسخة)",
        parent_id=target_parent_id,
        content_text=src.get("content_text"),
        media_type=src.get("media_type"),
        media_file_id=src.get("media_file_id"),
        url=src.get("url"),
    )
    children = get_buttons_by_parent(parent_id=source_btn_id)
    for child in children:
        _copy_button_recursive(child["id"], new_id)
    return new_id


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return
    mode = get_setting("bot_mode", "public")
    await message.answer(
        f"⚙️ <b>لوحة تحكم SuperBot</b>\nالوضع الحالي: <code>{mode}</code>",
        parse_mode="HTML",
        reply_markup=build_admin_panel_keyboard(current_mode=mode),
    )


@router.callback_query(F.data == "admin:panel")
async def cb_admin_panel(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("غير مسموح لك بالوصول.", show_alert=True)
        return
    await state.clear()
    mode = get_setting("bot_mode", "public")
    await callback.message.edit_text(
        f"⚙️ <b>لوحة تحكم SuperBot</b>\nالوضع الحالي: <code>{mode}</code>",
        parse_mode="HTML",
        reply_markup=build_admin_panel_keyboard(current_mode=mode),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:toggle_mode")
async def cb_toggle_mode(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    current_mode = get_setting("bot_mode", "public")
    if current_mode == "public":
        new_mode = "private"
        _pause_subscriptions_for_private_mode()
        notice = "🔒 تم التحويل إلى الوضع الخاص (Private) وإيقاف عدّاد الاشتراكات مؤقتاً."
    else:
        new_mode = "public"
        _resume_subscriptions_for_public_mode()
        notice = "🌐 تم التحويل إلى الوضع العام (Public) واستئناف عدّاد الاشتراكات."

    set_setting("bot_mode", new_mode)
    await callback.message.edit_text(
        f"⚙️ <b>لوحة تحكم SuperBot</b>\nالوضع الحالي: <code>{new_mode}</code>\n\n{notice}",
        parse_mode="HTML",
        reply_markup=build_admin_panel_keyboard(current_mode=new_mode),
    )
    await callback.answer("تم تحديث وضع البوت")


@router.callback_query(F.data == "admin:requests")
async def cb_admin_requests(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    pending = _get_pending_users()
    await callback.answer()
    if not pending:
        await callback.message.answer("لا توجد طلبات انضمام معلقة حالياً.")
        return

    for user in pending:
        uname = f"@{user['username']}" if user.get("username") else "بدون معرف"
        text = (
            f"📥 <b>طلب انضمام جديد</b>\n"
            f"الاسم: {user.get('full_name') or 'مستخدم'}\n"
            f"المعرف: {uname}\n"
            f"ID: <code>{user['user_id']}</code>"
        )
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=build_request_action_keyboard(int(user["user_id"])),
        )


@router.callback_query(F.data.startswith("req:approve:"))
async def cb_approve_request(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    target_id = int(callback.data.split(":")[2])
    set_user_status(target_id, "active")
    await callback.message.edit_text(f"✅ تم قبول طلب المستخدم <code>{target_id}</code>.", parse_mode="HTML")
    try:
        await callback.bot.send_message(target_id, "✅ تمت الموافقة على طلب انضمامك! أرسل /start لفتح القائمة.")
    except Exception:
        pass
    await callback.answer("تم القبول")


@router.callback_query(F.data.startswith("req:reject:"))
async def cb_reject_request(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    target_id = int(callback.data.split(":")[2])
    set_user_status(target_id, "rejected")
    await callback.message.edit_text(f"❌ تم رفض طلب المستخدم <code>{target_id}</code>.", parse_mode="HTML")
    try:
        await callback.bot.send_message(target_id, "❌ نعتذر، لم تتم الموافقة على طلب انضمامك حالياً.")
    except Exception:
        pass
    await callback.answer("تم الرفض")


@router.callback_query(F.data.startswith("admin:buttons:"))
async def cb_admin_buttons_list(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    raw_parent = callback.data.split(":")[2]
    parent_id = None if raw_parent == "root" else int(raw_parent)
    buttons = get_buttons_by_parent(parent_id=parent_id)
    label = "القائمة الرئيسية" if parent_id is None else f"الأزرار الفرعية للزر #{parent_id}"

    await callback.message.edit_text(
        f"🌲 <b>إدارة الأزرار</b> — {label}",
        parse_mode="HTML",
        reply_markup=build_admin_buttons_keyboard(buttons=buttons, parent_id=parent_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_btn:open:"))
async def cb_adm_btn_open(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    btn_id = int(callback.data.split(":")[2])
    btn = get_button(btn_id)
    if not btn:
        await callback.answer("الزر غير موجود", show_alert=True)
        return

    info = (
        f"🛠 <b>إدارة الزر #{btn['id']}</b>\n"
        f"العنوان: {btn['title']}\n"
        f"المحتوى: {btn.get('content_text') or '—'}\n"
        f"الرابط: {btn.get('url') or '—'}\n"
        f"الترتيب: {btn.get('position', 0)}"
    )
    await callback.message.edit_text(
        info,
        parse_mode="HTML",
        reply_markup=build_single_button_manage_keyboard(
            button_id=btn_id,
            parent_id=btn.get("parent_id"),
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_btn:move_up:") | F.data.startswith("adm_btn:move_down:"))
async def cb_adm_btn_move(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    parts = callback.data.split(":")
    direction = parts[1]
    btn_id = int(parts[2])
    btn = get_button(btn_id)
    if not btn:
        await callback.answer("الزر غير موجود", show_alert=True)
        return

    siblings = get_buttons_by_parent(parent_id=btn.get("parent_id"))
    idx = next((i for i, b in enumerate(siblings) if b["id"] == btn_id), -1)
    if idx == -1:
        await callback.answer("تعذر تحديد الموضع", show_alert=True)
        return

    target_idx = idx - 1 if direction == "move_up" else idx + 1
    if 0 <= target_idx < len(siblings):
        _swap_button_positions(siblings[idx], siblings[target_idx])

    updated_siblings = get_buttons_by_parent(parent_id=btn.get("parent_id"))
    await callback.message.edit_reply_markup(
        reply_markup=build_admin_buttons_keyboard(
            buttons=updated_siblings,
            parent_id=btn.get("parent_id"),
        )
    )
    await callback.answer("تم تحديث الترتيب")


@router.callback_query(F.data.startswith("adm_btn:copy:"))
async def cb_adm_btn_copy(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    btn_id = int(callback.data.split(":")[2])
    btn = get_button(btn_id)
    if not btn:
        await callback.answer("الزر غير موجود", show_alert=True)
        return

    new_id = _copy_button_recursive(btn_id, btn.get("parent_id"))
    updated_siblings = get_buttons_by_parent(parent_id=btn.get("parent_id"))
    await callback.message.edit_reply_markup(
        reply_markup=build_admin_buttons_keyboard(
            buttons=updated_siblings,
            parent_id=btn.get("parent_id"),
        )
    )
    await callback.answer(f"تم نسخ الزر (#{new_id})", show_alert=True)


@router.callback_query(F.data.startswith("adm_btn:delete:"))
async def cb_adm_btn_delete(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    btn_id = int(callback.data.split(":")[2])
    btn = get_button(btn_id)
    parent_id = btn.get("parent_id") if btn else None

    with get_connection() as conn:
        conn.execute("DELETE FROM buttons WHERE id = ?;", (btn_id,))
        conn.commit()

    updated_siblings = get_buttons_by_parent(parent_id=parent_id)
    await callback.message.edit_text(
        "🗑 تم حذف الزر وأزراره الفرعية.",
        reply_markup=build_admin_buttons_keyboard(buttons=updated_siblings, parent_id=parent_id),
    )
    await callback.answer("تم الحذف")


@router.callback_query(F.data.startswith("adm_btn:add:"))
async def cb_adm_btn_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    raw_parent = callback.data.split(":")[2]
    parent_id = None if raw_parent == "root" else int(raw_parent)
    await state.update_data(new_btn_parent_id=parent_id)
    await state.set_state(AdminStates.waiting_new_button_title)
    await callback.message.answer("✍️ أرسل الآن عنوان الزر الجديد:")
    await callback.answer()


@router.message(AdminStates.waiting_new_button_title)
async def fsm_new_button_title(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.update_data(new_btn_title=message.text.strip())
    await state.set_state(AdminStates.waiting_new_button_content)
    await message.answer(
        "📝 أرسل الآن نص المحتوى الذي يظهر عند الضغط على الزر (أو اكتب <code>-</code> لتركه فارغاً أو لجعله حاوية لأزرار فرعية):",
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_new_button_content)
async def fsm_new_button_content(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    data = await state.get_data()
    parent_id = data.get("new_btn_parent_id")
    title = data.get("new_btn_title", "زر جديد")
    raw_content = (message.text or "").strip()
    content_text = None if raw_content in ("", "-") else raw_content

    new_id = add_button(title=title, parent_id=parent_id, content_text=content_text)
    await state.clear()
    await message.answer(f"✅ تم إنشاء الزر <b>{title}</b> بنجاح (رقم #{new_id}).", parse_mode="HTML")


@router.callback_query(F.data.startswith("adm_btn:edit:"))
async def cb_adm_btn_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    btn_id = int(callback.data.split(":")[2])
    await state.update_data(edit_btn_id=btn_id)
    await state.set_state(AdminStates.waiting_edit_button_content)
    await callback.message.answer("✏️ أرسل النص الجديد لمحتوى الزر (أو <code>-</code> لمسح المحتوى النصي):", parse_mode="HTML")
    await callback.answer()


@router.message(AdminStates.waiting_edit_button_content)
async def fsm_edit_button_content(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    data = await state.get_data()
    btn_id = data.get("edit_btn_id")
    raw_text = (message.text or "").strip()
    new_content = None if raw_text in ("", "-") else raw_text

    with get_connection() as conn:
        conn.execute("UPDATE buttons SET content_text = ? WHERE id = ?;", (new_content, btn_id))
        conn.commit()

    await state.clear()
    await message.answer(f"✅ تم تحديث محتوى الزر #{btn_id}.")


@router.callback_query(F.data == "admin:dm")
async def cb_admin_dm_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_dm_target_id)
    await callback.message.answer("🆔 أرسل رقم معرف المستخدم (User ID) الذي تريد مراسلته:")
    await callback.answer()


@router.callback_query(F.data.startswith("dm:user:"))
async def cb_dm_specific_user(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    target_id = int(callback.data.split(":")[2])
    await state.update_data(dm_target_id=target_id)
    await state.set_state(AdminStates.waiting_dm_text)
    await callback.message.answer(f"✉️ أرسل نص الرسالة التي تريد إرسالها للمستخدم <code>{target_id}</code>:", parse_mode="HTML")
    await callback.answer()


@router.message(AdminStates.waiting_dm_target_id)
async def fsm_dm_target_id(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    raw_id = (message.text or "").strip()
    if not raw_id.isdigit():
        await message.answer("⚠️ من فضلك أرسل رقماً صحيحاً لمعرف المستخدم.")
        return

    target_id = int(raw_id)
    if not get_user(target_id):
        await message.answer("⚠️ هذا المستخدم غير مسجل في قاعدة بيانات البوت بعد.")
        return

    await state.update_data(dm_target_id=target_id)
    await state.set_state(AdminStates.waiting_dm_text)
    await message.answer("✉️ أرسل الآن نص الرسالة المراد إرسالها:")


@router.message(AdminStates.waiting_dm_text)
async def fsm_dm_send_text(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    data = await state.get_data()
    target_id = data.get("dm_target_id")
    text_to_send = message.text or ""

    try:
        await message.bot.send_message(target_id, f"📩 <b>رسالة من الإدارة:</b>\n\n{text_to_send}", parse_mode="HTML")
        await message.answer(f"✅ تم إرسال الرسالة إلى المستخدم <code>{target_id}</code>.", parse_mode="HTML")
    except Exception as exc:
        await message.answer(f"❌ تعذر إرسال الرسالة: <code>{exc}</code>", parse_mode="HTML")
    finally:
        await state.clear()