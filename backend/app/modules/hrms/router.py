"""
modules/hrms/router.py
------------------------
Xodimlar smenasi: ish boshlash (clock-in), ish tugatish (clock-out),
va ish vaqti tarixi.

RUXSAT MODELI:
  - Clock-in/clock-out — istalgan autentifikatsiyadan o'tgan
    foydalanuvchi O'ZI uchun bajara oladi (maxsus ruxsat kerak emas,
    bu — har bir xodimning oddiy kundalik ishi).
  - "Barcha xodimlarning" tarixini ko'rish — faqat `hrms.view_all`
    ruxsatiga ega bo'lganlar (standart holatda faqat egasi).
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.tenant import get_current_company_id, get_current_user_id
from app.core.permissions import require_permission
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging_config import get_logger
from app.modules.hrms import models, schemas

router = APIRouter(prefix="/hrms", tags=["HRMS - Xodimlar"])
logger = get_logger(__name__)


@router.post(
    "/shifts/clock-in",
    response_model=schemas.ShiftOut,
    summary="Ish smenasini boshlash",
)
def clock_in(
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    user_id: int = Depends(get_current_user_id),
):
    """Xodim ishga kelganda chaqiradi. Agar allaqachon ochiq (yopilmagan)
    smenasi bo'lsa, yangisini boshlab bo'lmaydi — avval o'shani yopish kerak."""
    open_shift = db.query(models.Shift).filter(
        models.Shift.user_id == user_id,
        models.Shift.clock_out.is_(None),
    ).first()
    if open_shift:
        raise ConflictError("Sizda allaqachon boshlangan, yopilmagan smena bor")

    shift = models.Shift(company_id=company_id, user_id=user_id, clock_in=datetime.utcnow())
    db.add(shift)
    db.commit()
    db.refresh(shift)

    logger.info("Smena boshlandi: company=%s user_id=%s shift_id=%s", company_id, user_id, shift.id)
    return shift


@router.post(
    "/shifts/clock-out",
    response_model=schemas.ShiftOut,
    summary="Ish smenasini tugatish",
)
def clock_out(
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    user_id: int = Depends(get_current_user_id),
):
    """Xodim ishdan ketayotganda chaqiradi. Ochiq smena topilib, yopiladi
    va davomiyligi (soatlarda) hisoblab qo'yiladi."""
    shift = db.query(models.Shift).filter(
        models.Shift.user_id == user_id,
        models.Shift.clock_out.is_(None),
    ).first()
    if not shift:
        raise NotFoundError("Boshlangan (ochiq) smena topilmadi")

    shift.clock_out = datetime.utcnow()
    duration_seconds = (shift.clock_out - shift.clock_in).total_seconds()
    shift.duration_hours = round(duration_seconds / 3600, 2)
    db.commit()
    db.refresh(shift)

    logger.info(
        "Smena tugadi: company=%s user_id=%s shift_id=%s davomiyligi=%s soat",
        company_id, user_id, shift.id, shift.duration_hours,
    )
    return shift


@router.get(
    "/shifts/me",
    response_model=list[schemas.ShiftOut],
    summary="O'zimning smenalarim tarixi",
)
def my_shifts(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Har qanday xodim o'zining smena tarixini erkin ko'ra oladi."""
    return db.query(models.Shift).filter(
        models.Shift.user_id == user_id,
    ).order_by(models.Shift.clock_in.desc()).all()


@router.get(
    "/shifts",
    response_model=list[schemas.ShiftOut],
    summary="Barcha xodimlarning smenalari (faqat egasi)",
)
def all_shifts(
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    _: None = Depends(require_permission("hrms.view_all")),
):
    """Kompaniyadagi barcha xodimlarning smena tarixi — faqat
    `hrms.view_all` ruxsatiga ega foydalanuvchilar (standart: egasi)."""
    return db.query(models.Shift).filter(
        models.Shift.company_id == company_id,
    ).order_by(models.Shift.clock_in.desc()).all()
