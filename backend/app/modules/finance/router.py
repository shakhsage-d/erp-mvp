from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timedelta

from app.db.session import get_db
from app.core.tenant import get_current_company_id, get_current_user_id
from app.core.permissions import require_permission
from app.core.pagination import Page, PageParams, paginate, build_page
from app.core.audit_log import record_audit
from app.core.logging_config import get_logger
from app.modules.finance import models, schemas

router = APIRouter(prefix="/finance", tags=["FMS - Moliya"])
logger = get_logger(__name__)


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


@router.post(
    "/expenses",
    response_model=schemas.TransactionOut,
    summary="Xarajat (chiqim) qo'lda qo'shish",
)
def create_expense(
    payload: schemas.ExpenseCreate,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    actor_id: int = Depends(get_current_user_id),
    _: None = Depends(require_permission("finance.manage")),
):
    """
    Ijaraga, kommunal xizmatlarga, ish haqiga va h.k. — avtomatik
    yozilmaydigan har qanday xarajatni qo'lda kiritish uchun.
    Savdo/checkout kabi avtomatik kirim yozuvlaridan farqli, bu yerda
    foydalanuvchi bevosita summani va sababni kiritadi.
    """
    transaction = models.Transaction(
        company_id=company_id,
        type=models.TransactionType.EXPENSE,
        amount=payload.amount,
        source=payload.source,
    )
    db.add(transaction)
    db.flush()

    record_audit(
        db, company_id, actor_id, "expense.create",
        entity_type="transaction", entity_id=transaction.id,
        details=f"{payload.source}: {payload.amount}",
    )

    db.commit()
    db.refresh(transaction)

    logger.info(
        "Xarajat qo'shildi: company=%s amount=%s source=%s",
        company_id, payload.amount, payload.source,
    )
    return transaction


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


@router.get(
    "/analytics/daily-sales",
    response_model=list[schemas.DailySalesPoint],
    summary="Kunlik savdo dinamikasi (grafik uchun)",
)
def daily_sales_analytics(
    days: int = Query(default=30, ge=1, le=365, description="Necha kunlik tarix"),
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    _: None = Depends(require_permission("finance.view")),
):
    """
    Har bir kun uchun umumiy kirim/chiqim — dashboard'da chiziqli
    grafik chizish uchun mo'ljallangan. Kunlar bo'yicha guruhlangan.
    """
    since = datetime.utcnow() - timedelta(days=days)

    rows = (
        db.query(
            func.date(models.Transaction.created_at).label("day"),
            func.sum(case(
                (models.Transaction.type == models.TransactionType.INCOME, models.Transaction.amount),
                else_=0,
            )).label("income"),
            func.sum(case(
                (models.Transaction.type == models.TransactionType.EXPENSE, models.Transaction.amount),
                else_=0,
            )).label("expense"),
        )
        .filter(
            models.Transaction.company_id == company_id,
            models.Transaction.created_at >= since,
        )
        .group_by("day")
        .order_by("day")
        .all()
    )

    return [
        schemas.DailySalesPoint(
            date=str(row.day),
            total_income=float(row.income or 0),
            total_expense=float(row.expense or 0),
        )
        for row in rows
    ]
