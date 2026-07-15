"""
modules/pms/router.py
------------------------
Xonalarni boshqarish va mehmonlarni joylashtirish/chiqarish.

MUHIM: `checkout` funksiyasi — bu fayldagi eng muhim qism. U bitta
so'rovda uchta narsani bajaradi (xuddi `sales.create_sale` kabi):
  1. Bron holatini "checked_out" qiladi
  2. Xonani "available" holatiga qaytaradi
  3. FMS'ga (moliyaga) avtomatik kirim yozadi
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.tenant import get_current_company_id, get_current_user_id
from app.core.permissions import require_permission
from app.core.exceptions import NotFoundError, ConflictError
from app.core.logging_config import get_logger
from app.core.audit_log import record_audit
from app.modules.pms import models, schemas
from app.modules.finance import models as finance_models

router = APIRouter(prefix="/pms", tags=["PMS - Mehmonxona"])
logger = get_logger(__name__)


@router.post(
    "/rooms",
    response_model=schemas.RoomOut,
    summary="Yangi xona qo'shish",
)
def create_room(
    payload: schemas.RoomCreate,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    _: None = Depends(require_permission("pms.manage")),
):
    room = models.Room(company_id=company_id, **payload.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    logger.info("Yangi xona qo'shildi: company=%s room_id=%s", company_id, room.id)
    return room


@router.get(
    "/rooms",
    response_model=list[schemas.RoomOut],
    summary="Xonalar ro'yxati va holati",
)
def list_rooms(
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
):
    """Har qanday autentifikatsiyadan o'tgan foydalanuvchi xonalar
    holatini (bo'shmi/bandmi) ko'ra oladi."""
    return db.query(models.Room).filter(
        models.Room.company_id == company_id,
        models.Room.deleted_at.is_(None),
    ).all()


@router.post(
    "/bookings",
    response_model=schemas.BookingOut,
    summary="Mehmonni xonaga joylashtirish",
)
def create_booking(
    payload: schemas.BookingCreate,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    _: None = Depends(require_permission("pms.manage")),
):
    room = db.query(models.Room).filter(
        models.Room.id == payload.room_id,
        models.Room.company_id == company_id,
    ).first()
    if not room:
        raise NotFoundError("Xona topilmadi", extra={"room_id": payload.room_id})

    if room.status != models.RoomStatus.AVAILABLE:
        raise ConflictError(
            f"Xona {room.room_number} band yoki texnik xizmatda",
            extra={"room_status": room.status.value},
        )

    total_price = room.price_per_night * payload.nights

    booking = models.Booking(
        company_id=company_id,
        room_id=room.id,
        guest_name=payload.guest_name,
        guest_phone=payload.guest_phone,
        nights=payload.nights,
        total_price=total_price,
    )
    room.status = models.RoomStatus.OCCUPIED

    db.add(booking)
    db.commit()
    db.refresh(booking)

    logger.info(
        "Yangi bron: company=%s booking_id=%s room_id=%s summa=%s",
        company_id, booking.id, room.id, total_price,
    )
    return booking


@router.post(
    "/bookings/{booking_id}/checkout",
    response_model=schemas.BookingOut,
    summary="Mehmonni chiqarish (checkout)",
)
def checkout_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    actor_id: int = Depends(get_current_user_id),
    _: None = Depends(require_permission("pms.manage")),
):
    """
    Mehmon xonadan chiqqanda chaqiriladi. Bitta amalda:
    1) Bron "checked_out" qilinadi
    2) Xona "available" holatiga qaytadi
    3) FMS'ga to'lov summasi bo'yicha avtomatik kirim yoziladi
    """
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.company_id == company_id,
    ).first()
    if not booking:
        raise NotFoundError("Bron topilmadi", extra={"booking_id": booking_id})

    if booking.status == models.BookingStatus.CHECKED_OUT:
        raise ConflictError("Bu bron allaqachon yopilgan (checkout qilingan)")

    room = db.query(models.Room).filter(models.Room.id == booking.room_id).first()

    booking.status = models.BookingStatus.CHECKED_OUT
    booking.check_out = datetime.utcnow()
    if room:
        room.status = models.RoomStatus.AVAILABLE

    # --- FMS integratsiyasi: to'lov moliyaga avtomatik kirim sifatida yoziladi ---
    db.add(finance_models.Transaction(
        company_id=company_id,
        type=finance_models.TransactionType.INCOME,
        amount=booking.total_price,
        source=f"Booking #{booking.id} (xona {room.room_number if room else '?'})",
    ))

    record_audit(
        db, company_id, actor_id, "booking.checkout",
        entity_type="booking", entity_id=booking.id,
        details=f"{booking.guest_name}, summa={booking.total_price}",
    )

    db.commit()
    db.refresh(booking)

    logger.info(
        "Checkout: company=%s booking_id=%s summa=%s",
        company_id, booking.id, booking.total_price,
    )
    return booking


@router.get(
    "/bookings",
    response_model=list[schemas.BookingOut],
    summary="Bronlar ro'yxati",
)
def list_bookings(
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    _: None = Depends(require_permission("pms.manage")),
):
    return db.query(models.Booking).filter(
        models.Booking.company_id == company_id,
    ).order_by(models.Booking.check_in.desc()).all()
