"""
routers/sales.py
-----------------
BU FAYL — ARXITEKTURANING YURAGI.
Bitta savdo (chek) yopilganda, quyidagilar BITTA TRANZAKSIYADA sodir bo'ladi:
  1) WMS: har bir mahsulot qoldig'idan sotilgan miqdor ayiriladi
  2) FMS: kassaga kirim (Transaction/income) avtomatik yoziladi
Aynan shu — "modullar bir-biriga qanday ulanadi" degan savolning javobi:
ular alohida mikroservis emas, bitta kod ichida, bitta DB tranzaksiyasida ishlaydi.
Bu 2 kishilik jamoa uchun eng tez va eng kam xatoli yo'l.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db

router = APIRouter(prefix="/sales", tags=["Savdo (WMS + FMS integratsiyasi)"])

DEMO_COMPANY_ID = 1


@router.post("/", response_model=schemas.SaleOut)
def create_sale(sale_request: schemas.SaleCreate, db: Session = Depends(get_db)):
    """Kassir 'Sotish' tugmasini bosganda shu endpoint chaqiriladi."""

    if not sale_request.items:
        raise HTTPException(status_code=400, detail="Chekda mahsulot yo'q")

    total_amount = 0.0
    sale = models.Sale(company_id=DEMO_COMPANY_ID, total_amount=0.0)
    db.add(sale)
    db.flush()  # sale.id ni olish uchun, hali commit qilmasdan

    for item in sale_request.items:
        product = db.query(models.Product).filter(
            models.Product.id == item.product_id
        ).first()

        if not product:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Mahsulot topilmadi: id={item.product_id}")

        if product.quantity < item.quantity:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"'{product.name}' dan omborda yetarli mahsulot yo'q "
                       f"(qoldiq: {product.quantity}, so'ralgan: {item.quantity})"
            )

        # 1) WMS: qoldiqni kamaytiramiz
        product.quantity -= item.quantity
        db.add(models.StockMovement(
            product_id=product.id,
            type=models.MovementType.OUT,
            quantity=item.quantity,
            reason=f"Sale #{sale.id}",
        ))

        # 2) Chek qatorini yozamiz
        line_total = product.sale_price * item.quantity
        total_amount += line_total
        db.add(models.SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            quantity=item.quantity,
            price=product.sale_price,
        ))

    sale.total_amount = total_amount

    # 3) FMS: moliyaga avtomatik kirim yozamiz
    db.add(models.Transaction(
        company_id=DEMO_COMPANY_ID,
        type=models.TransactionType.INCOME,
        amount=total_amount,
        source=f"Sale #{sale.id}",
    ))

    db.commit()
    db.refresh(sale)
    return sale
