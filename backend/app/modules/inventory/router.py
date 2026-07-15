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
from app.core.permissions import require_permission
from app.core.exceptions import NotFoundError
from app.core.logging_config import get_logger
from app.core.rate_limit import limiter
from app.core.pagination import Page, PageParams, paginate, build_page
from app.modules.inventory import models, schemas

router = APIRouter(prefix="/inventory", tags=["WMS - Ombor"])
logger = get_logger(__name__)


@router.post(
    "/products",
    response_model=schemas.ProductOut,
    summary="Yangi mahsulot qo'shish",
)
@limiter.limit("30/minute")
def create_product(
    request: Request,
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    _: None = Depends(require_permission("inventory.manage")),
):
    """
    Yangi mahsulotni ombor katalogiga qo'shadi.

    - Boshlang'ich `quantity` (0 dan katta) bilan ham qo'shish mumkin,
      yoki `0` bilan qo'shib, keyin `/inventory/stock-in` orqali
      kirim qilish mumkin.
    - `name` bo'sh yoki faqat bo'shliqlardan iborat bo'lishi mumkin emas.
    - Narxlar va miqdor manfiy bo'lishi mumkin emas.
    """
    db_product = models.Product(company_id=company_id, **product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    logger.info("Mahsulot qo'shildi: company=%s id=%s name=%s", company_id, db_product.id, db_product.name)
    return db_product


@router.get(
    "/products",
    response_model=Page[schemas.ProductOut],
    summary="Mahsulotlar ro'yxati va qoldig'i (sahifalangan, qidiruv bilan)",
)
def list_products(
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    params: PageParams = Depends(),
):
    """
    Faqat shu kompaniyaga (token orqali) tegishli mahsulotlar va
    ularning qoldig'i. `?search=guruch` orqali nomi bo'yicha qidirish,
    `?page=2&page_size=10` orqali sahifalash mumkin.
    """
    query = db.query(models.Product).filter(
        models.Product.company_id == company_id,
        models.Product.deleted_at.is_(None),
    )
    if params.search:
        query = query.filter(models.Product.name.ilike(f"%{params.search}%"))

    query = query.order_by(models.Product.id.desc())
    items, total = paginate(query, params)
    return build_page(items, total, params)


@router.post(
    "/stock-in",
    summary="Omborga tovar kirim qilish",
)
@limiter.limit("60/minute")
def stock_in(
    request: Request,
    stock_request: schemas.StockInRequest,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    _: None = Depends(require_permission("inventory.manage")),
):
    """
    Mavjud mahsulotga yetkazib berilgan tovarni ombor qoldig'iga qo'shadi.

    Har bir kirim `stock_movements` jadvaliga tarix sifatida ham yoziladi
    (audit uchun) — bu orqali "qachon, qancha kirim bo'lgan" tarixini
    keyinchalik ko'rish mumkin bo'ladi.
    """
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
