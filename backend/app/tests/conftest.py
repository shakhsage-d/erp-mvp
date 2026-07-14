"""
tests/conftest.py
------------------
Testlar uchun umumiy sozlamalar (fixtures).

MUHIM: testlar HAQIQIY (Supabase) bazaga tegmaydi — har bir test
o'zining vaqtinchalik, xotieradagi SQLite bazasida ishlaydi va test
tugagach yo'q qilinadi. Bu shuni anglatadi:
  - Testlarni istalgancha, xohlagan vaqtda ishga tushirish mumkin —
    haqiqiy ma'lumotlarga zarar yetkazmaydi
  - Testlar bir-biriga bog'liq emas, har biri "toza" holatdan boshlanadi
"""

import os

# MUHIM: app.main import qilinganda, u DATABASE_URL borligini talab qiladi
# (haqiqiy Supabase uchun). Testlar esa haqiqiy bazaga umuman bog'liq
# bo'lmasligi kerak — shuning uchun import'dan OLDIN vaqtinchalik/soxta
# qiymat beramiz. Endpointlar baribir pastdagi override orqali test
# bazasidan foydalanadi, bu qiymat faqat "import xato bermasin" uchun.
os.environ.setdefault("DATABASE_URL", "sqlite:///./_unused_module_level.db")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.session import Base, get_db
from app.core.tenant import get_current_company_id
from app.core.rate_limit import limiter
from app.main import app

# Har bir test funksiyasi uchun yangi, bo'sh xotieradagi SQLite baza
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """
    Rate limiter hisoblagichi butun test sessiyasi davomida saqlanib
    qolmasligi uchun, har bir test OLDIDAN tozalanadi. Aks holda, ko'p
    test bir xil "IP" (testserver) dan so'rov yuborgani uchun,
    testlar orasida chegaraga tegib qolish xavfi bo'lardi — bu esa
    testlarni "tasodifiy" (flaky) qilib qo'yadi.
    """
    limiter.reset()
    yield


@pytest.fixture()
def db_session():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    """
    FastAPI test klienti — haqiqiy serverni ishga tushirmasdan,
    to'g'ridan-to'g'ri endpointlarni chaqirish imkonini beradi.

    Faqat `get_db` almashtiriladi (haqiqiy bazaga tegmaslik uchun).
    `get_current_company_id` esa ATAYLAB almashtirilmaydi — u ishlab
    chiqarishdagi kabi `X-Company-Id` header'ini o'qiydi (standart: 1).
    Boshqa "kompaniya" nomidan so'rov yuborish kerak bo'lsa, testda
    shunchaki boshqa header yuboriladi:
        client.get("/inventory/products", headers={"X-Company-Id": "2"})
    Bu productiondagi xatti-harakatni aynan takrorlaydi — testlar
    "sun'iy" emas, haqiqiy yo'l bilan tekshiradi.
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def as_company(headers_company_id: int) -> dict:
    """Yordamchi: boshqa kompaniya nomidan so'rov yuborish uchun header tayyorlaydi."""
    return {"X-Company-Id": str(headers_company_id)}
