from pydantic import BaseModel
from typing import List
from datetime import datetime


class SaleItemCreate(BaseModel):
    product_id: int
    quantity: float


class SaleCreate(BaseModel):
    items: List[SaleItemCreate]


class SaleOut(BaseModel):
    id: int
    company_id: int
    total_amount: float
    created_at: datetime

    class Config:
        from_attributes = True
