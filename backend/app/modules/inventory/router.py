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

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.tenant import get_current_company_id
from app.modules.inventory import models, schemas

router = APIRouter(prefix="/inventory", tags=["WMS - Ombor"])


@router.post("/products", response_model=schemas.ProductOut)
def create_product(
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
):
    """Yangi mahsulot qo'shish."""
    db_product = models.Product(company_id=company_id, **product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
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
def stock_in(
    request: schemas.StockInRequest,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
):
    """Omborga yangi tovar kirim qilish."""
    product = db.query(models.Product).filter(
        models.Product.id == request.product_id,
        models.Product.company_id == company_id,  # <-- TUZATILDI: filtr qo'shildi
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")

    product.quantity += request.quantity

    movement = models.StockMovement(
        company_id=company_id,  # <-- endi bu yerda ham to'g'ridan-to'g'ri yoziladi
        product_id=product.id,
        type=models.MovementType.IN,
        quantity=request.quantity,
        reason=request.reason,
    )
    db.add(movement)
    db.commit()

    return {
        "message": f"{product.name} uchun {request.quantity} {product.unit} kirim qilindi",
        "new_quantity": product.quantity,
    }
