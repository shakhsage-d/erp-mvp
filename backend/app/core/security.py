"""
core/security.py
-------------------
Parolni xavfsiz saqlash (hech qachon ochiq matnda emas, faqat bcrypt
hash sifatida), JWT (access) token yaratish/tekshirish, va refresh
token (uzoq umrli, bekor qilinishi mumkin) yaratish shu yerda.

IKKI TOKEN MODELI:
  - ACCESS TOKEN (JWT, 30 daqiqa) — har bir so'rovda yuboriladi, o'zida
    company_id/role_id kabi ma'lumotni saqlaydi, tekshirish uchun
    bazaga murojaat qilinmaydi (tez).
  - REFRESH TOKEN (tasodifiy, 30 kun) — faqat yangi access token olish
    uchun ishlatiladi, BAZADA (xeshlangan holda) saqlanadi — shuning
    uchun "logout" yoki "token o'g'irlandi" holatida uni BEKOR QILISH
    (revoke) mumkin, JWT'dan farqli o'laroq.

MUHIM: `SECRET_KEY` haqiqiy (production) muhitda albatta maxfiy va
tasodifiy bo'lishi kerak (.env orqali, hech qachon kodga yozilmaydi).
Mahalliy sinov uchun standart qiymat beriladi, lekin bu qiymat bilan
ishlab chiqarishga chiqarish XAVFSIZ EMAS.
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt as pyjwt

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Endi qisqa umrli — refresh token bilan yangilanadi
REFRESH_TOKEN_EXPIRE_DAYS = 30

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
    JWT (access) token yaratadi. `payload` odatda quyidagilarni o'z
    ichiga oladi: {"sub": user_id, "company_id": ..., "role_id": ...}
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


def generate_refresh_token() -> tuple[str, str, datetime]:
    """
    Yangi refresh token yaratadi.
    Qaytaradi: (foydalanuvchiga yuboriladigan XOM token,
                bazada saqlanadigan XESH, muddati tugash vaqti)

    Xom token — faqat BIR MARTA, yaratilgan paytda ko'rinadi (javobda).
    Bazada esa hech qachon xom holida saqlanmaydi — agar baza
    "sizib chiqsa" ham, tokenlar ishlatilmaydigan bo'lib qoladi.
    """
    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return raw_token, token_hash, expires_at


def hash_refresh_token(raw_token: str) -> str:
    """Kelib tushgan refresh tokenni bazadagi xesh bilan solishtirish uchun."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
