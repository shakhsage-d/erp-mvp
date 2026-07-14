"""
core/exceptions.py
--------------------
Tizimning barcha "biznes xatolari" shu yerda belgilangan maxsus klasslar
orqali ko'tariladi (routerlarda to'g'ridan-to'g'ri HTTPException emas).

Nega bu muhim:
  - Har bir modul (inventory, sales, finance, keyinchalik hrms, pms) bir xil
    formatda xato qaytaradi — frontend/bot uchun "bashorat qilinadigan" javob
  - Xato turini (masalan "mahsulot topilmadi" yoki "omborda yetarli emas")
    frontend kod bo'yicha ajrata oladi, matnni tahlil qilishga hojat yo'q
  - Yangi modul yozganda, dasturchi shunchaki shu klasslardan foydalanadi,
    formatni qayta o'ylab chiqarish shart emas
"""


class AppError(Exception):
    """Barcha biznes-xatolarining ota klassi."""

    status_code: int = 400
    code: str = "app_error"

    def __init__(self, message: str, extra: dict | None = None):
        self.message = message
        self.extra = extra or {}
        super().__init__(message)


class NotFoundError(AppError):
    """So'ralgan yozuv topilmadi (yoki boshqa kompaniyaga tegishli)."""
    status_code = 404
    code = "not_found"


class InsufficientStockError(AppError):
    """Omborda so'ralgan miqdorda mahsulot yo'q."""
    status_code = 400
    code = "insufficient_stock"


class EmptyRequestError(AppError):
    """So'rovda bo'lishi shart bo'lgan ma'lumot (masalan chek qatorlari) yo'q."""
    status_code = 400
    code = "empty_request"
