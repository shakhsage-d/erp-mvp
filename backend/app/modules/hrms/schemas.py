from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class ShiftOut(BaseModel):
    id: int
    user_id: int
    clock_in: datetime
    clock_out: Optional[datetime] = None
    duration_hours: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class PayrollResult(BaseModel):
    user_id: int
    shifts_paid: int
    total_hours: float
    hourly_rate: float
    total_amount: float
