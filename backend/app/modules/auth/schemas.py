from pydantic import BaseModel, Field


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
