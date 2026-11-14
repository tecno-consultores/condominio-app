import os
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.engine import Connection
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


def apply_rls_session_settings(
    sync_conn: Connection,
    tenant_id: str | None,
    is_superadmin: bool = False,
) -> None:
    """Inyecta variables de sesión RLS por transacción en PostgreSQL 17."""
    if sync_conn.dialect.name != "postgresql":
        return
    sync_conn.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, true), set_config('app.is_superadmin', :sa, true)"),
        {
            "tid": "" if tenant_id is None else str(tenant_id),
            "sa": "true" if is_superadmin else "false",
        },
    )


@event.listens_for(AsyncSession.sync_session_class, "after_begin")
def _configurar_rls_al_iniciar_transaccion(
    session: Any,
    transaction: Any,
    connection: Connection,
) -> None:
    """Ejecuta set_config local para aislamiento multi-tenant al abrir cada transacción PG17."""
    del transaction
    tenant_id = session.info.get("tenant_id", "1")
    is_superadmin = bool(session.info.get("is_superadmin", False))
    apply_rls_session_settings(connection, tenant_id, is_superadmin=is_superadmin)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        session.sync_session.info.setdefault("tenant_id", "1")
        yield session
