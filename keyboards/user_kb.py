from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from config import ADMIN_IDS


def get_main_reply_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    keyboard: list[list[KeyboardButton]] = []

    if user_id in ADMIN_IDS:
        keyboard.append([KeyboardButton(text="صنع أزرار جديدة")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )