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
    role: str


class EmployeeCreateRequest(BaseModel):
    """Faqat 'owner' chaqira oladi — yangi xodim (sotuvchi/omborchi) qo'shadi."""
    full_name: str = Field(..., min_length=1, max_length=200)
    phone: str = Field(..., min_length=5, max_length=20)
    password: str = Field(..., min_length=6, max_length=100)
    # Bu yerdan "owner" ATAYLAB chiqarib qoldirilgan — bu endpoint orqali
    # ikkinchi egani yaratib bo'lmaydi, faqat xodimlarni.
    role: Literal["cashier", "storekeeper"]


class EmployeeOut(BaseModel):
    id: int
    full_name: str
    phone: str
    role: str

    model_config = ConfigDict(from_attributes=True)
