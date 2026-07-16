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
from app.core.audit_log import record_audit
from app.modules.hrms import models, schemas
from app.modules.auth import models as auth_models
from app.modules.finance import models as finance_models

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


@router.post(
    "/payroll/pay/{user_id}",
    response_model=schemas.PayrollResult,
    summary="Ish haqini hisoblash va to'lash (HRMS + FMS integratsiyasi)",
)
def pay_employee(
    user_id: int,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    actor_id: int = Depends(get_current_user_id),
    _: None = Depends(require_permission("hrms.manage")),
):
    """
    Xodimning hali TO'LANMAGAN, yopilgan (clock_out mavjud) barcha
    smenalarini yig'ib, `hourly_rate` bo'yicha ish haqini hisoblaydi,
    natijani bitta amalda:
      1) FMS'ga chiqim (Transaction) sifatida yozadi
      2) Shu smenalarni "to'landi" deb belgilaydi (qayta hisoblanmasligi uchun)

    Bu — xuddi Savdo (WMS+FMS) va Checkout (PMS+FMS) kabi, HRMS'ni
    FMS bilan chuqur bog'laydigan integratsiya nuqtasi.
    """
    user = db.query(auth_models.User).filter(
        auth_models.User.id == user_id,
        auth_models.User.company_id == company_id,
    ).first()
    if not user:
        raise NotFoundError("Xodim topilmadi", extra={"user_id": user_id})

    unpaid_shifts = db.query(models.Shift).filter(
        models.Shift.user_id == user_id,
        models.Shift.company_id == company_id,
        models.Shift.clock_out.isnot(None),
        models.Shift.is_paid.is_(False),
    ).all()

    if not unpaid_shifts:
        raise ConflictError("Bu xodim uchun to'lanmagan, yopilgan smena topilmadi")

    total_hours = sum(s.duration_hours or 0 for s in unpaid_shifts)
    total_amount = round(total_hours * user.hourly_rate, 2)

    for shift in unpaid_shifts:
        shift.is_paid = True

    if total_amount > 0:
        db.add(finance_models.Transaction(
            company_id=company_id,
            type=finance_models.TransactionType.EXPENSE,
            amount=total_amount,
            source=f"Ish haqi: {user.full_name} ({total_hours} soat)",
        ))

    record_audit(
        db, company_id, actor_id, "payroll.pay",
        entity_type="user", entity_id=user.id,
        details=f"{user.full_name}: {total_hours} soat, {total_amount} so'm",
    )

    db.commit()

    logger.info(
        "Ish haqi to'landi: company=%s user_id=%s soat=%s summa=%s",
        company_id, user_id, total_hours, total_amount,
    )
    return schemas.PayrollResult(
        user_id=user_id,
        shifts_paid=len(unpaid_shifts),
        total_hours=total_hours,
        hourly_rate=user.hourly_rate,
        total_amount=total_amount,
    )
