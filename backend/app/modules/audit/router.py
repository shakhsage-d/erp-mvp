"""
modules/audit/router.py
--------------------------
Audit tarixini ko'rish — faqat `audit.view` ruxsatiga ega (standart
holatda faqat egasi).
"""

from fastapi import APIRouter, Depends

from app.db.session import get_db
from app.core.tenant import get_current_company_id
from app.core.permissions import require_permission
from app.core.pagination import Page, PageParams, paginate, build_page
from app.modules.audit import models, schemas

router = APIRouter(prefix="/audit-log", tags=["Audit - Tarix"])


@router.get(
    "",
    response_model=Page[schemas.AuditLogOut],
    summary="Kompaniyadagi muhim amallar tarixi",
)
def list_audit_log(
    db=Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    params: PageParams = Depends(),
    _: None = Depends(require_permission("audit.view")),
):
    """
    Har bir muhim amal (xodim qo'shildi/faolsizlantirildi, sotuv
    qilindi, mehmon chiqarildi va h.k.) shu yerda, eng yangisi
    birinchi bo'lib ko'rinadi. `?search=...` — amal turi (`action`)
    bo'yicha qidiradi, masalan "employee".
    """
    query = db.query(models.AuditLog).filter(
        models.AuditLog.company_id == company_id,
    )
    if params.search:
        query = query.filter(models.AuditLog.action.ilike(f"%{params.search}%"))

    query = query.order_by(models.AuditLog.created_at.desc())
    items, total = paginate(query, params)
    return build_page(items, total, params)
