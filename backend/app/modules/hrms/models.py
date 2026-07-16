"""
modules/hrms/models.py
------------------------
HRMS moduli — Bosqich 3. Xodimlar smenasi (ish boshlash/tugatish) va
ish vaqti tarixi. Kelajakda shu yerga ish haqi (Payroll) jadvali ham
qo'shiladi (Bosqich 3.1).

E'TIBOR: bu modul `auth.User`ga bog'lanadi (har bir xodim allaqachon
User sifatida mavjud — HRMS uni "qayta yaratmaydi", faqat ish vaqti
ma'lumotini qo'shadi).
"""

from sqlalchemy import Column, Integer, DateTime, ForeignKey, Float, Boolean
from datetime import datetime

from app.db.session import Base


class Shift(Base):
    """Bitta xodimning bitta ish smenasi (kirish va chiqish vaqti)."""
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    clock_in = Column(DateTime, default=datetime.utcnow, nullable=False)
    clock_out = Column(DateTime, nullable=True)  # NULL = smena hali davom etyapti

    # Smena yopilganda avtomatik hisoblanadi (soat, kasr bilan) — hisobotlar
    # uchun har safar qayta hisoblab o'tirmaslik uchun saqlab qo'yiladi.
    duration_hours = Column(Float, nullable=True)

    # Ish haqi hisoblanganda True bo'ladi — bir smena uchun ikki marta
    # to'lov qilinmasligi uchun (HRMS<->FMS integratsiyasi).
    is_paid = Column(Boolean, default=False, nullable=False)
