from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.core.tenant import get_current_company_id
from app.core.permissions import require_permission
from app.core.pagination import Page, PageParams, paginate, build_page
from app.modules.finance import models, schemas

router = APIRouter(prefix="/finance", tags=["FMS - Moliya"])


@router.get(
    "/transactions",
    response_model=Page[schemas.TransactionOut],
    summary="Kirim/chiqim tarixi (sahifalangan, qidiruv bilan)",
)
def list_transactions(
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    params: PageParams = Depends(),
    _: None = Depends(require_permission("finance.view")),
):
    """
    Barcha pul kirim/chiqimlari tarixi (eng yangisi birinchi) — faqat
    shu kompaniyaga tegishli. `finance.view` ruxsatiga ega
    foydalanuvchilar (standart holatda faqat egasi) ko'ra oladi.
    `?search=...` — manba (`source`) bo'yicha qidiradi, masalan "Sale".
    """
    query = db.query(models.Transaction).filter(
        models.Transaction.company_id == company_id
    )
    if params.search:
        query = query.filter(models.Transaction.source.ilike(f"%{params.search}%"))

    query = query.order_by(models.Transaction.created_at.desc())
    items, total = paginate(query, params)
    return build_page(items, total, params)


@router.get(
    "/summary",
    summary="Moliyaviy xulosa (kirim/chiqim/foyda)",
)
def summary(
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    _: None = Depends(require_permission("finance.view")),
):
    """
    Umumiy kirim, chiqim va sof foydani qaytaradi. `finance.view`
    ruxsatiga ega foydalanuvchilar ko'ra oladi.
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
