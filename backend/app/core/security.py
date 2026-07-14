"""
core/security.py
-------------------
Parolni xavfsiz saqlash (hech qachon ochiq matnda emas, faqat bcrypt
hash sifatida) va JWT token yaratish/tekshirish shu yerda.

MUHIM: `SECRET_KEY` haqiqiy (production) muhitda albatta maxfiy va
tasodifiy bo'lishi kerak (.env orqali, hech qachon kodga yozilmaydi).
Mahalliy sinov uchun standart qiymat beriladi, lekin bu qiymat bilan
ishlab chiqarishga chiqarish XAVFSIZ EMAS.
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt as pyjwt

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 kun

SECRET_KEY = os.getenv("SECRET_KEY", "mahalliy-sinov-uchun-xavfsiz-emas-kalit")
if SECRET_KEY == "mahalliy-sinov-uchun-xavfsiz-emas-kalit" and os.getenv("ENV") == "production":
    raise RuntimeError(
        "PRODUCTION muhitda standart SECRET_KEY ishlatib bo'lmaydi! "
        "Render'da Environment Variables'ga tasodifiy, uzun SECRET_KEY qo'shing."
    )


def hash_password(password: str) -> str:
    """Parolni bcrypt bilan xeshlab, saqlash uchun tayyor matn qaytaradi."""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiritilgan parol, bazadagi xesh bilan mos kelishini tekshiradi."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(payload: dict) -> str:
    """
    JWT token yaratadi. `payload` odatda quyidagilarni o'z ichiga oladi:
        {"sub": user_id, "company_id": ..., "role": ...}
    """
    to_encode = payload.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return pyjwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Tokenni ochib, ichidagi ma'lumotni qaytaradi.
    Muddati tugagan yoki soxta token bo'lsa, `jwt.PyJWTError` ko'taradi —
    buni chaqiruvchi (core/tenant.py) mos HTTP xatosiga aylantiradi.
    """
    return pyjwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
