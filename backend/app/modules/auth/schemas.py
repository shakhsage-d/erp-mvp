from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class CompanyRegisterRequest(BaseModel):
    """Yangi kompaniya + uning birinchi foydalanuvchisi (egasi) shu orqali yaratiladi."""
    company_name: str = Field(..., min_length=1, max_length=200)
    business_type: str = Field(default="retail", max_length=50)
    owner_full_name: str = Field(..., min_length=1, max_length=200)
    phone: str = Field(..., min_length=5, max_length=20)
    password: str = Field(..., min_length=6, max_length=100)


class LoginRequest(BaseModel):
    phone: str = Field(..., min_length=5, max_length=20)
    password: str = Field(..., min_length=1, max_length=100)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    company_id: int
    company_name: str
    role: str  # lavozim NOMI (masalan "owner") — ko'rsatish uchun


class EmployeeCreateRequest(BaseModel):
    """Faqat 'employees.manage' ruxsatiga ega foydalanuvchi chaqira oladi."""
    full_name: str = Field(..., min_length=1, max_length=200)
    phone: str = Field(..., min_length=5, max_length=20)
    password: str = Field(..., min_length=6, max_length=100)
    # Hozircha faqat standart 2 ta lavozim tanlanadi. Kelajakda (HRMS
    # bosqichida) bu maydon kompaniyaning o'z maxsus lavozimlaridan
    # birini ham qabul qiladigan bo'ladi (masalan role_id orqali).
    role: Literal["cashier", "storekeeper", "receptionist"]


class EmployeeOut(BaseModel):
    id: int
    full_name: str
    phone: str
    role: str
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class EmployeeUpdateRequest(BaseModel):
    """Barcha maydonlar ixtiyoriy — faqat o'zgartirilishi kerak bo'lganlari yuboriladi."""
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, min_length=5, max_length=20)
    # Bu yerdan ham "owner" ATAYLAB chiqarib qoldirilgan — bu endpoint orqali
    # birortaning ham egaga aylantirib bo'lmaydi.
    role: Literal["cashier", "storekeeper", "receptionist"] | None = None
