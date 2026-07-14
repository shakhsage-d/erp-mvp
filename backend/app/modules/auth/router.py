"""
modules/auth/router.py
------------------------
Ro'yxatdan o'tish va tizimga kirish.

MUHIM: bu — hozircha ENG ODDIY holat (bitta kompaniya = bitta "owner"
foydalanuvchi). Kelajakda (rollar to'liq ishga tushganda) shu modulga
"xodim qo'shish" (`POST /auth/users`, faqat owner chaqira oladi) kabi
qo'shimcha endpointlar qo'shiladi — bu FAYLGA tegilmaydi, mavjud
`register`/`login` o'zgarmaydi.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.logging_config import get_logger
from app.core.rate_limit import limiter
from app.modules.auth import models, schemas
from fastapi import Request

router = APIRouter(prefix="/auth", tags=["Auth - Kirish"])
logger = get_logger(__name__)


@router.post(
    "/register",
    response_model=schemas.TokenResponse,
    summary="Yangi kompaniyani ro'yxatdan o'tkazish",
)
@limiter.limit("10/minute")
def register(
    request: Request,
    payload: schemas.CompanyRegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Yangi kompaniya (do'kon/kafe/mehmonxona) va uning birinchi
    foydalanuvchisini (rol: `owner`) bir vaqtda yaratadi, so'ng
    darhol kirish uchun token qaytaradi (qayta login qilish shart emas).
    """
    existing = db.query(models.User).filter(models.User.phone == payload.phone).first()
    if existing:
        raise ConflictError("Bu telefon raqami bilan foydalanuvchi allaqachon ro'yxatdan o'tgan")

    company = models.Company(name=payload.company_name, business_type=payload.business_type)
    db.add(company)
    db.flush()  # company.id ni olish uchun

    user = models.User(
        company_id=company.id,
        full_name=payload.owner_full_name,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
        role="owner",
    )
    db.add(user)
    db.commit()
    db.refresh(company)
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "company_id": company.id, "role": user.role})
    logger.info("Yangi kompaniya ro'yxatdan o'tdi: company_id=%s name=%s", company.id, company.name)

    return schemas.TokenResponse(
        access_token=token, company_id=company.id, company_name=company.name, role=user.role,
    )


@router.post(
    "/login",
    response_model=schemas.TokenResponse,
    summary="Tizimga kirish",
)
@limiter.limit("10/minute")
def login(
    request: Request,
    payload: schemas.LoginRequest,
    db: Session = Depends(get_db),
):
    """Telefon raqami va parol orqali kirish, javobida JWT token qaytadi."""
    user = db.query(models.User).filter(
        models.User.phone == payload.phone,
        models.User.deleted_at.is_(None),
    ).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        logger.warning("Muvaffaqiyatsiz login urinishi: phone=%s", payload.phone)
        raise UnauthorizedError("Telefon raqami yoki parol noto'g'ri")

    company = db.query(models.Company).filter(models.Company.id == user.company_id).first()

    token = create_access_token({"sub": str(user.id), "company_id": user.company_id, "role": user.role})
    logger.info("Kirish muvaffaqiyatli: company_id=%s user_id=%s", user.company_id, user.id)

    return schemas.TokenResponse(
        access_token=token, company_id=user.company_id, company_name=company.name, role=user.role,
    )
