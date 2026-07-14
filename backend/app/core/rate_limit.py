"""
core/rate_limit.py
--------------------
Bitta IP/kompaniyadan haddan tashqari ko'p so'rov kelishining oldini
oladi (masalan, xato konfiguratsiyalangan bot yoki niyati buzuq odam
serverni "cho'ktirib qo'ymasligi" uchun).

Nega bu muhim, ayniqsa kelajakda:
  - Ko'p mijoz bo'lganda, bitta mijozning muammosi (masalan, uning
    tizimi noto'g'ri sozlanib, sekundiga yuzlab so'rov yuborsa) boshqa
    barcha mijozlarga ta'sir qilmasligi kerak
  - Bepul Render tarifida resurslar cheklangan — bitta manbadan kelgan
    haddan tashqari yuklama butun serverni sekinlashtirishi mumkin

Chegaralar hozircha "erkinroq" qo'yilgan (haqiqiy foydalanuvchi hech
qachon duch kelmaydigan darajada) — maqsad shaxsiy foydalanuvchini
cheklash emas, anomal holatlarning oldini olish.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
