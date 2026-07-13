"""
main.py
-------
Ilovaning kirish nuqtasi. Shu faylni ishga tushirasiz:
    uvicorn main:app --reload

Ishga tushgandan keyin http://127.0.0.1:8000/docs manziliga kirsangiz,
FastAPI avtomatik yaratgan interaktiv API dokumentatsiyasini ko'rasiz —
u yerda hech qanday frontend kod yozmasdan barcha endpointlarni sinab ko'rish
mumkin (bu "Swagger UI" deb ataladi).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import Base, engine
from routers import inventory, sales, finance
import models  # noqa: F401  -- jadvallar yaratilishi uchun import qilinishi shart

# Ilova birinchi marta ishga tushganda, kerakli jadvallarni avtomatik yaratadi
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MikroERP API",
    description="Kichik biznes egalari uchun ERP (FMS + WMS) - MVP versiya",
    version="0.1.0",
)

# CORS: demo bosqichida Telegram bot yoki boshqa lokal skriptlar
# to'sqinliksiz so'rov yubora olishi uchun ochiq qoldirilgan.
# Productionda bu yerga aniq domenlar ro'yxati yoziladi.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Har bir modul o'z routerini olib keladi.
# Telegram bot ham, mobil ilova ham, desktop dastur ham -
# hammasi shu bitta API'ga so'rov yuboradi. Bu - "single source of truth".
app.include_router(inventory.router)
app.include_router(sales.router)
app.include_router(finance.router)

# Web dashboard shu backendning o'zidan xizmat qiladi (alohida server kerak emas)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root():
    """Web dashboard - brauzerda ochiladi."""
    return FileResponse("static/index.html")


# --- Demo uchun boshlang'ich ma'lumot yaratish (faqat birinchi ishga tushganda) ---
@app.on_event("startup")
def seed_demo_data():
    from database import SessionLocal
    db = SessionLocal()
    try:
        if not db.query(models.Company).first():
            company = models.Company(id=1, name="Namuna Do'kon", business_type="retail")
            db.add(company)
            db.commit()
    finally:
        db.close()
