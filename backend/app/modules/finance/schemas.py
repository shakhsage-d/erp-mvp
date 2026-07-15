from pydantic import BaseModel, ConfigDict
from datetime import datetime
from .models import TransactionType


class TransactionOut(BaseModel):
    id: int
    company_id: int
    type: TransactionType
    amount: float
    source: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DailySalesPoint(BaseModel):
    date: str  # "2026-07-15" formatida
    total_income: float
    total_expense: float
