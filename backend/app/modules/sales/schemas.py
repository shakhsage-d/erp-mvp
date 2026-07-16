from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime


class SaleItemCreate(BaseModel):
    product_id: int
    quantity: float = Field(..., gt=0, description="Sotilayotgan miqdor musbat bo'lishi shart")


class SaleCreate(BaseModel):
    # min_length=1 -- Pydantic darajasida ham bo'sh chekni oldini oladi
    # (routerdagi EmptyRequestError esa ikkinchi himoya qatlami sifatida qoladi)
    items: List[SaleItemCreate] = Field(..., min_length=1)
    customer_name: Optional[str] = Field(default=None, max_length=200)
    customer_phone: Optional[str] = Field(default=None, max_length=20)


class SaleOut(BaseModel):
    id: int
    company_id: int
    total_amount: float
    created_at: datetime
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TopProductItem(BaseModel):
    product_id: int
    product_name: str
    total_quantity: float
    total_revenue: float


class TopCustomerItem(BaseModel):
    customer_name: str
    customer_phone: Optional[str] = None
    total_spent: float
    purchase_count: int
