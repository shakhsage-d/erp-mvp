from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class SupplierCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    contact_person: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=20)
    notes: Optional[str] = Field(default=None, max_length=500)


class SupplierOut(SupplierCreate):
    id: int
    company_id: int

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderItemCreate(BaseModel):
    product_id: int
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    items: List[PurchaseOrderItemCreate] = Field(..., min_length=1)


class PurchaseOrderOut(BaseModel):
    id: int
    company_id: int
    supplier_id: int
    total_amount: float
    status: str
    created_at: datetime
    received_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
