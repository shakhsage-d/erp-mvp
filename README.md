# MikroERP — Demo (Web + Telegram bot, bitta backend)

Bu versiya avvalgi MVP yadrosi ustiga qurilgan: endi **Web dashboard** va
**Telegram bot** ikkalasi ham bitta FastAPI backendga ulanadi va bitta
ma'lumotlar bazasidan (`erp_demo.db`) foydalanadi — ya'ni **single source
of truth**. Webda qilingan savdo botda ham, botdagi savdo webda ham
darhol ko'rinadi.

```
        ┌──────────────┐
        │ Web Dashboard │ ──┐
        └──────────────┘   │
                            ▼
                   ┌──────────────────┐        ┌──────────────┐
                   │  FastAPI backend  │───────▶│  erp_demo.db  │
                   └──────────────────┘        └──────────────┘
                            ▲
        ┌──────────────┐   │
        │ Telegram bot  │ ──┘
        └──────────────┘
```

## VS Code'da ishga tushirish (2 ta terminal kerak bo'ladi)

### 0-qadam: Bir martalik sozlash

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 1-terminal — Backend + Web dashboard

```bash
uvicorn main:app --reload
```

Brauzerda oching: **http://127.0.0.1:8000** — bu Web dashboard.
API hujjatlari uchun: **http://127.0.0.1:8000/docs**

### 2-terminal — Telegram bot

Avval @BotFather orqali Telegram'da bot yarating va tokenini oling
(bepul, 1 daqiqa vaqt oladi: Telegram'da @BotFather ga `/newbot` yozing).

```bash
export TELEGRAM_BOT_TOKEN="bu_yerga_tokeningizni_qo'ying"    # Windows: set TELEGRAM_BOT_TOKEN=...
python telegram_bot.py
```

Botga Telegram'da yozing: `/start`, `/mahsulotlar`, `/hisobot`, `/sotish 1 3`

## Demo skript (jamoaga ko'rsatish uchun)

1. Webda mahsulot qo'shing (masalan: "Choy", narxi 15000, qoldiq 20)
2. Telegramda `/mahsulotlar` yozing — mahsulot u yerda ham ko'rinadi
3. Telegramda `/sotish 1 2` yozing (2 dona sotish)
4. Webga qayting — bir necha soniyada (avtomatik yangilanish) qoldiq
   18 taga tushganini va "Moliya xulosasi"da tushum paydo bo'lganini ko'rasiz
5. Aksincha — webdagi "Tezkor sotish" formasidan sotib, Telegramda
   `/hisobot` bilan tekshiring

Bu — aynan "bitta backend, ko'p klient" arxitekturasining jonli isboti.

## Papka tuzilishi

```
erp-mvp/
├── main.py              # Backend kirish nuqtasi + Web dashboard xizmati
├── telegram_bot.py       # Telegram bot (backendga so'rov yuboradi, mantiqsiz)
├── database.py            # DB ulanish
├── models.py               # Jadvallar
├── schemas.py                # API validatsiyasi
├── routers/                   # WMS, Savdo, FMS endpointlari
└── static/                     # Web dashboard (HTML/CSS/JS)
    ├── index.html
    ├── style.css
    └── app.js
```

## Keyingi qadam: GitHub'ga o'tish

Demo tayyor bo'lgach, asosiy tizimni GitHub'da boshlashda tavsiya:

```bash
git init
echo "venv/
__pycache__/
*.db
.env" > .gitignore
git add .
git commit -m "Initial MVP: WMS + FMS + Web dashboard + Telegram bot"
```

`TELEGRAM_BOT_TOKEN` kabi maxfiy ma'lumotlarni hech qachon kodga yozmang —
har doim environment variable yoki `.env` fayl orqali bering (va uni
`.gitignore`ga qo'shing).
