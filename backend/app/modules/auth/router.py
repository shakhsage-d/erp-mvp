"""
modules/auth/router.py
------------------------
Ro'yxatdan o'tish, tizimga kirish va xodim boshqaruvi.

DINAMIK RUXSATLAR: endi `role` oddiy matn emas — har bir foydalanuvchi
`Role` jadvaliga (`role_id` orqali) bog'langan, ruxsatlar esa
`RolePermission` orqali aniqlanadi. Standart lavozimlar (owner/
cashier/storekeeper) `seed.py`da e'lon qilingan va har bir so'rov
bazasida `ensure_seeded()` orqali avtomatik tayyorlanadi.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import get_db
from app.core.security import (
    hash_password, verify_password, create_access_token,
    generate_refresh_token, hash_refresh_token,
)
from app.core.exceptions import ConflictError, UnauthorizedError, ForbiddenError, NotFoundError
from app.core.tenant import get_current_company_id, get_current_user_id
from app.core.permissions import require_permission
from app.core.audit_log import record_audit
from app.core.logging_config import get_logger
from app.core.rate_limit import limiter
from app.modules.auth import models, schemas
from app.modules.auth.seed import ensure_seeded, get_default_role

router = APIRouter(prefix="/auth", tags=["Auth - Kirish"])
logger = get_logger(__name__)


def _issue_tokens(db: Session, user: models.User) -> tuple[str, str]:
    """
    Har bir muvaffaqiyatli login/register'da chaqiriladi: yangi access
    (JWT) va refresh (bazada xeshlangan) tokenlarni yaratadi.
    Qaytaradi: (access_token, refresh_token_xom)
    """
    access_token = create_access_token({
        "sub": str(user.id), "company_id": user.company_id, "role_id": user.role_id,
    })

    raw_refresh, refresh_hash, expires_at = generate_refresh_token()
    db.add(models.RefreshToken(
        user_id=user.id, token_hash=refresh_hash, expires_at=expires_at,
    ))

    return access_token, raw_refresh


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
    foydalanuvchisini (lavozim: `owner`) bir vaqtda yaratadi, so'ng
    darhol kirish uchun token qaytaradi.
    """
    ensure_seeded(db)  # standart lavozim/ruxsat katalogi shu bazada tayyor bo'lishini ta'minlaydi

    existing = db.query(models.User).filter(models.User.phone == payload.phone).first()
    if existing:
        raise ConflictError("Bu telefon raqami bilan foydalanuvchi allaqachon ro'yxatdan o'tgan")

    owner_role = get_default_role(db, "owner")

    company = models.Company(name=payload.company_name, business_type=payload.business_type)
    db.add(company)
    db.flush()  # company.id ni olish uchun

    user = models.User(
        company_id=company.id,
        full_name=payload.owner_full_name,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
        role_id=owner_role.id,
    )
    db.add(user)
    db.flush()  # user.id ni token yaratish uchun olish

    access_token, refresh_token = _issue_tokens(db, user)

    db.commit()
    db.refresh(company)
    db.refresh(user)

    logger.info("Yangi kompaniya ro'yxatdan o'tdi: company_id=%s name=%s", company.id, company.name)

    return schemas.TokenResponse(
        access_token=access_token, refresh_token=refresh_token,
        company_id=company.id, company_name=company.name, role=owner_role.name,
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
    role = db.query(models.Role).filter(models.Role.id == user.role_id).first()

    access_token, refresh_token = _issue_tokens(db, user)
    db.commit()

    logger.info("Kirish muvaffaqiyatli: company_id=%s user_id=%s", user.company_id, user.id)

    return schemas.TokenResponse(
        access_token=access_token, refresh_token=refresh_token,
        company_id=user.company_id, company_name=company.name, role=role.name,
    )


@router.post(
    "/refresh",
    response_model=schemas.RefreshResponse,
    summary="Yangi access token olish (refresh token orqali)",
)
@limiter.limit("30/minute")
def refresh_token_endpoint(
    request: Request,
    payload: schemas.RefreshRequest,
    db: Session = Depends(get_db),
):
    """
    Access token muddati tugaganda (30 daqiqa), foydalanuvchi qayta
    login qilmasdan, shu endpoint orqali yangi access token oladi.

    XAVFSIZLIK: har safar chaqirilganda ESKI refresh token BEKOR
    QILINADI va YANGISI beriladi ("rotation") — agar kimdir eski
    (masalan o'g'irlangan) tokendan foydalanmoqchi bo'lsa, u allaqachon
    bekor qilingan bo'ladi.
    """
    token_hash = hash_refresh_token(payload.refresh_token)
    stored = db.query(models.RefreshToken).filter(
        models.RefreshToken.token_hash == token_hash,
    ).first()

    if (
        not stored
        or stored.revoked_at is not None
        or stored.expires_at < datetime.utcnow()
    ):
        raise UnauthorizedError("Refresh token yaroqsiz, muddati tugagan yoki bekor qilingan")

    user = db.query(models.User).filter(
        models.User.id == stored.user_id,
        models.User.deleted_at.is_(None),
    ).first()
    if not user:
        raise UnauthorizedError("Foydalanuvchi topilmadi yoki faolsizlantirilgan")

    # Eski tokenni bekor qilib, yangisini beramiz (rotation)
    stored.revoked_at = datetime.utcnow()
    new_access_token, new_refresh_token = _issue_tokens(db, user)
    db.commit()

    return schemas.RefreshResponse(access_token=new_access_token, refresh_token=new_refresh_token)


@router.post(
    "/logout",
    summary="Tizimdan chiqish (refresh tokenni bekor qilish)",
)
def logout(
    payload: schemas.LogoutRequest,
    db: Session = Depends(get_db),
):
    """
    Berilgan refresh tokenni bekor qiladi — shundan keyin u orqali
    yangi access token olib bo'lmaydi. Access token (JWT) o'zi hali
    biroz vaqt amal qilishi mumkin (30 daqiqagacha), lekin refresh
    yo'q bo'lgani uchun sessiya davom etolmaydi.

    Token topilmasa/allaqachon bekor bo'lsa ham, xatolik qaytarmaydi —
    natija bir xil ("chiqildi"), bu orqali tokenning bazada bor-yo'qligi
    haqida ma'lumot "sizib chiqmaydi".
    """
    token_hash = hash_refresh_token(payload.refresh_token)
    stored = db.query(models.RefreshToken).filter(
        models.RefreshToken.token_hash == token_hash,
    ).first()
    if stored and stored.revoked_at is None:
        stored.revoked_at = datetime.utcnow()
        db.commit()

    return {"message": "Tizimdan chiqildi"}


@router.post(
    "/users",
    response_model=schemas.EmployeeOut,
    summary="Yangi xodim qo'shish",
)
@limiter.limit("20/minute")
def create_employee(
    request: Request,
    payload: schemas.EmployeeCreateRequest,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    actor_id: int = Depends(get_current_user_id),
    _: None = Depends(require_permission("employees.manage")),
):
    """
    Yangi xodim (sotuvchi yoki omborchi) qo'shadi. Yaratilgan xodim
    keyin o'z telefon raqami va paroli bilan `/auth/login` orqali
    kiradi — lekin faqat o'z lavozimidagi ruxsatlar doirasida
    ishlay oladi.
    """
    existing = db.query(models.User).filter(models.User.phone == payload.phone).first()
    if existing:
        raise ConflictError("Bu telefon raqami bilan foydalanuvchi allaqachon ro'yxatdan o'tgan")

    if payload.custom_role_id:
        role = db.query(models.Role).filter(
            models.Role.id == payload.custom_role_id,
            models.Role.company_id == company_id,  # faqat SHU kompaniyaning o'z lavozimi
        ).first()
        if not role:
            raise NotFoundError("Ko'rsatilgan maxsus lavozim topilmadi")
    elif payload.role:
        role = get_default_role(db, payload.role)
    else:
        raise ConflictError("Lavozim ko'rsatilishi shart (role yoki custom_role_id)")

    user = models.User(
        company_id=company_id,
        full_name=payload.full_name,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
        role_id=role.id,
        hourly_rate=payload.hourly_rate,
    )
    db.add(user)
    db.flush()  # user.id ni audit yozuvi uchun olish

    record_audit(
        db, company_id, actor_id, "employee.create",
        entity_type="user", entity_id=user.id,
        details=f"{user.full_name} ({role.name}) qo'shildi",
    )

    db.commit()
    db.refresh(user)

    logger.info(
        "Yangi xodim qo'shildi: company=%s user_id=%s role=%s",
        company_id, user.id, role.name,
    )
    return schemas.EmployeeOut(
        id=user.id, full_name=user.full_name, phone=user.phone,
        role=role.name, hourly_rate=user.hourly_rate,
    )


@router.get(
    "/users",
    response_model=list[schemas.EmployeeOut],
    summary="Kompaniya xodimlari ro'yxati",
)
def list_employees(
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    _: None = Depends(require_permission("employees.manage")),
):
    """
    Shu kompaniyaga tegishli barcha foydalanuvchilar (egasi + xodimlar).
    Faolsizlantirilganlar ham ko'rsatiladi (`is_active: false` bilan) —
    egasi ularni kerak bo'lsa qayta faollashtira olishi uchun.
    """
    users = db.query(models.User).filter(
        models.User.company_id == company_id,
    ).all()

    role_names = {r.id: r.name for r in db.query(models.Role).all()}

    return [
        schemas.EmployeeOut(
            id=u.id, full_name=u.full_name, phone=u.phone,
            role=role_names.get(u.role_id, "noma'lum"),
            is_active=u.deleted_at is None,
            hourly_rate=u.hourly_rate,
        )
        for u in users
    ]


@router.patch(
    "/users/{user_id}",
    response_model=schemas.EmployeeOut,
    summary="Xodim ma'lumotlarini tahrirlash",
)
def update_employee(
    user_id: int,
    payload: schemas.EmployeeUpdateRequest,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    actor_id: int = Depends(get_current_user_id),
    _: None = Depends(require_permission("employees.manage")),
):
    """
    Xodimning ismi, telefon raqami va/yoki lavozimini o'zgartiradi.
    Faqat shu kompaniyaga tegishli, EGASI BO'LMAGAN foydalanuvchilarga
    qo'llash mumkin (egani bu endpoint orqali o'zgartirib bo'lmaydi).
    """
    user = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.company_id == company_id,
    ).first()
    if not user:
        raise NotFoundError("Xodim topilmadi", extra={"user_id": user_id})

    current_role = db.query(models.Role).filter(models.Role.id == user.role_id).first()
    if current_role and current_role.name == "owner":
        raise ForbiddenError("Kompaniya egasining ma'lumotlarini bu endpoint orqali o'zgartirib bo'lmaydi")

    if payload.phone and payload.phone != user.phone:
        existing = db.query(models.User).filter(
            models.User.phone == payload.phone, models.User.id != user.id,
        ).first()
        if existing:
            raise ConflictError("Bu telefon raqami boshqa foydalanuvchida band")
        user.phone = payload.phone

    if payload.full_name:
        user.full_name = payload.full_name

    if payload.role:
        new_role = get_default_role(db, payload.role)
        user.role_id = new_role.id
    elif payload.custom_role_id:
        new_role = db.query(models.Role).filter(
            models.Role.id == payload.custom_role_id,
            models.Role.company_id == company_id,
        ).first()
        if not new_role:
            raise NotFoundError("Ko'rsatilgan maxsus lavozim topilmadi")
        user.role_id = new_role.id

    if payload.hourly_rate is not None:
        user.hourly_rate = payload.hourly_rate

    record_audit(
        db, company_id, actor_id, "employee.update",
        entity_type="user", entity_id=user.id,
        details=f"{user.full_name} ma'lumotlari yangilandi",
    )

    db.commit()
    db.refresh(user)

    role_name = db.query(models.Role).filter(models.Role.id == user.role_id).first().name
    logger.info("Xodim tahrirlandi: company=%s user_id=%s", company_id, user.id)
    return schemas.EmployeeOut(
        id=user.id, full_name=user.full_name, phone=user.phone,
        role=role_name, is_active=user.deleted_at is None, hourly_rate=user.hourly_rate,
    )


