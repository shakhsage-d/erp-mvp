"""
app/main.py
-----------
Ilovaning kirish nuqtasi. FAQAT routerlarni ulaydi — biznes-mantiq YO'Q.
Ishga tushirish (backend/ papkasidan turib):
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import Base, engine, SessionLocal

# Har bir modulning models.py faylini import qilish shart —
# shunda SQLAlchemy ularning jadval borligini biladi.
from app.modules.auth import models as auth_models  # noqa: F401
from app.modules.inventory import models as inventory_models  # noqa: F401
from app.modules.sales import models as sales_models  # noqa: F401
from app.modules.finance import models as finance_models  # noqa: F401

from app.modules.inventory.router import router as inventory_router
from app.modules.sales.router import router as sales_router
from app.modules.finance.router import router as finance_router

# Ilova birinchi marta ishga tushganda, kerakli jadvallarni avtomatik yaratadi.
# (Bosqich 0 dan keyin bu o'rniga Alembic migratsiyalari ishlatiladi.)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="Kichik biznes egalari uchun ERP (WMS + FMS + ...) ",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Modullarni ulash. Yangi modul qo'shilganda faqat shu yerga bitta qator qo'shiladi. ---
app.include_router(inventory_router)
app.include_router(sales_router)
app.include_router(finance_router)
# app.include_router(hrms_router)   # Bosqich 3 da ochiladi
# app.include_router(pms_router)    # Bosqich 4 da ochiladi


@app.get("/")
def root():
    return {"status": "ok", "service": settings.APP_NAME}


@app.get("/health")
def health():
    """Render/monitoring uchun — server tirikligini tekshirish."""
    return {"status": "healthy"}


# --- Demo uchun boshlang'ich ma'lumot (faqat 1-kompaniya bo'lmasa yaratiladi) ---
@app.on_event("startup")
def seed_demo_data():
    db = SessionLocal()
    try:
        if not db.query(auth_models.Company).first():
            company = auth_models.Company(id=1, name="Namuna Do'kon", business_type="retail")
            db.add(company)
            db.commit()
    finally:
        db.close()
