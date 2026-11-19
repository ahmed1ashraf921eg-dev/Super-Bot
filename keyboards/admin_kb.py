from typing import Any, Dict, List, Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_admin_panel_keyboard(current_mode: str = "public") -> InlineKeyboardMarkup:
    mode_label = "🔒 تحويل إلى خاص (Private)" if current_mode == "public" else "🌐 تحويل إلى عام (Public)"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=mode_label, callback_data="admin:toggle_mode")],
            [InlineKeyboardButton(text="📥 طلبات الانضمام المعلقة", callback_data="admin:requests")],
            [InlineKeyboardButton(text="🌲 إدارة الأزرار المتداخلة", callback_data="admin:buttons:root")],
            [InlineKeyboardButton(text="✉️ مراسلة مستخدم مباشر", callback_data="admin:dm")],
            [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="menu:root")],
        ]
    )


def build_request_action_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ قبول الطلب", callback_data=f"req:approve:{user_id}"),
                InlineKeyboardButton(text="❌ رفض الطلب", callback_data=f"req:reject:{user_id}"),
            ],
            [InlineKeyboardButton(text="💬 مراسلة المستخدم", callback_data=f"dm:user:{user_id}")],
        ]
    )


def build_admin_buttons_keyboard(
    buttons: List[Dict[str, Any]],
    parent_id: Optional[int] = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for btn in buttons:
        btn_id = btn["id"]
        title = btn["title"]
        pos = btn.get("position", 0)
        builder.row(
            InlineKeyboardButton(text=f"📁 {title} (#{pos})", callback_data=f"adm_btn:open:{btn_id}"),
            InlineKeyboardButton(text="⬆️", callback_data=f"adm_btn:move_up:{btn_id}"),
            InlineKeyboardButton(text="⬇️", callback_data=f"adm_btn:move_down:{btn_id}"),
            InlineKeyboardButton(text="📋", callback_data=f"adm_btn:copy:{btn_id}"),
        )

    add_target = "root" if parent_id is None else str(parent_id)
    builder.row(InlineKeyboardButton(text="➕ إضافة زر جديد هنا", callback_data=f"adm_btn:add:{add_target}"))

    back_cb = "admin:panel" if parent_id is None else "admin:buttons:root"
    builder.row(InlineKeyboardButton(text="⬅️ رجوع", callback_data=back_cb))

    return builder.as_markup()


def build_single_button_manage_keyboard(button_id: int, parent_id: Optional[int] = None) -> InlineKeyboardMarkup:
    back_cb = "admin:buttons:root" if parent_id is None else f"adm_btn:open:{parent_id}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📂 فتح الأزرار الفرعية بداخل هذا الزر", callback_data=f"admin:buttons:{button_id}")],
            [InlineKeyboardButton(text="➕ إضافة زر فرعي هنا", callback_data=f"adm_btn:add:{button_id}")],
            [InlineKeyboardButton(text="✏️ تعديل النص / المحتوى / الرابط", callback_data=f"adm_btn:edit:{button_id}")],
            [InlineKeyboardButton(text="📋 نسخ الزر", callback_data=f"adm_btn:copy:{button_id}")],
            [InlineKeyboardButton(text="🗑 حذف الزر", callback_data=f"adm_btn:delete:{button_id}")],
            [InlineKeyboardButton(text="⬅️ رجوع", callback_data=back_cb)],
        ]
    )