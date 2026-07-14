"""
core/logging_config.py
------------------------
Butun ilova uchun BITTA joyda logging sozlanadi.

Nega bu muhim:
  - Render'dagi "Logs" bo'limida nima bo'layotganini tushunish uchun
    (masalan nega bitta mijoz shikoyat qilyapti) — mahalliy debug qilish
    imkoni bo'lmaganda, log — yagona "ko'z"ingiz
  - Har bir muhim amal (mahsulot qo'shildi, sotuv bo'ldi, xato chiqdi)
    QAYSI KOMPANIYA, QACHON, NIMA qilgani bilan birga yoziladi
  - Yangi modul qo'shilganda, shunchaki `get_logger(__name__)` chaqiriladi —
    formatni qayta o'ylab chiqarish shart emas
"""

import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    """main.py import qilinganda BIR MARTA chaqiriladi."""
    level = logging.DEBUG if settings.ENV == "local" else logging.INFO

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # SQLAlchemy va boshqa kutubxonalarning haddan tashqari "chiyillashini"
    # bosish — faqat WARNING va undan yuqorisini ko'rsatadi
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Har bir modul o'zining logger'ini shu orqali oladi:
        logger = get_logger(__name__)
        logger.info("Mahsulot qo'shildi: %s", product.name)
    """
    return logging.getLogger(name)
