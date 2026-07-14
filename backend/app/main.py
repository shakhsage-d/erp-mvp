"""
app/main.py
-----------
Ilovaning kirish nuqtasi. FAQAT routerlarni ulaydi — biznes-mantiq YO'Q.
Ishga tushirish (backend/ papkasidan turib):
    uvicorn app.main:app --reload
"""

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.core.error_handlers import register_error_handlers
from app.core.rate_limit import limiter
from app.db.session import Base, engine, SessionLocal

# Logging ENG BIRINCHI sozlanadi — shundan keyin import qilinadigan
# hech qanday modul logsiz qolmaydi.
setup_logging()
logger = get_logger(__name__)

# Har bir modulning models.py faylini import qilish shart —
# shunda SQLAlchemy ularning jadval borligini biladi.
from app.modules.auth import models as auth_models  # noqa: F401,E402
from app.modules.inventory import models as inventory_models  # noqa: F401,E402
from app.modules.sales import models as sales_models  # noqa: F401,E402
from app.modules.finance import models as finance_models  # noqa: F401,E402

from app.modules.inventory.router import router as inventory_router  # noqa: E402
from app.modules.sales.router import router as sales_router  # noqa: E402
from app.modules.finance.router import router as finance_router  # noqa: E402

# Ilova birinchi marta ishga tushganda, kerakli jadvallarni avtomatik yaratadi.
# (Bosqich 0 dan keyin bu o'rniga Alembic migratsiyalari ishlatiladi.)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Kichik do'kon, kafe va mehmonxonalar uchun ERP tizimi API'si.\n\n"
        "**Multi-tenant**: har bir so'rov `X-Company-Id` header'i orqali "
        "qaysi kompaniyaga tegishli ekanini bildiradi (Bosqich 1'da bu "
        "login orqali avtomatik aniqlanadi).\n\n"
        "**Xato formati**: barcha xatolar bir xil ko'rinishda qaytadi:\n"
        "`{\"error\": {\"code\": \"...\", \"message\": \"...\"}}`"
    ),
    version="0.2.0",
    openapi_tags=[
        {
            "name": "WMS - Ombor",
            "description": "Mahsulotlar, ularning qoldig'i va ombor harakatlari (kirim).",
        },
        {
            "name": "Savdo (WMS + FMS integratsiyasi)",
            "description": "Chek yopish — bitta amalda ombor va moliyani birga yangilaydi.",
        },
        {
            "name": "FMS - Moliya",
            "description": "Kirim/chiqim tarixi va moliyaviy xulosa hisobotlari.",
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting — bitta joyda ulanadi, endpointlarda @limiter.limit(...) orqali ishlatiladi
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Boshqa barcha xatolar bilan bir xil formatda javob beradi."""
    logger.warning("Rate limit oshib ketdi: %s %s", request.client.host if request.client else "-", request.url.path)
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "rate_limit_exceeded",
                "message": "Juda ko'p so'rov yuborildi. Birozdan so'ng qayta urinib ko'ring.",
            }
        },
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Har bir HTTP so'rovini bitta qatorda jurnalga yozadi:
    qaysi kompaniya, qaysi endpoint, qancha vaqtda, qaysi natija bilan.
    Render'ning "Logs" bo'limida aynan shu qatorlar ko'rinadi — muammo
    chiqqanda (masalan bitta mijoz shikoyat qilsa) shu yerdan qidirasiz.
    """
    start = time.perf_counter()
    company_id = request.headers.get("X-Company-Id", "-")

    response = await call_next(request)

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "company=%s %s %s -> %s (%.1fms)",
        company_id, request.method, request.url.path,
        response.status_code, duration_ms,
    )
    return response


# Barcha modullar uchun bir xil xato formati — bitta joyda, bir marta.
register_error_handlers(app)

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
    """
    Render/monitoring (masalan UptimeRobot) uchun.

    MUHIM: shunchaki "server jarayoni ishlab turibdimi" emas, balki
    "server HAQIQIY ISHLAY OLADIMI" (ya'ni bazaga ulana oladimi) ni
    tekshiradi. Ikkalasi bir xil emas: server jarayoni tirik bo'lishi
    mumkin, lekin agar baza bilan aloqa uzilgan bo'lsa, u baribir
    hech qanday so'rovga to'g'ri javob bera olmaydi — bunday holatni
    "healthy" deb ko'rsatish yolg'on xotirjamlik beradi.
    """
    db_status = "ok"
    overall_status = "healthy"

    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception as exc:
        db_status = "unreachable"
        overall_status = "unhealthy"
        logger.error("Health check: bazaga ulanib bo'lmadi: %s", exc)

    response_body = {
        "status": overall_status,
        "checks": {"database": db_status},
    }

    if overall_status != "healthy":
        return JSONResponse(status_code=503, content=response_body)
    return response_body


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
