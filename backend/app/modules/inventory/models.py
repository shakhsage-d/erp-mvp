"""
modules/inventory/models.py
----------------------------
WMS (Warehouse Management) moduli jadvallari.

MUHIM TUZATISH (avvalgi versiyaga nisbatan):
StockMovement'da endi company_id TO'G'RIDAN-TO'G'RI bor (avval faqat
product_id orqali "bilib olinardi"). Bu ikkinchi himoya qatlami —
agar kimdir kelajakda shu jadvalni join qilmasdan so'rasa (masalan,
umumiy audit-hisobotda), baribir boshqa kompaniya ma'lumoti chiqib
ketmaydi.
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum
from datetime import datetime
import enum

from app.db.session import Base


class Product(Base):
    """Ombordagi/do'kondagi mahsulot."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    barcode = Column(String, index=True, nullable=True)
    unit = Column(String, default="dona")
    purchase_price = Column(Float, default=0.0)
    sale_price = Column(Float, default=0.0)
    quantity = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)


class MovementType(str, enum.Enum):
    IN = "in"
    OUT = "out"


class StockMovement(Base):
    """Har bir ombor harakati tarixi (audit uchun muhim)."""
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)  # YANGI qo'shildi
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    type = Column(Enum(MovementType), nullable=False)
    quantity = Column(Float, nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
