# MikroERP — Arxitektura Ramkasi va Rivojlanish Yo'l Xaritasi

*Bu hujjat — loyihaning "yagona haqiqat manbai" (single source of truth). Har bir yangi funksiya, modul yoki texnik qaror shu ramka asosida tekshiriladi. Demo emas — bu hozirdan boshlab asta-sekin haqiqiy mahsulotga aylanadigan tizimning konstitutsiyasi.*

---

## 1. Umumiy falsafa (nega bu ramka kerak)

Tizim demo'dan boshlab, bekitilmagan holda o'sib boradi — qayta yozilmaydi. Buning uchun uchta printsipga qat'iy rioya qilinadi:

1. **Multi-tenant boshidanoq** — har bir yozuv qaysi kompaniyaga tegishli ekani aniq bo'ladi, hech qachon keyinga qoldirilmaydi.
2. **Modulli, vertikal kesim** — har bir biznes-modul (ombor, moliya, kadrlar, mehmonxona) o'z ichida to'liq, boshqasiga tegmasdan qo'shilishi/olib tashlanishi mumkin.
3. **API-first** — backend hech qachon frontend yoki botga "qattiq bog'lanmaydi". Web, Telegram bot, mobil ilova — hammasi bir xil API bilan gaplashadi.

---

## 2. Repo va papka tuzilishi (monorepo)

```
erp-system/
├── backend/
│   ├── app/
│   │   ├── main.py                 # Faqat routerlarni ulaydi, mantiq yo'q
│   │   ├── core/
│   │   │   ├── config.py           # .env o'qish, sozlamalar
│   │   │   ├── security.py         # JWT, parol hash
│   │   │   ├── tenant.py           # get_current_company_id() — MARKAZIY joy
│   │   │   └── audit.py            # Har bir muhim amalni yozib boruvchi umumiy funksiya
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   └── session.py          # PostgreSQL ulanish
│   │   ├── modules/
│   │   │   ├── auth/               # Company, User, login
│   │   │   ├── inventory/          # WMS
│   │   │   ├── finance/            # FMS
│   │   │   ├── hrms/               # Bosqich 3 da to'ldiriladi
│   │   │   └── pms/                # Bosqich 4 da to'ldiriladi
│   │   └── tests/
│   ├── alembic/                    # Baza migratsiyalari (versiyalangan)
│   ├── requirements.txt
│   └── .env.example
├── frontend/                       # React/Next.js web dashboard
│   ├── src/{pages,components,api}
│   └── package.json
├── bot/                            # Telegram bot — alohida jarayon
│   ├── handlers/
│   └── bot.py
├── mobile/                         # Bosqich 5+ da ochiladi (React Native)
└── docs/
    └── ERP_Arxitektura_va_Yol_Xaritasi.md   # aynan shu fayl
```

**Qoida:** yangi modul qo'shilganda faqat `modules/<yangi_nom>/` papkasi ochiladi va `main.py`da bitta qator qo'shiladi. Boshqa hech narsaga tegilmaydi.

---

## 3. Multi-tenancy qoidasi (hech qachon buzilmaydi)

