"""
routers/finance.py
-------------------
FMS (Financial Management) moduli. Do'kon egasi "bugun qancha pul tushdi?"
degan savolga javob olishi uchun.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

import models
import schemas
from database import get_db

router = APIRouter(prefix="/finance", tags=["FMS - Moliya"])

DEMO_COMPANY_ID = 1


@router.get("/transactions", response_model=list[schemas.TransactionOut])
def list_transactions(db: Session = Depends(get_db)):
    """Barcha pul kirim/chiqimlari tarixi."""
    return db.query(models.Transaction).filter(
        models.Transaction.company_id == DEMO_COMPANY_ID
    ).order_by(models.Transaction.created_at.desc()).all()


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    """Umumiy kirim, chiqim va sof foyda - do'kon egasi uchun eng muhim raqam."""
    income = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.company_id == DEMO_COMPANY_ID,
        models.Transaction.type == models.TransactionType.INCOME,
    ).scalar() or 0.0

    expense = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.company_id == DEMO_COMPANY_ID,
        models.Transaction.type == models.TransactionType.EXPENSE,
    ).scalar() or 0.0

    return {
        "total_income": income,
        "total_expense": expense,
        "net_profit": income - expense,
    }
