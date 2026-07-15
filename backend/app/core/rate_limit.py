"""
core/rate_limit.py
--------------------
Bitta IP yoki foydalanuvchidan haddan tashqari ko'p so'rov kelishining
oldini oladi (masalan, xato konfiguratsiyalangan bot yoki niyati buzuq
odam serverni "cho'ktirib qo'ymasligi" uchun).

ERP 2.0 YANGILANISHI — endi ikki xil "kalit" bo'yicha cheklanadi:
  - Agar so'rovda haqiqiy (login qilingan) foydalanuvchi tokeni bo'lsa —
    cheklov FOYDALANUVCHI ID'si bo'yicha qo'llaniladi.
  - Aks holda (masalan /auth/login, /auth/register — hali token yo'q) —
    eski kabi IP manzili bo'yicha.

Nega bu muhim: eski usulda (faqat IP) bitta ofisdagi barcha xodimlar
(bitta umumiy Wi-Fi/router orqali chiqadigan) BIR XIL IP'ga ega bo'lib,
bir-birining chegarasini "yeb qo'yishi" mumkin edi. Endi har bir
xodimning o'z alohida chegarasi bor — offisdagi boshqalar band
qilmagan taqdirda ham.
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.security import decode_access_token


def rate_limit_key(request: Request) -> str:
    """
    Avval tokendan foydalanuvchi ID'sini olishga urinadi (agar
    autentifikatsiyadan o'tgan bo'lsa). Bo'lmasa, IP manziliga
    qaytadi. Token yaroqsiz/eskirgan bo'lsa ham xatoga olib kelmaydi —
    bu yerda faqat "kalit" tanlanadi, haqiqiy autentifikatsiya
    tekshiruvi boshqa joyda (core/tenant.py) amalga oshadi.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass  # token yaroqsiz — IP'ga tushamiz

    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=rate_limit_key)
