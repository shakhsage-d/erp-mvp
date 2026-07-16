"""
modules/roles/router.py
--------------------------
Maxsus lavozim yaratish interfeysi. Backend'dagi dinamik ruxsatlar
tizimi (`Permission`/`Role`/`RolePermission`, Bosqich 1'da qurilgan)
allaqachon TAYYOR — bu fayl shunchaki uni frontendga chiqaradigan
CRUD endpointlarni qo'shadi. Tekshiruv mexanizmining o'zi
(`core/permissions.py`) HECH NARSA o'zgarmadi.
"""

from fastapi import APIRouter, Depends

from app.db.session import get_db
from app.core.tenant import get_current_company_id
from app.core.permissions import require_permission
from app.core.exceptions import ConflictError
from app.core.logging_config import get_logger
from app.modules.auth.models import Role, Permission, RolePermission
from app.modules.auth.seed import ensure_seeded, PERMISSION_CATALOG
from app.modules.roles import schemas

router = APIRouter(tags=["Lavozimlar (Roles)"])
logger = get_logger(__name__)


@router.get(
    "/permissions",
    response_model=list[schemas.PermissionOut],
    summary="Tizimdagi barcha mumkin bo'lgan ruxsatlar ro'yxati",
)
def list_permissions(
    db=Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    _: None = Depends(require_permission("roles.manage")),
):
    """
    Yangi lavozim yaratayotganda, egasi checkbox orqali tanlaydigan
    "mumkin bo'lgan ruxsatlar" ro'yxati. Yangi modul qo'shilganda
    (masalan HRMS'ga yangi ruxsat), bu ro'yxat AVTOMATIK yangilanadi —
    chunki u markaziy `PERMISSION_CATALOG`dan o'qiladi.
    """
    ensure_seeded(db)
    return [schemas.PermissionOut(code=code, description=desc) for code, desc in PERMISSION_CATALOG.items()]


@router.get(
    "/roles",
    response_model=list[schemas.RoleOut],
    summary="Mavjud lavozimlar (standart + maxsus)",
)
def list_roles(
    db=Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    _: None = Depends(require_permission("roles.manage")),
):
    """
    Standart lavozimlar (`company_id=NULL`, barcha kompaniyalar uchun
    umumiy — owner/cashier/storekeeper/receptionist) VA shu
    kompaniyaning o'zi yaratgan maxsus lavozimlarini birga qaytaradi.
    """
    ensure_seeded(db)

    roles = db.query(Role).filter(
        (Role.company_id.is_(None)) | (Role.company_id == company_id),
    ).all()

    permission_by_id = {p.id: p.code for p in db.query(Permission).all()}

    result = []
    for role in roles:
        perm_ids = {
            rp.permission_id
            for rp in db.query(RolePermission).filter(RolePermission.role_id == role.id).all()
        }
        result.append(schemas.RoleOut(
            id=role.id,
            name=role.name,
            is_custom=role.company_id is not None,
            permission_codes=sorted(permission_by_id[pid] for pid in perm_ids if pid in permission_by_id),
        ))
    return result


@router.post(
    "/roles",
    response_model=schemas.RoleOut,
    summary="Yangi maxsus lavozim yaratish",
)
def create_custom_role(
    payload: schemas.RoleCreateRequest,
    db=Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    _: None = Depends(require_permission("roles.manage")),
):
    """
    Egasi o'zi lavozim yaratadi (masalan "Katta sotuvchi" — sotish +
    narx o'zgartirish, lekin xodim qo'shish yo'q). Faqat shu
    kompaniyaga tegishli (`company_id` to'ldirilgan) — boshqa
    kompaniyalarga ko'rinmaydi.
    """
    ensure_seeded(db)

    existing = db.query(Role).filter(
        Role.company_id == company_id, Role.name == payload.name,
    ).first()
    if existing:
        raise ConflictError(f"'{payload.name}' nomli lavozim allaqachon mavjud")

    valid_codes = set(PERMISSION_CATALOG.keys())
    invalid = set(payload.permission_codes) - valid_codes
    if invalid:
        raise ConflictError(f"Noto'g'ri ruxsat kodlari: {', '.join(invalid)}")

    role = Role(company_id=company_id, name=payload.name)
    db.add(role)
    db.flush()

    permission_by_code = {p.code: p for p in db.query(Permission).all()}
    for code in payload.permission_codes:
        db.add(RolePermission(role_id=role.id, permission_id=permission_by_code[code].id))

    db.commit()

    logger.info("Maxsus lavozim yaratildi: company=%s role_id=%s name=%s", company_id, role.id, role.name)
    return schemas.RoleOut(
        id=role.id, name=role.name, is_custom=True,
        permission_codes=sorted(payload.permission_codes),
    )
