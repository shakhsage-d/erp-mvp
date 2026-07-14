"""
core/tenant.py
--------------
MUHIM FAYL — MULTI-TENANCY NING YURAGI.

QOIDA: Har bir router (inventory, sales, finance, hrms, pms...) mahsulot,
tranzaksiya yoki boshqa yozuvni O'QIGANDA HAM, YOZGANDA HAM shu yerdagi
get_current_company_id() funksiyasidan foydalanadi. Hech qachon
routerning o'zida "company_id = 1" kabi qattiq yozilmaydi va hech qachon
company_id filtri o'tkazib yuborilmaydi.

Nega bu markazlashtirilgan:
Auth (login) tizimi qo'shilganda, FAQAT SHU BITTA FUNKSIYA ichini
o'zgartirasiz. Inventory, sales, finance, hrms, pms — birortasiga ham
tegilmaydi. Shuning uchun yangi modul qo'shganda dasturchi
"company_id filtrini unutib qo'yish" xatosini qila olmaydi — chunki
filtr bu funksiyaga bog'liq, har bir joyda qayta yozilmaydi.
"""

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.db.session import get_db

# ---------------------------------------------------------------------------
# HOZIRGI HOLAT (auth hali yo'q — Bosqich 0/1):
# Har bir so'rovda "X-Company-Id" header orqali company_id yuboriladi.
# Bu SQLite'dagi "DEMO_COMPANY_ID = 1" ga qaraganda ancha yaxshi, chunki:
#   - endi bir nechta kompaniyani PARALLEL sinab ko'rish mumkin (masalan,
#     2-3 ta pilot do'konni bitta demo'da, bir-biridan ajratilgan holda)
#   - kod tuzilishi Bosqich 1 (haqiqiy JWT auth) ga tayyor turadi —
#     pastdagi funksiya ichi almashtiriladi, tashqarisi o'zgarmaydi
# ---------------------------------------------------------------------------
def get_current_company_id(
    x_company_id: int = Header(default=1, alias="X-Company-Id"),
) -> int:
    """
    Hozircha: so'rov header'idan o'qiydi (test/demo uchun qulay).
    BOSQICH 1 da bu funksiya ichi shunga o'zgaradi:

        def get_current_company_id(
            current_user: User = Depends(get_current_user),  # JWT dan
        ) -> int:
            return current_user.company_id

    Routerlarda HECH NARSA o'zgarmaydi — ular baribir
    `Depends(get_current_company_id)` chaqiradi.
    """
    return x_company_id


def get_db_session() -> Session:
    """Qulaylik uchun qayta eksport (routerlarda bitta joydan import qilish uchun)."""
    return Depends(get_db)
