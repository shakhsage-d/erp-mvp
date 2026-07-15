"""
core/pagination.py
---------------------
Barcha "ro'yxat qaytaruvchi" endpointlar (mahsulotlar, tranzaksiyalar,
xodimlar, bronlar) uchun BITTA umumiy sahifalash naqshi.

Nega markazlashtirilgan: agar har bir router o'zicha "page/page_size"
mantig'ini yozsa, birida sahifalash boshqasida boshqacha ishlaydi.
Bu yerda bitta joyda yozilgani uchun, yangi modul (masalan HRMS'ning
"barcha smenalar" ro'yxati) ham xuddi shu formatga ega bo'ladi.
"""

import math
from typing import Generic, TypeVar, List

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy.orm import Query as SAQuery

T = TypeVar("T")


class PageParams:
    """So'rovdan `page`, `page_size`, `search` parametrlarini o'qiydi."""

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="Sahifa raqami (1 dan boshlanadi)"),
        page_size: int = Query(default=20, ge=1, le=100, description="Bitta sahifada nechta yozuv"),
        search: str | None = Query(default=None, max_length=100, description="Nom bo'yicha qidiruv"),
    ):
        self.page = page
        self.page_size = page_size
        self.search = search


class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


def paginate(query: SAQuery, params: PageParams) -> tuple[list, int]:
    """
    SQLAlchemy `query` obyektini sahifalab, (yozuvlar, jami_son) qaytaradi.
    Qidiruv filtri chaqiruvchi tomonidan (search maydoni qaysi ustunga
    tegishli ekanini bilgani uchun) oldindan qo'llanilgan bo'lishi kerak —
    bu funksiya faqat sahifalashning o'zini qiladi.
    """
    total = query.count()
    items = (
        query.offset((params.page - 1) * params.page_size)
        .limit(params.page_size)
        .all()
    )
    return items, total


def build_page(items: list, total: int, params: PageParams) -> dict:
    return {
        "items": items,
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "total_pages": max(1, math.ceil(total / params.page_size)),
    }
