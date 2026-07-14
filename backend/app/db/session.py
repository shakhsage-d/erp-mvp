"""
db/session.py
-------------
Ma'lumotlar bazasiga ulanish shu yerda, faqat SHU YERDA sozlanadi.
Endi PostgreSQL ishlatamiz (SQLite emas) — .env dagi DATABASE_URL orqali.

Local sinov uchun ham, Render/Supabase uchun ham bir xil kod ishlaydi —
faqat DATABASE_URL qiymati farq qiladi.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL topilmadi. .env fayliga qo'shing, masalan:\n"
        "DATABASE_URL=postgresql://user:password@host:5432/dbname\n"
        "(Supabase'dan: Project Settings -> Database -> Connection string)"
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Har bir so'rov (request) uchun alohida DB sessiya ochib, keyin yopib beradi."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