- Har bir biznes-jadvalda **majburiy** `company_id` ustuni bo'ladi (child-jadvallarda ham — `StockMovement`, `SaleItem` kabi).
- Ma'lumot **yozilganda ham, o'qilganda ham** `company_id` filtri bo'lishi shart. Faqat yozishda bo'lib, o'qishda yo'qligi — xavfsizlik teshigi hisoblanadi.
- Filtr har doim `core/tenant.py`dagi bitta markaziy funksiya (`get_current_company_id`) orqali olinadi, hech qachon routerlarda alohida-alohida yozilmaydi.
- Hozircha (auth yo'q paytda) bu funksiya `1` qaytaradi. Auth qo'shilganda **faqat shu bitta funksiya** o'zgaradi, boshqa hech qaysi fayl o'zgarmaydi.

---

## 4. Ma'lumotlar bazasi qoidalari

- **PostgreSQL** — SQLite'dan boshidanoq voz kechiladi (demo bosqichida ham).
- **Alembic** — har bir jadval o'zgarishi migratsiya sifatida yoziladi, hech qachon bazaga "qo'lda" o'zgartirish kiritilmaydi.
- Har bir jadvalda: `created_at`, `updated_at`, `deleted_at` (soft delete — hech narsa butunlay o'chirilmaydi).
- Pul qiymatlari — `Numeric`/`Decimal` turida, `Float`da emas (hisoblash xatolarining oldini olish uchun).
- Har bir muhim amal (narx o'zgarishi, kirim-chiqim, sotuv) — `audit_log` jadvaliga yoziladi: kim, qachon, nima qildi.

---

## 5. Muhitlar (environments) strategiyasi

| Muhit | Maqsad | Infratuzilma |
|---|---|---|
| **Local** | Dasturchi kompyuterida ishlab chiqish | Docker Compose orqali PostgreSQL + backend |
| **Demo/Staging** | Pilot mijozlar, investorlarga ko'rsatish | Render (bepul/arzon tarif) + Supabase (bepul PostgreSQL) |
| **Production** | Haqiqiy pullik mijozlar | Render/DigitalOcean (pullik, doimiy) + Supabase Pro yoki o'z-VPS PostgreSQL |

Muhim: kod bir xil, faqat `.env`dagi ulanish manzillari farq qiladi. Hech qachon muhitga qarab kod shoxobchasi (branch) ko'paytirilmaydi — bitta `main` branch, environment variable orqali boshqariladi.

---

## 6. Rivojlanish bosqichlari (Roadmap)

### Bosqich 0 — Poydevor (hozir, 2-3 hafta)
- Repo'ni yuqoridagi tuzilishga ko'chirish
- SQLite → PostgreSQL (Supabase)
- Barcha jadvallarga `company_id` to'liq va izchil qo'yish (yozishda ham, o'qishda ham)
- Markaziy `get_current_company_id()` dependency
- Alembic sozlash
- **Natija:** kod tartibli, xavfsiz, kengaytirishga tayyor — lekin funksional jihatdan hozirgi demo bilan bir xil

### Bosqich 1 — Haqiqiy autentifikatsiya (3-4 hafta)
- `auth` moduli: Company ro'yxatdan o'tishi, User login (JWT)
- `get_current_company_id()` endi haqiqiy foydalanuvchidan olinadi
- Rollar: egasi / sotuvchi / omborchi
- **Natija:** endi haqiqatan ham ko'p kompaniya bir tizimda, bir-biridan xavfsiz ajratilgan holda ishlashi mumkin — bu birinchi haqiqiy "multi-tenant SaaS" bosqichi

### Bosqich 2 — Pilot mijozlar bilan mustahkamlash (4-6 hafta)
- Do'stingizning do'konlarida real foydalanish
- Ombor ogohlantirishlari (tugab qolish haqida)
- Bir nechta filial/nuqta qo'llab-quvvatlash
- Metrikalar yig'ish (kunlik faollik, xatolar)

### Bosqich 3 — HRMS moduli (6-8 hafta)
- `modules/hrms/`: xodimlar, smena, ish haqi
- Ombor/savdo modullariga tegmasdan qo'shiladi — bu bosqich aynan arxitekturaning "sinovi"

### Bosqich 4 — PMS (mehmonxona) moduli
- Xona bron qilish, mehmon hisobi — alohida modul sifatida

### Bosqich 5 — Rasmiy integratsiyalar
- Fiskal kassa/OFD, Asl Belgisi, IKPU, Click/Payme
- Faqat shu bosqichda kerak — pullik mijozlar paydo bo'lganda

### Bosqich 6 — AI qo'shimchalari
- Chek/faktura OCR, sotuv bashorati, anomaliya aniqlash

### Bosqich 7 — Mobil ilova
- `mobile/` — React Native, mavjud API'dan foydalanadi, backend o'zgarmaydi

---

## 7. Har bir bosqichda tekshiriladigan savollar (checklist)

Yangi funksiya qo'shishdan oldin har safar so'rang:
- [ ] Yangi jadvalda `company_id` bormi?
- [ ] Yozuvni o'qiyotganda ham `company_id` bo'yicha filtr bormi?
- [ ] Bu funksiya alohida modul papkasida joylashganmi, mavjud modullarga aralashib ketmadimi?
- [ ] Muhim amal audit-log'ga yozildimi?
- [ ] Migratsiya (Alembic) yaratildimi?
- [ ] Bu o'zgarish boshqa modullarning testlarini buzmadimi?

---

## 8. Keyingi darhol qadam

Bosqich 0'dan boshlanadi: repo tuzilishini ko'chirish, PostgreSQL'ga o'tish, `company_id` filtrlarini to'g'irlash. Bu tugagach, hujjatning shu bo'limi belgilanadi va Bosqich 1'ga o'tiladi.
