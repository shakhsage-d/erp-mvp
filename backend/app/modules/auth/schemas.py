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
    refresh_token: str
    token_type: str = "bearer"
    company_id: int
    company_name: str
    role: str  # lavozim NOMI (masalan "owner") — ko'rsatish uchun


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LogoutRequest(BaseModel):
    refresh_token: str


class EmployeeCreateRequest(BaseModel):
    """Faqat 'employees.manage' ruxsatiga ega foydalanuvchi chaqira oladi."""
    full_name: str = Field(..., min_length=1, max_length=200)
    phone: str = Field(..., min_length=5, max_length=20)
    password: str = Field(..., min_length=6, max_length=100)
    # Ikkitadan FAQAT BITTASI beriladi: standart lavozim (`role`) YOKI
    # kompaniyaning o'z yaratgan maxsus lavozimi (`custom_role_id`).
    role: Literal["cashier", "storekeeper", "receptionist"] | None = None
    custom_role_id: int | None = Field(default=None, description="Maxsus (o'zi yaratgan) lavozim ID'si")
    hourly_rate: float = Field(default=0.0, ge=0, description="Ish haqi hisoblash uchun, so'm/soat")


class EmployeeOut(BaseModel):
    id: int
    full_name: str
    phone: str
    role: str
    is_active: bool = True
    hourly_rate: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class CompanyOut(BaseModel):
    id: int
    name: str
    business_type: str
    tax_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CompanyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    business_type: str | None = Field(default=None, max_length=50)
    tax_id: str | None = Field(default=None, max_length=50)


class EmployeeUpdateRequest(BaseModel):
    """Barcha maydonlar ixtiyoriy — faqat o'zgartirilishi kerak bo'lganlari yuboriladi."""
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, min_length=5, max_length=20)
    # Bu yerdan ham "owner" ATAYLAB chiqarib qoldirilgan — bu endpoint orqali
    # birortaning ham egaga aylantirib bo'lmaydi.
    role: Literal["cashier", "storekeeper", "receptionist"] | None = None
    custom_role_id: int | None = Field(default=None, description="Maxsus (o'zi yaratgan) lavozim ID'si")
    hourly_rate: float | None = Field(default=None, ge=0)


class BulkDeactivateRequest(BaseModel):
    user_ids: list[int] = Field(..., min_length=1, max_length=100)


class BulkDeactivateResult(BaseModel):
    deactivated_count: int
    skipped_ids: list[int]
