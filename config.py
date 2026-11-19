import os
from typing import List


def _parse_admin_ids(raw_ids: str) -> List[int]:
    ids: List[int] = []
    for part in raw_ids.split(","):
        cleaned = part.strip()
        if cleaned.isdigit():
            ids.append(int(cleaned))
    return ids


# توكن البوت من متغيرات البيئة في Koyeb (مع قيمة افتراضية مؤقتة للتجربة المحلية فقط)
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")

# معرفات الأدمن مفصولة بفاصلة، مثال: "123456789,987654321"
ADMIN_IDS: List[int] = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))

# مسار ملف قاعدة بيانات SQLite
DB_PATH: str = os.getenv("DB_PATH", "database/superbot.db")

# وضع البوت الافتراضي: "public" أو "private"
DEFAULT_BOT_MODE: str = os.getenv("BOT_MODE", "public").lower()