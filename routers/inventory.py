"""
routers/inventory.py
---------------------
WMS (Warehouse Management) moduli. Mahsulot qo'shish, ro'yxatni ko'rish,
va omborga kirim qilish shu yerda.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db

router = APIRouter(prefix="/inventory", tags=["WMS - Ombor"])

# MVP uchun soddalashtirilgan: doim 1-company bilan ishlaymiz.
# Keyingi bosqichda bu joyga "current_user" orqali haqiqiy autentifikatsiya keladi.
DEMO_COMPANY_ID = 1


@router.post("/products", response_model=schemas.ProductOut)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    """Yangi mahsulot qo'shish (masalan: 'Coca-Cola 0.5L')."""
    db_product = models.Product(company_id=DEMO_COMPANY_ID, **product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@router.get("/products", response_model=list[schemas.ProductOut])
def list_products(db: Session = Depends(get_db)):
    """Barcha mahsulotlar va ularning joriy qoldig'i (stock)."""
    return db.query(models.Product).filter(
        models.Product.company_id == DEMO_COMPANY_ID
    ).all()


@router.post("/stock-in")
def stock_in(request: schemas.StockInRequest, db: Session = Depends(get_db)):
    """Omborga yangi tovar kirim qilish (masalan, yetkazib beruvchidan tovar keldi)."""
    product = db.query(models.Product).filter(
        models.Product.id == request.product_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")

    product.quantity += request.quantity

    movement = models.StockMovement(
        product_id=product.id,
        type=models.MovementType.IN,
        quantity=request.quantity,
        reason=request.reason,
    )
    db.add(movement)
    db.commit()

    return {"message": f"{product.name} uchun {request.quantity} {product.unit} kirim qilindi",
            "new_quantity": product.quantity}
