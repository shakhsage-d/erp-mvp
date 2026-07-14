"""
core/config.py
--------------
Barcha muhim sozlamalar (.env dan o'qiladi) shu yerda bitta joyda.
Yangi sozlama kerak bo'lsa (masalan API kaliti), shu faylga qo'shiladi,
kodning boshqa joyiga os.getenv sochib tashlanmaydi.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = "MikroERP API"
    ENV: str = os.getenv("ENV", "local")  # local | staging | production
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")


settings = Settings()
