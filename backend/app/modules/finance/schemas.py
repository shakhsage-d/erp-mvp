from pydantic import BaseModel, ConfigDict, Field
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


class ExpenseCreate(BaseModel):
    amount: float = Field(..., gt=0, le=1_000_000_000)
    source: str = Field(..., min_length=1, max_length=255, description="Xarajat sababi, masalan 'Ijaraga - iyul'")
