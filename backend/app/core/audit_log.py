"""
core/audit_log.py
--------------------
Barcha modullar audit yozuvini shu BITTA funksiya orqali qo'shadi —
bu format har doim bir xil bo'lishini ta'minlaydi.

MUHIM: `record_audit()` `db.commit()` QILMAYDI — chaqiruvchi o'zining
asosiy amali (masalan sotuv, xodim faolsizlantirish) bilan BIR
TRANZAKSIYADA committ qiladi. Shunda audit yozuvi asosiy amaldan
"ajralib qolmaydi" (yoki ikkalasi ham saqlanadi, yoki hech biri).
"""

from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog


def record_audit(
    db: Session,
    company_id: int,
    user_id: int | None,
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    details: str | None = None,
) -> None:
    """
    Foydalanish:
        record_audit(db, company_id, user_id, "sale.create",
                     entity_type="sale", entity_id=sale.id,
                     details=f"summa={sale.total_amount}")
    """
    db.add(AuditLog(
        company_id=company_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    ))
