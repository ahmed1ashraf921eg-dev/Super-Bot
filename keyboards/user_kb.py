from typing import Any, Dict, List, Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_menu_keyboard(
    buttons: List[Dict[str, Any]],
    parent_id: Optional[int] = None,
    grandparent_id: Optional[int] = None,
    row_width: int = 2,
    is_admin: bool = False,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for btn in buttons:
        btn_id = btn["id"]
        title = btn["title"]
        url = btn.get("url")

        if url:
            builder.add(InlineKeyboardButton(text=title, url=url))
        else:
            builder.add(InlineKeyboardButton(text=title, callback_data=f"btn:{btn_id}"))

    if row_width > 0:
        builder.adjust(row_width)

    # زر الرجوع عند الدخول في مستوى فرعي أو عرض محتوى زر
    if parent_id is not None:
        back_target = f"btn:{grandparent_id}" if grandparent_id is not None else "menu:root"
        builder.row(InlineKeyboardButton(text="⬅️ رجوع", callback_data=back_target))

    # زر لوحة الإدارة يظهر للأدمن فقط في القائمة الرئيسية
    if parent_id is None and is_admin:
        builder.row(InlineKeyboardButton(text="⚙️ لوحة التحكم", callback_data="admin:panel"))

    return builder.as_markup()


def build_pending_request_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 تحديث حالة الطلب", callback_data="req:check")]
        ]
    )