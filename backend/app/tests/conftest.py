"""
tests/conftest.py
------------------
Testlar uchun umumiy sozlamalar (fixtures).

MUHIM: testlar HAQIQIY (Supabase) bazaga tegmaydi — har bir test
o'zining vaqtinchalik, xotieradagi SQLite bazasida ishlaydi va test
tugagach yo'q qilinadi.

BOSQICH 1 YANGILANISHI: endi `client` fixture avtomatik ravishda bitta
test-kompaniyani ro'yxatdan o'tkazadi va JWT tokenni sozlaydi — bu
productiondagi haqiqiy oqimni aynan takrorlaydi (eski "X-Company-Id"
header o'rniga endi haqiqiy Authorization: Bearer token ishlatiladi).
"""

import os

# MUHIM: app.main import qilinganda, u DATABASE_URL borligini talab qiladi
# (haqiqiy Supabase uchun). Testlar esa haqiqiy bazaga umuman bog'liq
# bo'lmasligi kerak — shuning uchun import'dan OLDIN vaqtinchalik/soxta
# qiymat beramiz. Endpointlar baribir pastdagi override orqali test
# bazasidan foydalanadi, bu qiymat faqat "import xato bermasin" uchun.
os.environ.setdefault("DATABASE_URL", "sqlite:///./_unused_module_level.db")
os.environ.setdefault("SECRET_KEY", "test-uchun-maxfiy-kalit")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.session import Base, get_db
from app.core.rate_limit import limiter
from app.main import app

# Har bir test funksiyasi uchun yangi, bo'sh xotieradagi SQLite baza
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """
    Rate limiter hisoblagichi butun test sessiyasi davomida saqlanib
    qolmasligi uchun, har bir test OLDIDAN tozalanadi.
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


def _register(c: TestClient, phone: str, company_name: str) -> dict:
    """Yordamchi: yangi kompaniya ro'yxatdan o'tkazib, token qaytaradi."""
    resp = c.post("/auth/register", json={
        "company_name": company_name,
        "owner_full_name": "Test Egasi",
        "phone": phone,
        "password": "parol123",
    })
    assert resp.status_code == 200, f"Ro'yxatdan o'tish muvaffaqiyatsiz: {resp.text}"
    return resp.json()


@pytest.fixture()
def client(db_session):
    """
    FastAPI test klienti — haqiqiy serverni ishga tushirmasdan,
    to'g'ridan-to'g'ri endpointlarni chaqirish imkonini beradi.

    Avtomatik ravishda BITTA test-kompaniyani ro'yxatdan o'tkazadi va
    olingan JWT tokenni standart `Authorization` header sifatida
    o'rnatadi — shuning uchun boshqa testlarda `client.post(...)`
    chaqirilganda, u allaqachon "kirgan" holatda bo'ladi (xuddi
    productionda foydalanuvchi login qilgandan keyingi holat kabi).
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        data = _register(c, phone="+998900000001", company_name="Test Do'kon 1")
        c.headers.update({"Authorization": f"Bearer {data['access_token']}"})
        yield c

    app.dependency_overrides.clear()


def other_company_headers(client: TestClient) -> dict:
    """
    Tenant-izolyatsiya testlari uchun: IKKINCHI, boshqa (begona)
    kompaniyani ro'yxatdan o'tkazadi va uning header'ini qaytaradi.
    Foydalanish:
        resp = client.post("/inventory/products", json={...},
                            headers=other_company_headers(client))
    """
    data = _register(client, phone="+998900000002", company_name="Test Do'kon 2")
    return {"Authorization": f"Bearer {data['access_token']}"}
