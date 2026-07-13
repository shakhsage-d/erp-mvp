"""
schemas.py
----------
Bu "Pydantic" modellari — API orqali kirib-chiqadigan ma'lumotlarning
"formasi"ni belgilaydi. Masalan, mijoz noto'g'ri formatda ma'lumot yuborsa,
FastAPI avtomatik xatolik qaytaradi (bizga qo'lda tekshirish shart emas).
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ProductCreate(BaseModel):
    name: str
    barcode: Optional[str] = None
    unit: str = "dona"
    purchase_price: float = 0.0
    sale_price: float = 0.0
    quantity: float = 0.0


class ProductOut(ProductCreate):
    id: int
    company_id: int

    class Config:
        from_attributes = True


class StockInRequest(BaseModel):
    """Omborga yangi tovar kirim qilish uchun."""
    product_id: int
    quantity: float
    reason: Optional[str] = "Yetkazib beruvchidan kirim"


class SaleItemCreate(BaseModel):
    product_id: int
    quantity: float


class SaleCreate(BaseModel):
    """Kassada bitta chek yopish uchun keladigan so'rov."""
    items: List[SaleItemCreate]


class SaleOut(BaseModel):
    id: int
    total_amount: float
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionOut(BaseModel):
    id: int
    type: str
    amount: float
    source: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
