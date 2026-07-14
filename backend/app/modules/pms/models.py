"""
modules/pms/models.py
------------------------
PMS moduli — Bosqich 4. Mehmonxona xonalari va bron qilish (booking).

CHUQUR INTEGRATSIYA: mehmon chiqib ketganda (`checkout`), moliyaga
(`finance.Transaction`) avtomatik kirim yoziladi — xuddi `sales`
moduli `inventory` va `finance`ni bog'laganidek. Bu — loyihaning
eng boshidan maqsad qilingan "WMS+FMS+PMS bitta tizimda, chuqur
bog'langan" g'oyasining amalga oshishi.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from datetime import datetime
import enum

from app.db.session import Base


class RoomStatus(str, enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"


class Room(Base):
    """Mehmonxonadagi bitta xona."""
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    room_number = Column(String, nullable=False)
    room_type = Column(String, default="standard")
    price_per_night = Column(Float, default=0.0)
    status = Column(Enum(RoomStatus), default=RoomStatus.AVAILABLE, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)


class BookingStatus(str, enum.Enum):
    ACTIVE = "active"
    CHECKED_OUT = "checked_out"


class Booking(Base):
    """Bitta mehmonning bitta xonaga joylashishi (kirishdan chiqishgacha)."""
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False, index=True)

    guest_name = Column(String, nullable=False)
    guest_phone = Column(String, nullable=True)

    nights = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)

    check_in = Column(DateTime, default=datetime.utcnow, nullable=False)
    check_out = Column(DateTime, nullable=True)  # NULL = mehmon hali xonada

    status = Column(Enum(BookingStatus), default=BookingStatus.ACTIVE, nullable=False)
