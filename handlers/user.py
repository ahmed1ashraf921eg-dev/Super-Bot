from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from keyboards.user_kb import get_main_reply_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    await message.answer(
        text="مرحباً بك.",
        reply_markup=get_main_reply_keyboard(user_id=user_id),
    )