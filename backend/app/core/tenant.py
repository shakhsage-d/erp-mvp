"""
core/tenant.py
--------------
MUHIM FAYL — MULTI-TENANCY NING YURAGI.

Har bir so'rov `Authorization: Bearer <token>` header'i orqali o'zini
tasdiqlaydi, `company_id` esa tokenning ICHIDAN olinadi (soxtalashtirib
bo'lmaydi).

Rol/ruxsat tekshiruvi endi shu faylda EMAS — `core/permissions.py`da
(`require_permission(...)`), chunki u bazaga murojaat qiladi (dinamik
ruxsatlar jadvali orqali). Bu fayl faqat "kim so'ramoqda va qaysi
kompaniya nomidan" savoliga javob beradi.
"""

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt as pyjwt

from app.core.security import decode_access_token
from app.core.exceptions import UnauthorizedError

bearer_scheme = HTTPBearer(
    scheme_name="JWT",
    description="Ro'yxatdan o'tish yoki kirishdan olingan token: 'Bearer <token>'",
)


def get_current_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Tokenni ochib, ichidagi ma'lumotni (sub, company_id, role_id) qaytaradi."""
    try:
        return decode_access_token(credentials.credentials)
    except pyjwt.ExpiredSignatureError:
        raise UnauthorizedError("Tokenning muddati tugagan, qayta kiring")
    except pyjwt.PyJWTError:
        raise UnauthorizedError("Token yaroqsiz")


def get_current_company_id(
    payload: dict = Depends(get_current_token_payload),
) -> int:
    """
    Barcha routerlar shu funksiyadan foydalanadi. Kelajakda (masalan
    "xodim faqat o'z filialini ko'rsin" kabi murakkabroq qoidalar
    kerak bo'lsa) FAQAT shu funksiya ichi o'zgaradi — routerlarga
    tegilmaydi.
    """
    company_id = payload.get("company_id")
    if company_id is None:
        raise UnauthorizedError("Tokenda company_id topilmadi")
    return int(company_id)


def get_current_user_id(
    payload: dict = Depends(get_current_token_payload),
) -> int:
    """Joriy so'rovni yuborayotgan foydalanuvchining o'z ID'si (masalan
    HRMS'da 'o'zining smenasini boshlash/tugatish' kabi holatlar uchun)."""
    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError("Tokenda foydalanuvchi ID'si topilmadi")
    return int(user_id)
