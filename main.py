import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.db import init_db
from handlers.admin import router as admin_router
from handlers.user import router as user_router


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    if not BOT_TOKEN or BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        raise RuntimeError(
            "BOT_TOKEN غير مضبوط. أضف قيمة BOT_TOKEN في متغيرات البيئة (Environment Variables) على pella."
        )

    # تهيئة قاعدة بيانات SQLite وإنشاء الجداول والإعدادات الافتراضية
    init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # تسجيل مسارات الأدمن والمستخدمين
    dp.include_router(admin_router)
    dp.include_router(user_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())