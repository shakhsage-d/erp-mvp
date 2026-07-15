from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class RoomCreate(BaseModel):
    room_number: str = Field(..., min_length=1, max_length=20)
    room_type: str = Field(default="standard", max_length=50)
    price_per_night: float = Field(..., ge=0, le=1_000_000_000)


class RoomOut(RoomCreate):
    id: int
    company_id: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class BookingCreate(BaseModel):
    room_id: int
    guest_name: str = Field(..., min_length=1, max_length=200)
    guest_phone: Optional[str] = Field(default=None, max_length=20)
    nights: int = Field(..., gt=0, le=365)


class BookingOut(BaseModel):
    id: int
    company_id: int
    room_id: int
    guest_name: str
    guest_phone: Optional[str] = None
    nights: int
    total_price: float
    check_in: datetime
    check_out: Optional[datetime] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class OccupancyStats(BaseModel):
    total_rooms: int
    occupied_rooms: int
    occupancy_rate: float  # foizda, masalan 66.7
