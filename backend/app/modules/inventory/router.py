"""
modules/inventory/router.py
-----------------------------
WMS (Warehouse Management) moduli. Mahsulot qo'shish, ro'yxatni ko'rish,
va omborga kirim qilish shu yerda.

MUHIM TUZATISH (avvalgi versiyaga nisbatan):
Avval `stock_in` funksiyasida mahsulot faqat `product_id` bo'yicha
qidirilardi, `company_id` filtri YO'Q edi — bu boshqa kompaniyaning
mahsulotini o'zgartirish imkonini berardi. Endi har bir qidiruvda
company_id filtri MAJBURIY.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.tenant import get_current_company_id
from app.core.exceptions import NotFoundError
from app.core.logging_config import get_logger
from app.core.rate_limit import limiter
from app.modules.inventory import models, schemas

router = APIRouter(prefix="/inventory", tags=["WMS - Ombor"])
logger = get_logger(__name__)


@router.post("/products", response_model=schemas.ProductOut)
@limiter.limit("30/minute")
def create_product(
    request: Request,
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
):
    """Yangi mahsulot qo'shish."""
    db_product = models.Product(company_id=company_id, **product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    logger.info("Mahsulot qo'shildi: company=%s id=%s name=%s", company_id, db_product.id, db_product.name)
    return db_product


@router.get("/products", response_model=list[schemas.ProductOut])
def list_products(
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
):
    """Faqat shu kompaniyaga tegishli mahsulotlar va ularning qoldig'i."""
    return db.query(models.Product).filter(
        models.Product.company_id == company_id,
        models.Product.deleted_at.is_(None),
    ).all()


@router.post("/stock-in")
@limiter.limit("60/minute")
def stock_in(
    request: Request,
    stock_request: schemas.StockInRequest,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
):
    """Omborga yangi tovar kirim qilish."""
    product = db.query(models.Product).filter(
        models.Product.id == stock_request.product_id,
        models.Product.company_id == company_id,  # <-- TUZATILDI: filtr qo'shildi
    ).first()
    if not product:
        raise NotFoundError("Mahsulot topilmadi", extra={"product_id": stock_request.product_id})

    product.quantity += stock_request.quantity

    movement = models.StockMovement(
        company_id=company_id,  # <-- endi bu yerda ham to'g'ridan-to'g'ri yoziladi
        product_id=product.id,
        type=models.MovementType.IN,
        quantity=stock_request.quantity,
        reason=stock_request.reason,
    )
    db.add(movement)
    db.commit()

    logger.info(
        "Ombor kirimi: company=%s product_id=%s (+%s) yangi_qoldiq=%s",
        company_id, product.id, stock_request.quantity, product.quantity,
    )

    return {
        "message": f"{product.name} uchun {stock_request.quantity} {product.unit} kirim qilindi",
        "new_quantity": product.quantity,
    }
