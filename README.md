# MikroERP

Kichik do'kon, kafe va mehmonxonalar uchun WMS + FMS ERP tizimi. Arxitektura va
rivojlanish rejasi uchun qarang: [`docs/ERP_Arxitektura_va_Yol_Xaritasi.md`](docs/ERP_Arxitektura_va_Yol_Xaritasi.md)

## Loyihaning tuzilishi

```
erp-system/
├── backend/     # FastAPI + PostgreSQL — API server
├── frontend/    # Web dashboard (HTML/CSS/JS, kelajakda React)
├── bot/         # Telegram bot
├── mobile/      # Kelajakda: React Native ilova
└── docs/        # Arxitektura va reja hujjatlari
```

Uchalasi (`backend`, `frontend`, `bot`) — mustaqil, alohida ishga tushiriladigan
qismlar. Ular faqat backend API orqali gaplashadi. Frontend yoki botga
o'zgartirish kiritish backendga tegmaydi, va aksincha.

## Ishga tushirish (local, 3 ta terminal)

### 0-qadam: PostgreSQL baza (Supabase, bepul)
1. [supabase.com](https://supabase.com) da bepul loyiha oching
2. Project Settings → Database → Connection string (URI) ni nusxalang

### 1-terminal — Backend

**Windows (PowerShell):**
```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
```
Agar `Activate.ps1` xatolik bersa ("running scripts is disabled"), bir marta shuni ishga tushiring:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```
so'ng qayta:
```powershell
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```
`.env` faylini oching va `DATABASE_URL`ni Supabase manzilingiz bilan almashtiring, so'ng:
```powershell
uvicorn app.main:app --reload
```

**macOS / Linux:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # va DATABASE_URL ni Supabase manzilingiz bilan almashtiring
uvicorn app.main:app --reload
```

Ochiladi: http://127.0.0.1:8000/docs (API hujjatlari)

### 2-terminal — Frontend
Frontend hozircha oddiy statik fayllar — brauzerda to'g'ridan-to'g'ri
`frontend/index.html` ni oching, YOKI qulayroq bo'lishi uchun:

**Windows (PowerShell):**
```powershell
cd frontend
python -m http.server 5500
```

**macOS / Linux:**
```bash
cd frontend
python -m http.server 5500
```

Ochiladi: http://127.0.0.1:5500

`frontend/config.js` dagi `API_BASE` manzili backend qayerda ishlab
turganini ko'rsatadi — kerak bo'lsa shu yerda o'zgartiring.

### 3-terminal — Telegram bot

**Windows (PowerShell):**
```powershell
cd bot
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```
`.env` faylida `TELEGRAM_BOT_TOKEN`ni @BotFather'dan olingan token bilan almashtiring, so'ng:
```powershell
python bot.py
```

**macOS / Linux:**
```bash
cd bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # va TELEGRAM_BOT_TOKEN ni @BotFather'dan olingan token bilan almashtiring
python bot.py
```

## Baza migratsiyalari (Alembic)

Yangi jadval yoki ustun qo'shganda:
```bash
cd backend
alembic revision --autogenerate -m "tavsif"
alembic upgrade head
```

## Muhim arxitektura qoidalari

To'liq tushuntirish: [`docs/ERP_Arxitektura_va_Yol_Xaritasi.md`](docs/ERP_Arxitektura_va_Yol_Xaritasi.md)

Qisqacha:
- Har bir jadvalda `company_id` bo'lishi SHART (multi-tenancy)
- Har bir so'rovda `company_id` filtri O'QISHDA HAM, YOZISHDA HAM qo'llanadi — buni
  `app/core/tenant.py` dagi `get_current_company_id()` orqali qiling, qo'lda emas
- Har bir yangi modul `app/modules/<nom>/` ichida to'liq (models/schemas/router)