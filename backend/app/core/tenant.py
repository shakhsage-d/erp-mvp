"""
core/tenant.py
--------------
MUHIM FAYL — MULTI-TENANCY NING YURAGI.

Endi (Bosqich 1) bu yerda HAQIQIY autentifikatsiya ishlaydi: har bir
so'rov `Authorization: Bearer <token>` header'i orqali o'zini
tasdiqlaydi, `company_id` esa endi so'rovda o'zi aytilmaydi (masalan
eski "X-Company-Id" header kabi) — u tokenning ICHIDAN olinadi, ya'ni
soxtalashtirib bo'lmaydi.

QOIDA: Har bir router (inventory, sales, finance, hrms, pms...)
`get_current_company_id()` orqali kompaniyani aniqlaydi. Yangi modul
qo'shilganda ham shu FAYLGA tegilmaydi.
"""

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt as pyjwt

from app.core.security import decode_access_token
from app.core.exceptions import UnauthorizedError, ForbiddenError

bearer_scheme = HTTPBearer(
    scheme_name="JWT",
    description="Ro'yxatdan o'tish yoki kirishdan olingan token: 'Bearer <token>'",
)


def get_current_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Tokenni ochib, ichidagi ma'lumotni (sub, company_id, role) qaytaradi."""
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


def get_current_user_role(
    payload: dict = Depends(get_current_token_payload),
) -> str:
    """Kelajakdagi rol-asosidagi ruxsatlar uchun tayyor (masalan faqat
    'owner' HRMS ish haqi ma'lumotini ko'ra olishi kabi)."""
    return payload.get("role", "owner")


def require_roles(*allowed_roles: str):
    """
    Faqat ko'rsatilgan rollarga ruxsat beruvchi dependency yaratadi.
    Foydalanish (istalgan routerda):

        @router.get("/summary")
        def summary(
            ...,
            _: str = Depends(require_roles("owner")),
        ):
            ...

    Yangi rol yoki yangi qoida kerak bo'lsa, FAQAT chaqirilgan joydagi
    ro'yxat o'zgaradi — bu funksiyaning o'zi hech qachon o'zgarmaydi.
    """

    def dependency(role: str = Depends(get_current_user_role)) -> str:
        if role not in allowed_roles:
            raise ForbiddenError(
                f"Bu amal uchun ruxsatingiz yo'q (sizning rolingiz: {role})",
                extra={"required_roles": list(allowed_roles), "your_role": role},
            )
        return role

    return dependency
