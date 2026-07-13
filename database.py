"""
database.py
-----------
Ma'lumotlar bazasiga ulanish shu yerda sozlanadi.
MVP bosqichida SQLite ishlatamiz (fayl asosida, hech narsa o'rnatish shart emas).
Keyinchalik, production'ga chiqqanda, faqat shu faylni o'zgartirib PostgreSQL'ga
o'tib ketamiz (kod boshqa joyda o'zgarmaydi — bu "Repository Pattern"ning foydasi).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Production'da bu qatorni shunga o'zgartirasiz:
# DATABASE_URL = "postgresql://user:password@localhost/erp_db"
DATABASE_URL = "sqlite:///./erp_demo.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}  # faqat SQLite uchun kerak
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Har bir so'rov (request) uchun alohida DB sessiya ochib, keyin yopib beradi."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
