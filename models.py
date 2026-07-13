"""
models.py
---------
Bu yerda barcha jadvallar (modullar) tavsiflanadi.
MUHIM ARXITEKTURA QOIDASI: Har bir do'kon/kafe/mehmonxona — "Company" (Tenant).
Ya'ni bitta dasturiy kod, LEKIN har bir mijozning ma'lumoti alohida ajratiladi
(company_id orqali). Bu — SaaS (bitta tizim, ko'p mijoz) qurishning standart usuli.

Modullar orasidagi bog'liqlik shu faylda ko'rinadi:
- WMS (Product, StockMovement) -> Sale bilan bog'lanadi
- Sale -> FMS (Transaction) avtomatik yaratadi
Bu ikkalasi bitta DB'da bo'lgani uchun ular orasida "integratsiya" qilishning
hojati yo'q — ular allaqachon bir joyda, faqat mantiq bilan bog'laymiz.
"""

from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey, DateTime, Enum
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database import Base


class Company(Base):
    """Har bir mijoz-biznes (do'kon, kafe, mehmonxona)."""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    business_type = Column(String, default="retail")  # retail / cafe / hotel
    tax_id = Column(String, nullable=True)  # kelajakda soliq tizimi bilan integratsiya uchun
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="company")
    sales = relationship("Sale", back_populates="company")


class User(Base):
    """Tizim foydalanuvchilari (do'kon egasi, sotuvchi, ombor xodimi)."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    full_name = Column(String, nullable=False)
    phone = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="owner")  # owner / cashier / storekeeper


# ---------- WMS (Omborni boshqarish) moduli ----------

class Product(Base):
    """Ombordagi/do'kondagi mahsulot."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    name = Column(String, nullable=False)
    barcode = Column(String, index=True, nullable=True)
    unit = Column(String, default="dona")  # dona, kg, litr...
    purchase_price = Column(Float, default=0.0)  # kelish narxi
    sale_price = Column(Float, default=0.0)      # sotish narxi
    quantity = Column(Float, default=0.0)        # joriy qoldiq (stock)

    company = relationship("Company", back_populates="products")


class MovementType(str, enum.Enum):
    IN = "in"    # kirim (yangi tovar keldi)
    OUT = "out"  # chiqim (sotildi yoki ishdan chiqdi)


class StockMovement(Base):
    """Har bir ombor harakati tarixi (audit uchun juda muhim)."""
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    type = Column(Enum(MovementType), nullable=False)
    quantity = Column(Float, nullable=False)
    reason = Column(String, nullable=True)  # masalan: "Sale #12" yoki "Yetkazib beruvchidan kirim"
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------- Savdo + FMS (Moliya) moduli ----------

class Sale(Base):
    """Har bir chek (savdo)."""
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    total_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Kelajakda shu yerga fiscal_check_id qo'shiladi (davlat OFD tizimi integratsiyasi uchun)

    company = relationship("Company", back_populates="sales")
    items = relationship("SaleItem", back_populates="sale")


class SaleItem(Base):
    """Chekdagi har bir mahsulot qatori."""
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)

    sale = relationship("Sale", back_populates="items")


class TransactionType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"


class Transaction(Base):
    """FMS moduli: har qanday pul kirimi/chiqimi shu yerda saqlanadi."""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    source = Column(String, nullable=True)  # masalan: "Sale #12"
    created_at = Column(DateTime, default=datetime.utcnow)
