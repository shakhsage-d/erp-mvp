"""
modules/audit/models.py
--------------------------
Har bir muhim amal (xodim qo'shildi/faolsizlantirildi, sotuv qilindi,
mehmon chiqarildi va h.k.) shu jadvalga yoziladi.

Nega bu logging'dan farq qiladi: `logging_config.py` orqali yoziladigan
loglar — Render'ning "Logs" bo'limida, faqat matn sifatida, vaqtinchalik
(oylar davomida arxivlanmasligi mumkin). Bu jadval esa — SO'ROV QILINADIGAN,
doimiy saqlanadigan tarix: "o'tgan oyda kim nechta xodim qo'shgan/
o'chirgan" kabi savollarga to'g'ridan-to'g'ri SQL/API orqali javob beradi.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from datetime import datetime

from app.db.session import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Masalan: "employee.deactivate", "sale.create", "booking.checkout"
    action = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=True)  # "user", "sale", "booking", ...
    entity_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)  # erkin matn tavsif

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
