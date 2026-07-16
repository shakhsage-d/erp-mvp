"""
modules/suppliers/models.py
------------------------------
Faza D1: Ta'minotchilar va xarid buyurtmalari (Purchasing).

CHUQUR INTEGRATSIYA: xarid buyurtmasi "qabul qilindi" (received)
deb belgilanganda, bitta amalda:
  1) Har bir mahsulot ombor qoldig'iga qo'shiladi (WMS)
  2) Umumiy summa moliyaga chiqim sifatida yoziladi (FMS)
Bu — xuddi `sales.create_sale` (WMS+FMS) va `pms.checkout_booking`
(PMS+FMS) kabi, uchinchi "chuqur integratsiya" naqshi.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from datetime import datetime
import enum

from app.db.session import Base


class Supplier(Base):
    """Ta'minotchi (kimdan tovar sotib olinadi)."""
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    contact_person = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)


class PurchaseOrderStatus(str, enum.Enum):
    ORDERED = "ordered"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class PurchaseOrder(Base):
    """Bitta ta'minotchiga berilgan xarid buyurtmasi."""
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)

    total_amount = Column(Float, default=0.0, nullable=False)
    status = Column(Enum(PurchaseOrderStatus), default=PurchaseOrderStatus.ORDERED, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    received_at = Column(DateTime, nullable=True)


class PurchaseOrderItem(Base):
    """Xarid buyurtmasidagi har bir mahsulot qatori."""
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