@router.post(
    "/users/{user_id}/deactivate",
    response_model=schemas.EmployeeOut,
    summary="Xodimni faolsizlantirish",
)
def deactivate_employee(
    user_id: int,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    current_user_id: int = Depends(get_current_user_id),
    _: None = Depends(require_permission("employees.manage")),
):
    """
    Xodimni "o'chirmaydi" (ma'lumotlari, tarixi saqlanib qoladi — audit
    uchun muhim), faqat tizimga kira olmaydigan qiladi (`deleted_at`
    belgilanadi). Kerak bo'lsa `/reactivate` orqali qaytarish mumkin.

    Ikkita himoya: o'zingizni faolsizlantira olmaysiz, va kompaniya
    egasini faolsizlantirib bo'lmaydi.
    """
    if user_id == current_user_id:
        raise ForbiddenError("O'zingizni faolsizlantira olmaysiz")

    user = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.company_id == company_id,
    ).first()
    if not user:
        raise NotFoundError("Xodim topilmadi", extra={"user_id": user_id})

    role = db.query(models.Role).filter(models.Role.id == user.role_id).first()
    if role and role.name == "owner":
        raise ForbiddenError("Kompaniya egasini faolsizlantirib bo'lmaydi")

    user.deleted_at = datetime.utcnow()

    record_audit(
        db, company_id, current_user_id, "employee.deactivate",
        entity_type="user", entity_id=user.id,
        details=f"{user.full_name} faolsizlantirildi",
    )

    db.commit()
    db.refresh(user)

    logger.info("Xodim faolsizlantirildi: company=%s user_id=%s", company_id, user.id)
    return schemas.EmployeeOut(
        id=user.id, full_name=user.full_name, phone=user.phone,
        role=role.name if role else "noma'lum", is_active=False, hourly_rate=user.hourly_rate,
    )


