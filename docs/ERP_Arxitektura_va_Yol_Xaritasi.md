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

> **2026-yil iyul holatiga yangilandi:** Bosqich 0 muvaffaqiyatli yakunlandi (backend, frontend, bot — barchasi bulutda ishlayapti, bir-biri bilan ulangan). Strategik qaror: Telegram bot **vaqtincha to'xtatildi** (kod va modul saqlanadi, kelajakda bildirishnoma/hisobot xizmati sifatida qayta faollashtiriladi). Frontend UI/UX ham vaqtincha orqa planda qoladi. Asosiy e'tibor endi **backend va core arxitekturani mustahkamlashga** qaratiladi — bu keyingi barcha modullar (HRMS, PMS, AI) va yuklama o'sishi uchun poydevor bo'ladi.

### Bosqich 0 — Poydevor ✅ YAKUNLANDI
- Repo modulli tuzilishga ko'chirildi
- PostgreSQL (Supabase) ulandi
- `company_id` filtrlari to'g'rilandi (yozishda ham, o'qishda ham)
- Markaziy `get_current_company_id()` dependency
- Alembic sozlandi
- Backend, frontend, bot — barchasi Render'da bulutda ishga tushirildi

### Bosqich 0.5 — Backend/Core mustahkamlash ✅ YAKUNLANDI
Barcha 8 band bajarildi: xatolik boshqaruvi, validatsiya, logging, testlar (29 ta), rate limiting, health check, API hujjatlari, backup strategiyasi.

### Bosqich 1 — Haqiqiy autentifikatsiya ✅ YAKUNLANDI
- `POST /auth/register`, `POST /auth/login` — JWT token asosida
- Parollar bcrypt bilan xeshlanadi
- `get_current_company_id()` endi tokendan o'qiydi (eski `X-Company-Id` header butunlay olib tashlandi)
- **Dinamik ruxsatlar tizimi**: `Permission`/`Role`/`RolePermission` jadvallari, `require_permission("kod")` — qattiq yozilgan rol nomi emas, bazadagi aniq ruxsatga qarab tekshiradi. Kelajakda "o'z lavozimini yarat" funksiyasi qo'shilganda, faqat yangi CRUD endpoint kerak bo'ladi, tekshiruv mexanizmi o'zgarmaydi.
- Standart lavozimlar: `owner` (hammasi), `cashier` (`sales.create`), `storekeeper` (`inventory.manage`)
- **Frontend/bot vaqtincha ishlamay qoladi** — bu ataylab qabul qilingan qaror: backend/core mustahkamligi ustuvor, frontend o'z bosqichida (Bosqich 2) yangilanadi

### Bosqich 3 — HRMS moduli ✅ YAKUNLANDI
- `modules/hrms/`: xodimlar smenasi (clock-in/clock-out), ish vaqti tarixi
- Yangi ruxsat: `hrms.view_all`
- Boshqa hech qanday modulga tegilmadi — arxitekturaning "sinovi" muvaffaqiyatli o'tdi

### Bosqich 4 — PMS (mehmonxona) moduli ✅ YAKUNLANDI
- `modules/pms/`: xonalar, bronlar, checkout
- **Chuqur integratsiya**: checkout bitta amalda bron yopadi, xonani bo'shatadi VA FMS'ga avtomatik kirim yozadi (xuddi `sales` moduli inventory+finance'ni bog'laganidek)
- Yangi lavozim: `receptionist` (`pms.manage` ruxsati bilan)
- 52 ta test — barchasi o'tdi

### Bosqich 2 — Frontend UI/UX (endi bu bosqichga surildi)
- Professional dizayn, React'ga o'tish (agar kerak bo'lsa)
- Backend'ga tegilmaydi — API allaqachon tayyor turadi

### Bosqich 4 — PMS (mehmonxona) moduli
### Bosqich 5 — Rasmiy integratsiyalar (fiskal, Asl Belgisi, IKPU, to'lov tizimlari)
### Bosqich 6 — AI qo'shimchalari
### Bosqich 7 — Telegram bot qayta faollashtiriladi (bildirishnoma/hisobot xizmati sifatida) + mobil ilova

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