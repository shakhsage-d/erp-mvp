from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.core.tenant import get_current_company_id
from app.modules.finance import models, schemas

router = APIRouter(prefix="/finance", tags=["FMS - Moliya"])


@router.get(
    "/transactions",
    response_model=list[schemas.TransactionOut],
    summary="Kirim/chiqim tarixi",
)
def list_transactions(
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
):
    """Barcha pul kirim/chiqimlari tarixi (eng yangisi birinchi) — faqat shu kompaniyaga tegishli."""
    return db.query(models.Transaction).filter(
        models.Transaction.company_id == company_id
    ).order_by(models.Transaction.created_at.desc()).all()


@router.get(
    "/summary",
    summary="Moliyaviy xulosa (kirim/chiqim/foyda)",
)
def summary(
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
):
    """
    Umumiy kirim, chiqim va sof foydani qaytaradi. Dashboard'dagi
    "Moliya xulosasi" bo'limi aynan shu endpointdan ma'lumot oladi.
    """
    income = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.company_id == company_id,
        models.Transaction.type == models.TransactionType.INCOME,
    ).scalar() or 0.0

    expense = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.company_id == company_id,
        models.Transaction.type == models.TransactionType.EXPENSE,
    ).scalar() or 0.0

    return {
        "total_income": income,
        "total_expense": expense,
        "net_profit": income - expense,
    }
