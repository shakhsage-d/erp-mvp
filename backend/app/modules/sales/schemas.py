from pydantic import BaseModel, Field, ConfigDict
from typing import List
from datetime import datetime


class SaleItemCreate(BaseModel):
    product_id: int
    quantity: float = Field(..., gt=0, description="Sotilayotgan miqdor musbat bo'lishi shart")


class SaleCreate(BaseModel):
    # min_length=1 -- Pydantic darajasida ham bo'sh chekni oldini oladi
    # (routerdagi EmptyRequestError esa ikkinchi himoya qatlami sifatida qoladi)
    items: List[SaleItemCreate] = Field(..., min_length=1)


class SaleOut(BaseModel):
    id: int
    company_id: int
    total_amount: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
