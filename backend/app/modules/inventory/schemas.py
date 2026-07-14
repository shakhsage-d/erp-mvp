from pydantic import BaseModel
from typing import Optional


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
    product_id: int
    quantity: float
    reason: Optional[str] = None
