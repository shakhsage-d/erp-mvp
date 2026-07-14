from pydantic import BaseModel
from datetime import datetime
from .models import TransactionType


class TransactionOut(BaseModel):
    id: int
    company_id: int
    type: TransactionType
    amount: float
    source: str | None
    created_at: datetime

    class Config:
        from_attributes = True
