from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    barcode: Optional[str] = Field(default=None, max_length=64)
    unit: str = Field(default="dona", max_length=20)
    purchase_price: float = Field(default=0.0, ge=0, le=1_000_000_000)
    sale_price: float = Field(default=0.0, ge=0, le=1_000_000_000)
    quantity: float = Field(default=0.0, ge=0)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Mahsulot nomi bo'sh bo'lishi mumkin emas")
        return v


class ProductOut(ProductCreate):
    id: int
    company_id: int

    model_config = ConfigDict(from_attributes=True)


class StockInRequest(BaseModel):
    product_id: int
    quantity: float = Field(..., gt=0, description="Kirim miqdori musbat bo'lishi shart")
    reason: Optional[str] = Field(default=None, max_length=255)
