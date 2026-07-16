"""
modules/suppliers/router.py
------------------------------
Ta'minotchilar va xarid buyurtmalari.

MUHIM: `receive_purchase_order` — bu fayldagi eng muhim funksiya.
U bitta amalda: (1) ombor qoldig'ini oshiradi, (2) moliyaga chiqim
yozadi, (3) buyurtmani "qabul qilindi" deb belgilaydi.
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.tenant import get_current_company_id, get_current_user_id
from app.core.permissions import require_permission
from app.core.exceptions import NotFoundError, ConflictError, EmptyRequestError
from app.core.logging_config import get_logger
from app.core.audit_log import record_audit
from app.core.pagination import Page, PageParams, paginate, build_page
from app.modules.suppliers import models, schemas
from app.modules.inventory import models as inventory_models
from app.modules.finance import models as finance_models

router = APIRouter(tags=["Ta'minotchilar (Suppliers)"])
logger = get_logger(__name__)


# ============================================================
# TA'MINOTCHILAR
# ============================================================

@router.post(
    "/suppliers",
    response_model=schemas.SupplierOut,
    summary="Yangi ta'minotchi qo'shish",
)
def create_supplier(
    payload: schemas.SupplierCreate,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    _: None = Depends(require_permission("suppliers.manage")),
):
    supplier = models.Supplier(company_id=company_id, **payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    logger.info("Ta'minotchi qo'shildi: company=%s id=%s name=%s", company_id, supplier.id, supplier.name)
    return supplier


@router.get(
    "/suppliers",
    response_model=Page[schemas.SupplierOut],
    summary="Ta'minotchilar ro'yxati",
)
def list_suppliers(
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    params: PageParams = Depends(),
    _: None = Depends(require_permission("suppliers.manage")),
):
    query = db.query(models.Supplier).filter(
        models.Supplier.company_id == company_id,
        models.Supplier.deleted_at.is_(None),
    )
    if params.search:
        query = query.filter(models.Supplier.name.ilike(f"%{params.search}%"))
    query = query.order_by(models.Supplier.name)
    items, total = paginate(query, params)
    return build_page(items, total, params)


@router.post(
    "/suppliers/{supplier_id}/deactivate",
    response_model=schemas.SupplierOut,
    summary="Ta'minotchini faolsizlantirish",
)
def deactivate_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    _: None = Depends(require_permission("suppliers.manage")),
):
    supplier = db.query(models.Supplier).filter(
        models.Supplier.id == supplier_id,
        models.Supplier.company_id == company_id,
    ).first()
    if not supplier:
        raise NotFoundError("Ta'minotchi topilmadi")

    supplier.deleted_at = datetime.utcnow()
    db.commit()
    db.refresh(supplier)
    return supplier


# ============================================================
# XARID BUYURTMALARI
# ============================================================

@router.post(
    "/purchase-orders",
    response_model=schemas.PurchaseOrderOut,
    summary="Yangi xarid buyurtmasi yaratish",
)
def create_purchase_order(
    payload: schemas.PurchaseOrderCreate,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    _: None = Depends(require_permission("suppliers.manage")),
):
    """
    Buyurtma yaratiladi ("ordered" holatida) — hali ombor yoki
    moliyaga TA'SIR QILMAYDI. Faqat `receive` chaqirilganda (tovar
    haqiqatan ham kelib tushganda) ombor va moliya yangilanadi.
    """
    if not payload.items:
        raise EmptyRequestError("Buyurtmada mahsulot yo'q")

    supplier = db.query(models.Supplier).filter(
        models.Supplier.id == payload.supplier_id,
        models.Supplier.company_id == company_id,
    ).first()
    if not supplier:
        raise NotFoundError("Ta'minotchi topilmadi", extra={"supplier_id": payload.supplier_id})

    total_amount = 0.0
    order = models.PurchaseOrder(company_id=company_id, supplier_id=supplier.id, total_amount=0.0)
    db.add(order)
    db.flush()

    for item in payload.items:
        product = db.query(inventory_models.Product).filter(
            inventory_models.Product.id == item.product_id,
            inventory_models.Product.company_id == company_id,
        ).first()
        if not product:
            db.rollback()
            raise NotFoundError("Mahsulot topilmadi", extra={"product_id": item.product_id})

        line_total = item.quantity * item.unit_price
        total_amount += line_total

        db.add(models.PurchaseOrderItem(
            company_id=company_id,
            purchase_order_id=order.id,
            product_id=product.id,
            quantity=item.quantity,
            unit_price=item.unit_price,
        ))

    order.total_amount = total_amount
    db.commit()
    db.refresh(order)

    logger.info("Xarid buyurtmasi yaratildi: company=%s order_id=%s summa=%s", company_id, order.id, total_amount)
    return order


@router.get(
    "/purchase-orders",
    response_model=list[schemas.PurchaseOrderOut],
    summary="Xarid buyurtmalari ro'yxati",
)
def list_purchase_orders(
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    _: None = Depends(require_permission("suppliers.manage")),
):
    return db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.company_id == company_id,
    ).order_by(models.PurchaseOrder.created_at.desc()).all()


@router.post(
    "/purchase-orders/{order_id}/receive",
    response_model=schemas.PurchaseOrderOut,
    summary="Xarid buyurtmasini qabul qilish (WMS+FMS integratsiyasi)",
)
def receive_purchase_order(
    order_id: int,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    actor_id: int = Depends(get_current_user_id),
    _: None = Depends(require_permission("suppliers.manage")),
):
    """
    Tovar haqiqatan ham kelib tushganda chaqiriladi. Bitta amalda:
    1) Har bir mahsulot ombor qoldig'iga qo'shiladi
    2) Umumiy summa moliyaga CHIQIM sifatida yoziladi
    3) Buyurtma "received" deb belgilanadi
    """
    order = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.id == order_id,
        models.PurchaseOrder.company_id == company_id,
    ).first()
    if not order:
        raise NotFoundError("Xarid buyurtmasi topilmadi", extra={"order_id": order_id})

    if order.status != models.PurchaseOrderStatus.ORDERED:
        raise ConflictError(f"Bu buyurtma allaqachon '{order.status.value}' holatida")

    items = db.query(models.PurchaseOrderItem).filter(
        models.PurchaseOrderItem.purchase_order_id == order.id,
    ).all()

    for item in items:
        product = db.query(inventory_models.Product).filter(
            inventory_models.Product.id == item.product_id,
        ).first()
        if product:
            product.quantity += item.quantity
            db.add(inventory_models.StockMovement(
                company_id=company_id,
                product_id=product.id,
                type=inventory_models.MovementType.IN,
                quantity=item.quantity,
                reason=f"Purchase Order #{order.id}",
            ))

    order.status = models.PurchaseOrderStatus.RECEIVED
    order.received_at = datetime.utcnow()

    db.add(finance_models.Transaction(
        company_id=company_id,
        type=finance_models.TransactionType.EXPENSE,
        amount=order.total_amount,
        source=f"Xarid buyurtmasi #{order.id}",
    ))

    record_audit(
        db, company_id, actor_id, "purchase_order.receive",
        entity_type="purchase_order", entity_id=order.id,
        details=f"summa={order.total_amount}",
    )

    db.commit()
    db.refresh(order)

    logger.info("Xarid buyurtmasi qabul qilindi: company=%s order_id=%s", company_id, order.id)
    return order