@router.post(
    "/users/{user_id}/reactivate",
    response_model=schemas.EmployeeOut,
    summary="Faolsizlantirilgan xodimni qayta faollashtirish",
)
def reactivate_employee(
    user_id: int,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    actor_id: int = Depends(get_current_user_id),
    _: None = Depends(require_permission("employees.manage")),
):
    user = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.company_id == company_id,
    ).first()
    if not user:
        raise NotFoundError("Xodim topilmadi", extra={"user_id": user_id})

    user.deleted_at = None

    record_audit(
        db, company_id, actor_id, "employee.reactivate",
        entity_type="user", entity_id=user.id,
        details=f"{user.full_name} qayta faollashtirildi",
    )

    db.commit()
    db.refresh(user)

    role = db.query(models.Role).filter(models.Role.id == user.role_id).first()
    logger.info("Xodim qayta faollashtirildi: company=%s user_id=%s", company_id, user.id)
    return schemas.EmployeeOut(
        id=user.id, full_name=user.full_name, phone=user.phone,
        role=role.name if role else "noma'lum", is_active=True, hourly_rate=user.hourly_rate,
    )


@router.get(
    "/company",
    response_model=schemas.CompanyOut,
    summary="Kompaniya profilini ko'rish",
)
def get_company(
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
):
    """Har qanday autentifikatsiyadan o'tgan foydalanuvchi o'z kompaniyasi
    profilini ko'ra oladi (faqat ko'rish, tahrirlash uchun ruxsat kerak)."""
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise NotFoundError("Kompaniya topilmadi")
    return company


@router.patch(
    "/company",
    response_model=schemas.CompanyOut,
    summary="Kompaniya profilini tahrirlash",
)
def update_company(
    payload: schemas.CompanyUpdateRequest,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    actor_id: int = Depends(get_current_user_id),
    _: None = Depends(require_permission("company.manage")),
):
    """Kompaniya nomi, biznes turi va soliq ID'sini tahrirlaydi."""
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise NotFoundError("Kompaniya topilmadi")

    if payload.name:
        company.name = payload.name
    if payload.business_type:
        company.business_type = payload.business_type
    if payload.tax_id is not None:
        company.tax_id = payload.tax_id

    record_audit(
        db, company_id, actor_id, "company.update",
        entity_type="company", entity_id=company.id,
        details="Kompaniya profili yangilandi",
    )

    db.commit()
    db.refresh(company)

    logger.info("Kompaniya profili yangilandi: company=%s", company_id)
    return company
