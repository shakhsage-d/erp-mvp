"""
modules/auth/seed.py
-----------------------
Tizimning "standart katalogi": barcha mumkin bo'lgan ruxsatlar
(`Permission`) va standart lavozimlar (`Role`, `company_id=NULL`)
shu yerda ANIQ va MARKAZIY ro'yxat sifatida saqlanadi.

Yangi modul (masalan HRMS) qo'shilganda, shu faylga yangi
PERMISSION_CATALOG qatorlari va kerak bo'lsa DEFAULT_ROLE_PERMISSIONS
ga yangi ruxsatlar qo'shiladi — boshqa hech qanday faylga tegilmaydi.

`ensure_seeded(db)` funksiyasi HAR BIR so'rov bazasida (production
Supabase'da ham, testlardagi vaqtinchalik SQLite'da ham) idempotent
tarzda ishlaydi: agar katalog allaqachon bazada bo'lsa, hech narsa
qilmaydi; bo'lmasa, bir marta to'ldiradi.
"""

from sqlalchemy.orm import Session

from app.modules.auth.models import Permission, Role, RolePermission

# --- Tizimdagi BARCHA mumkin bo'lgan aniq amallar ---
PERMISSION_CATALOG = {
    "inventory.manage": "Mahsulot qo'shish va omborga kirim qilish",
    "sales.create": "Sotuv (chek) amalga oshirish",
    "finance.view": "Moliyaviy hisobot va tranzaksiyalarni ko'rish",
    "employees.manage": "Xodim qo'shish va ro'yxatini ko'rish",
    "hrms.view_all": "Barcha xodimlarning ish vaqti (smena) tarixini ko'rish",
    "pms.manage": "Mehmonxona xonalari va bronlarni boshqarish",
}

# --- Standart lavozimlar va ularning ruxsatlari ---
DEFAULT_ROLE_PERMISSIONS = {
    "owner": list(PERMISSION_CATALOG.keys()),  # egasi — hammasi
    "cashier": ["sales.create"],
    "storekeeper": ["inventory.manage"],
    "receptionist": ["pms.manage"],  # mehmonxona resepshin xodimi
}


def ensure_seeded(db: Session) -> None:
    """Kerakli Permission/Role/RolePermission qatorlari yo'q bo'lsa, yaratadi."""

    # 1) Ruxsatlar katalogi
    existing_codes = {p.code for p in db.query(Permission).all()}
    for code, description in PERMISSION_CATALOG.items():
        if code not in existing_codes:
            db.add(Permission(code=code, description=description))
    db.flush()

    permission_by_code = {p.code: p for p in db.query(Permission).all()}

    # 2) Standart lavozimlar (company_id=NULL)
    existing_roles = {
        r.name: r for r in db.query(Role).filter(Role.company_id.is_(None)).all()
    }

    for role_name, permission_codes in DEFAULT_ROLE_PERMISSIONS.items():
        role = existing_roles.get(role_name)
        if role is None:
            role = Role(company_id=None, name=role_name)
            db.add(role)
            db.flush()
            existing_roles[role_name] = role

        existing_perm_ids = {
            rp.permission_id
            for rp in db.query(RolePermission).filter(RolePermission.role_id == role.id).all()
        }
        for code in permission_codes:
            permission = permission_by_code[code]
            if permission.id not in existing_perm_ids:
                db.add(RolePermission(role_id=role.id, permission_id=permission.id))

    db.commit()


def get_default_role(db: Session, name: str) -> Role:
    """Standart (company_id=NULL) lavozimni nomi bo'yicha topib beradi.
    `ensure_seeded()` avval chaqirilgan bo'lishi kerak."""
    return db.query(Role).filter(Role.company_id.is_(None), Role.name == name).first()
