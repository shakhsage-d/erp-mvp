"""
modules/sales/router.py
-------------------------
BU FAYL — ARXITEKTURANING YURAGI.
Bitta savdo (chek) yopilganda, quyidagilar BITTA TRANZAKSIYADA sodir bo'ladi:
  1) WMS: har bir mahsulot qoldig'idan sotilgan miqdor ayiriladi
  2) FMS: kassaga kirim (Transaction/income) avtomatik yoziladi

MUHIM TUZATISH (avvalgi versiyaga nisbatan):
Avval mahsulot faqat `product_id` bo'yicha qidirilardi — `company_id`
filtri yo'q edi. Bu boshqa kompaniyaning mahsulotini "sotib", uning
omborini kamaytirish imkonini berardi. Endi filtr MAJBURIY.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.tenant import get_current_company_id
from app.core.exceptions import NotFoundError, InsufficientStockError, EmptyRequestError
from app.core.logging_config import get_logger
from app.core.rate_limit import limiter
from app.modules.sales import models as sales_models, schemas
from app.modules.inventory import models as inventory_models
from app.modules.finance import models as finance_models

router = APIRouter(prefix="/sales", tags=["Savdo (WMS + FMS integratsiyasi)"])
logger = get_logger(__name__)


@router.post(
    "/",
    response_model=schemas.SaleOut,
    summary="Chek yopish (sotuv)",
)
@limiter.limit("60/minute")
def create_sale(
    request: Request,
    sale_request: schemas.SaleCreate,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
):
    """
    Kassir "Sotish" tugmasini bosganda chaqiriladigan asosiy endpoint.

    Bitta chaqiruvda uchta amal ATOM tarzda (hammasi yoki hech narsa)
    bajariladi:
    1. **WMS**: har bir sotilgan mahsulot uchun ombor qoldig'i kamayadi
    2. **FMS**: chek summasi bo'yicha moliyaga avtomatik kirim yoziladi
    3. Chekning o'zi (`sales` + `sale_items`) saqlanadi

    Agar ro'yxatdagi biror mahsulot topilmasa yoki omborda yetarli
    miqdor bo'lmasa, **butun chek bekor qilinadi** — yarim bajarilgan
    sotuv hech qachon qolmaydi.
    """

    if not sale_request.items:
        raise EmptyRequestError("Chekda mahsulot yo'q")

    total_amount = 0.0
    sale = sales_models.Sale(company_id=company_id, total_amount=0.0)
    db.add(sale)
    db.flush()  # sale.id ni olish uchun, hali commit qilmasdan

    for item in sale_request.items:
        product = db.query(inventory_models.Product).filter(
            inventory_models.Product.id == item.product_id,
            inventory_models.Product.company_id == company_id,  # <-- TUZATILDI
        ).first()

        if not product:
            db.rollback()
            logger.warning(
                "Sotuv rad etildi (mahsulot topilmadi): company=%s product_id=%s",
                company_id, item.product_id,
            )
            raise NotFoundError(
                f"Mahsulot topilmadi: id={item.product_id}",
                extra={"product_id": item.product_id},
            )

        if product.quantity < item.quantity:
            db.rollback()
            logger.warning(
                "Sotuv rad etildi (omborda yetarli emas): company=%s product_id=%s "
                "mavjud=%s so'ralgan=%s",
                company_id, product.id, product.quantity, item.quantity,
            )
            raise InsufficientStockError(
                f"'{product.name}' dan omborda yetarli mahsulot yo'q",
                extra={
                    "product_id": product.id,
                    "product_name": product.name,
                    "available": product.quantity,
                    "requested": item.quantity,
                },
            )

        # 1) WMS: qoldiqni kamaytiramiz
        product.quantity -= item.quantity
        db.add(inventory_models.StockMovement(
            company_id=company_id,
            product_id=product.id,
            type=inventory_models.MovementType.OUT,
            quantity=item.quantity,
            reason=f"Sale #{sale.id}",
        ))

        # 2) Chek qatorini yozamiz
        line_total = product.sale_price * item.quantity
        total_amount += line_total
        db.add(sales_models.SaleItem(
            company_id=company_id,
            sale_id=sale.id,
            product_id=product.id,
            quantity=item.quantity,
            price=product.sale_price,
        ))

    sale.total_amount = total_amount

    # 3) FMS: moliyaga avtomatik kirim yozamiz
    db.add(finance_models.Transaction(
        company_id=company_id,
        type=finance_models.TransactionType.INCOME,
        amount=total_amount,
        source=f"Sale #{sale.id}",
    ))

    db.commit()
    db.refresh(sale)
    logger.info(
        "Sotuv yakunlandi: company=%s sale_id=%s summa=%s",
        company_id, sale.id, sale.total_amount,
    )
    return sale
