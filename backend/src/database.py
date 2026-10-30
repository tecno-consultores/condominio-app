import os
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

# Para Nivel 11X permitimos inyección de base de datos efímera para pruebas (SQLite memory)
# y PostgreSQL para el entorno normal.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

_engine_kwargs: dict[str, Any] = {"echo": False}
if DATABASE_URL.startswith("sqlite") and ":memory:" in DATABASE_URL:
    # SQLite en memoria: StaticPool mantiene una única conexión compartida para que el
    # esquema creado al arrancar y los datos persistan durante toda la vida del proceso.
    _engine_kwargs["poolclass"] = StaticPool
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(DATABASE_URL, **_engine_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session
