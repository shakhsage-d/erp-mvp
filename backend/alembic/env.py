"""
alembic/env.py
---------------
Bu fayl Alembic'ga qaysi bazaga ulanish va qaysi jadvallarni
"bilish" kerakligini aytadi. .env dagi DATABASE_URL avtomatik o'qiladi.

Yangi modul (masalan HRMS) qo'shilganda, uning models.py fayli
shu yerga import qilinishi kerak — aks holda Alembic uni "ko'rmaydi".
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv

# backend/ papkasini import yo'lida ko'rish uchun
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from app.db.session import Base  # noqa: E402

# --- HAR BIR MODUL SHU YERGA IMPORT QILINADI (jadval yaratish/o'zgartirish uchun) ---
from app.modules.auth import models as auth_models  # noqa: F401,E402
from app.modules.inventory import models as inventory_models  # noqa: F401,E402
from app.modules.sales import models as sales_models  # noqa: F401,E402
from app.modules.finance import models as finance_models  # noqa: F401,E402
from app.modules.hrms import models as hrms_models  # noqa: F401,E402
from app.modules.pms import models as pms_models  # noqa: F401,E402
from app.modules.audit import models as audit_models  # noqa: F401,E402

config = context.config
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", ""))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
