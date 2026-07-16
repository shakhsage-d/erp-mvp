from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum, Boolean
from datetime import datetime
import enum

from app.db.session import Base


class TransactionType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"


class Transaction(Base):
    """FMS moduli: har qanday pul kirimi/chiqimi shu yerda saqlanadi."""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    source = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RecurringExpense(Base):
    """
    Har oy takrorlanadigan xarajat shabloni (masalan "Ijaraga", "Internet").

    AVTOMATIK ISHLASH MEXANIZMI: alohida fon-jarayon (cron/scheduler)
    yo'q — buning o'rniga, har safar `/finance/summary` chaqirilganda
    (ya'ni egasi Moliya sahifasini ochganda), tizim "shu oy uchun hali
    yaratilmagan takrorlanuvchi xarajatlar bormi" deb tekshiradi va
    kerak bo'lsa avtomatik yaratadi. Bu — infratuzilma talab qilmaydigan,
    lekin foydalanuvchi uchun "o'zi ishlaydi" taassurotini beruvchi
    oddiy va ishonchli yechim.
    """
    __tablename__ = "recurring_expenses"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    source = Column(String, nullable=False)
    day_of_month = Column(Integer, nullable=False)  # 1-28 (oy oxiri muammosidan qochish uchun)
    is_active = Column(Boolean, default=True, nullable=False)
    last_generated_month = Column(String, nullable=True)  # "2026-07" formatida
    created_at = Column(DateTime, default=datetime.utcnow)
