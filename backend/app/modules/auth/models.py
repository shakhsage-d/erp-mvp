"""
modules/auth/models.py
-----------------------
Company — har bir mijoz-biznes (do'kon, kafe, mehmonxona). Bu — "tenant".
User — tizim foydalanuvchisi (do'kon egasi, sotuvchi, ombor xodimi).

Boshqa barcha modullardagi jadvallar (Product, Sale, Transaction, ...)
shu Company'ga company_id orqali bog'lanadi.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime

from app.db.session import Base


class Company(Base):
    """Har bir mijoz-biznes (do'kon, kafe, mehmonxona) — tenant."""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    business_type = Column(String, default="retail")  # retail / cafe / hotel
    tax_id = Column(String, nullable=True)  # kelajakda soliq integratsiyasi uchun
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)  # soft delete


class User(Base):
    """Tizim foydalanuvchilari."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="owner")  # owner / cashier / storekeeper
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
