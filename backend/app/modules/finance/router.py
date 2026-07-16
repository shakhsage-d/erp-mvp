from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, or_
from datetime import datetime, timedelta

from app.db.session import get_db
from app.core.tenant import get_current_company_id, get_current_user_id
from app.core.permissions import require_permission
from app.core.pagination import Page, PageParams, paginate, build_page, apply_sort
from app.core.audit_log import record_audit
from app.core.logging_config import get_logger
from app.core.exceptions import NotFoundError
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
    date_from: str | None = Query(default=None, description="YYYY-MM-DD formatida, shu sanadan boshlab"),
    date_to: str | None = Query(default=None, description="YYYY-MM-DD formatida, shu sanagacha"),
    txn_type: str | None = Query(default=None, alias="type", description="'income' yoki 'expense'"),
    _: None = Depends(require_permission("finance.view")),
):
    """
    Barcha pul kirim/chiqimlari tarixi (eng yangisi birinchi) — faqat
    shu kompaniyaga tegishli. `finance.view` ruxsatiga ega
    foydalanuvchilar (standart holatda faqat egasi) ko'ra oladi.
    `?search=...` — manba (`source`) bo'yicha qidiradi, masalan "Sale".
    `?date_from=`, `?date_to=`, `?type=` — kengaytirilgan filtrlar
    (buxgalter/soliq hisoboti uchun).
    """
    query = db.query(models.Transaction).filter(
        models.Transaction.company_id == company_id
    )
    if params.search:
        query = query.filter(models.Transaction.source.ilike(f"%{params.search}%"))
    if date_from:
        query = query.filter(models.Transaction.created_at >= datetime.strptime(date_from, "%Y-%m-%d"))
    if date_to:
        query = query.filter(
            models.Transaction.created_at < datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
        )
    if txn_type:
        query = query.filter(models.Transaction.type == txn_type)

    query = apply_sort(query, params, {
        "amount": models.Transaction.amount,
        "created_at": models.Transaction.created_at,
    }, default_column=models.Transaction.created_at)
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


def process_due_recurring_expenses(db: Session, company_id: int) -> int:
    """
    Shu kompaniya uchun "muddati kelgan" takrorlanuvchi xarajatlarni
    tekshiradi va kerak bo'lganlarini avtomatik yaratadi. Bir oyda
    bitta shablon uchun faqat BITTA marta yaratiladi (`last_generated_month`
    orqali nazorat qilinadi).

    Bu funksiya alohida fon-jarayon (cron) o'rniga, foydalanuvchi
    Moliya sahifasini har safar ochganda (`/finance/summary` orqali)
    chaqiriladi — shuning uchun "avtomatik" ishlaydi, lekin qo'shimcha
    infratuzilma (scheduler, cron) talab qilmaydi.
    """
    today = datetime.utcnow()
    current_month_key = today.strftime("%Y-%m")

    due_templates = db.query(models.RecurringExpense).filter(
        models.RecurringExpense.company_id == company_id,
        models.RecurringExpense.is_active.is_(True),
        models.RecurringExpense.day_of_month <= today.day,
        or_(
            models.RecurringExpense.last_generated_month.is_(None),
            models.RecurringExpense.last_generated_month != current_month_key,
        ),
    ).all()

    for template in due_templates:
        db.add(models.Transaction(
            company_id=company_id,
            type=models.TransactionType.EXPENSE,
            amount=template.amount,
            source=f"{template.source} (avtomatik)",
        ))
        template.last_generated_month = current_month_key

    if due_templates:
        db.commit()

    return len(due_templates)


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
    ruxsatiga ega foydalanuvchilar ko'ra oladi. Chaqirilganda, avval
    muddati kelgan takrorlanuvchi xarajatlar (agar bo'lsa) avtomatik
    yaratiladi.
    """
    process_due_recurring_expenses(db, company_id)

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


@router.post(
    "/recurring-expenses",
    response_model=schemas.RecurringExpenseOut,
    summary="Takrorlanuvchi xarajat shabloni yaratish",
)
def create_recurring_expense(
    payload: schemas.RecurringExpenseCreate,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    actor_id: int = Depends(get_current_user_id),
    _: None = Depends(require_permission("finance.manage")),
):
    """Masalan: har oyning 5-kunida "Ijaraga" nomli xarajat avtomatik yaratilsin."""
    template = models.RecurringExpense(
        company_id=company_id,
        amount=payload.amount,
        source=payload.source,
        day_of_month=payload.day_of_month,
    )
    db.add(template)
    db.flush()

    record_audit(
        db, company_id, actor_id, "recurring_expense.create",
        entity_type="recurring_expense", entity_id=template.id,
        details=f"{payload.source}: {payload.amount} (har oy {payload.day_of_month}-kun)",
    )

    db.commit()
    db.refresh(template)
    return template


@router.get(
    "/recurring-expenses",
    response_model=list[schemas.RecurringExpenseOut],
    summary="Takrorlanuvchi xarajat shablonlari ro'yxati",
)
def list_recurring_expenses(
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    _: None = Depends(require_permission("finance.manage")),
):
    return db.query(models.RecurringExpense).filter(
        models.RecurringExpense.company_id == company_id,
    ).order_by(models.RecurringExpense.day_of_month).all()


@router.post(
    "/recurring-expenses/{template_id}/deactivate",
    response_model=schemas.RecurringExpenseOut,
    summary="Takrorlanuvchi xarajatni to'xtatish",
)
def deactivate_recurring_expense(
    template_id: int,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    _: None = Depends(require_permission("finance.manage")),
):
    template = db.query(models.RecurringExpense).filter(
        models.RecurringExpense.id == template_id,
        models.RecurringExpense.company_id == company_id,
    ).first()
    if not template:
        raise NotFoundError("Shablon topilmadi")

    template.is_active = False
    db.commit()
    db.refresh(template)
    return template


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
