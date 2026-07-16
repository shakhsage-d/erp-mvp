"""
modules/auth/models.py
-----------------------
Company — har bir mijoz-biznes (do'kon, kafe, mehmonxona). Bu — "tenant".
User — tizim foydalanuvchisi (do'kon egasi, sotuvchi, ombor xodimi).

DINAMIK RUXSATLAR TIZIMI (Permission/Role/RolePermission):
Oldin `User.role` oddiy matn edi ("owner", "cashier") va kod ichida
qattiq yozilgan tekshiruvlar (`if role == "owner"`) ishlatilardi. Endi
bu — to'liq jadval asosidagi tizim:

  - `Permission` — tizimda mavjud BARCHA mumkin bo'lgan amallar
    ro'yxati (masalan "sales.create", "finance.view"). Yangi modul
    qo'shilganda, shunchaki yangi Permission qatorlari qo'shiladi.
  - `Role` — lavozim. `company_id=NULL` bo'lsa — bu STANDART,
    barcha kompaniyalar uchun umumiy lavozim (owner/cashier/
    storekeeper). Kelajakda (HRMS bosqichida) `company_id` to'ldirilgan
    MAXSUS lavozimlar ham qo'shiladi — masalan bitta do'kon o'ziga xos
    "Katta sotuvchi" lavozimini yaratishi mumkin bo'ladi.
  - `RolePermission` — qaysi lavozimda qaysi ruxsat borligini
    bog'lovchi jadval (ko'p-ko'pga bog'lanish).

Bu orqali, kelajakda "do'kon egasi o'zi lavozim yaratib, unga
checkbox orqali ruxsat belgilasin" degan funksiya qo'shilganda,
FAQAT yangi CRUD endpointlar qo'shiladi — bu jadval tuzilishi va
tekshiruv mexanizmi (`core/permissions.py`) o'ZGARMAYDI.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Float
from datetime import datetime

from app.db.session import Base


class Company(Base):
    """Har bir mijoz-biznes (do'kon, kafe, mehmonxona) — tenant."""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    business_type = Column(String, default="retail")  # retail / cafe / hotel
    tax_id = Column(String, nullable=True)  # kelajakda soliq integratsiyasi uchun
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)  # soft delete


class Permission(Base):
    """Tizimda mavjud bo'lgan har bir aniq amal (masalan 'sales.create')."""
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)


class Role(Base):
    """
    Lavozim. `company_id IS NULL` — tizim standart lavozimi (barcha
    kompaniyalar uchun umumiy: owner/cashier/storekeeper). Kelajakda
    `company_id` to'ldirilgan qatorlar — bitta kompaniyaga xos maxsus
    lavozimlar (masalan "Katta sotuvchi").
    """
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_role_company_name"),
    )


class RolePermission(Base):
    """Qaysi lavozimda qaysi ruxsat borligini bog'lovchi jadval."""
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )


class User(Base):
    """Tizim foydalanuvchilari. Endi `role` oddiy matn emas, `roles`
    jadvaliga FK (`role_id`) orqali bog'lanadi."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    hourly_rate = Column(Float, default=0.0, nullable=False)  # ish haqi hisoblash uchun (so'm/soat)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)


class RefreshToken(Base):
    """
    Refresh tokenlar — bazada XESHLANGAN holda saqlanadi (xom token
    hech qachon bazaga yozilmaydi). Bu orqali "logout" yoki "token
    o'g'irlandi" holatida uni bekor qilish (revoke) mumkin bo'ladi —
    JWT (access token)dan farqli o'laroq, u bazaga tegmasdan
    tekshiriladi va shu sababli bekor qilib bo'lmaydi.
    """
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
