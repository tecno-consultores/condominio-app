import os
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from src.security import compute_worm_record_hash

# Para Nivel 11X permitimos inyección de base de datos efímera para pruebas (SQLite memory)
# y PostgreSQL para el entorno normal.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
DEFAULT_CONDOMINIO_ID = int(os.getenv("CONDOMINIO_ID") or os.getenv("BOOTSTRAP_CONDOMINIO_ID") or "1")
WORM_GENESIS_HASH = "0" * 64
_WORM_LAST_HASH_SQL: dict[str, Any] = {
    "auditoria_recibos": text(
        "SELECT record_hash FROM auditoria_recibos WHERE condominio_id = :cid ORDER BY id DESC LIMIT 1"
    ),
    "votos_consulta": text(
        "SELECT record_hash FROM votos_consulta WHERE condominio_id = :cid ORDER BY id DESC LIMIT 1"
    ),
}


def _build_engine_kwargs(database_url: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"echo": False, "pool_pre_ping": True}
    if database_url.startswith("sqlite") and ":memory:" in database_url:
        kwargs["poolclass"] = StaticPool
        kwargs["connect_args"] = {"check_same_thread": False}
        return kwargs
    if not database_url.startswith("sqlite"):
        kwargs["pool_size"] = int(os.getenv("DB_POOL_SIZE", "10"))
        kwargs["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        kwargs["pool_timeout"] = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        kwargs["pool_recycle"] = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    return kwargs


engine = create_async_engine(DATABASE_URL, **_build_engine_kwargs(DATABASE_URL))
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


@event.listens_for(Engine, "connect")
def _activar_sqlite_foreign_keys(dbapi_connection: Any, connection_record: Any) -> None:
    """Garantiza integridad referencial estricta en motores SQLite (paridad PostgreSQL 17)."""
    del connection_record
    if "sqlite" in type(dbapi_connection).__module__.lower():
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def apply_rls_session_settings(
    sync_conn: Connection,
    tenant_id: str | None,
    is_superadmin: bool = False,
    enforce_runtime_role: bool = True,
) -> None:
    """Inyecta variables de sesión RLS y rol no-superusuario por transacción en PostgreSQL 17."""
    if sync_conn.dialect.name != "postgresql":
        return
    if enforce_runtime_role:
        sync_conn.execute(text("SET LOCAL ROLE condominio_app_runtime"))
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
    """Ejecuta set_config local fail-closed ('') para aislamiento multi-tenant al abrir cada transacción PG17."""
    del transaction
    tenant_id = session.info.get("tenant_id", "")
    is_superadmin = bool(session.info.get("is_superadmin", False))
    enforce_role = not bool(session.info.get("disable_runtime_role", False))
    apply_rls_session_settings(
        connection,
        tenant_id,
        is_superadmin=is_superadmin,
        enforce_runtime_role=enforce_role,
    )


async def bind_rls_tenant(
    db: Any,
    condominio_id: int | str | None,
    *,
    is_superadmin: bool = False,
) -> None:
    """Vincula explícitamente el tenant RLS en la sesión y en la transacción activa si ya inició."""
    if not isinstance(db, AsyncSession):
        return
    tid = "" if condominio_id is None else str(condominio_id)
    db.sync_session.info["tenant_id"] = tid
    db.sync_session.info["is_superadmin"] = is_superadmin
    if db.in_transaction():
        enforce_role = not bool(db.sync_session.info.get("disable_runtime_role", False))
        conn = await db.connection()
        await conn.run_sync(
            lambda sc: apply_rls_session_settings(
                sc,
                tid,
                is_superadmin=is_superadmin,
                enforce_runtime_role=enforce_role,
            )
        )


async def _obtener_prev_hash_worm(db: AsyncSession, table_name: str, condominio_id: int) -> str:
    tail_map: dict[tuple[str, int], str] = db.sync_session.info.setdefault("_worm_tail", {})
    cache_key = (table_name, condominio_id)
    if cache_key in tail_map:
        return tail_map[cache_key]
    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lk))"),
            {"lk": f"worm:{table_name}:{condominio_id}"},
        )
    sql = _WORM_LAST_HASH_SQL[table_name]
    res = await db.execute(sql, {"cid": condominio_id})
    last_hash = res.scalar_one_or_none()
    return str(last_hash) if last_hash else WORM_GENESIS_HASH


async def sellar_cadena_worm(
    db: Any,
    table_name: str,
    condominio_id: int,
    payload: str,
) -> tuple[str, str]:
    """Calcula y serializa el enlace criptográfico WORM (prev_hash, record_hash) para tablas inmutables."""
    if table_name not in _WORM_LAST_HASH_SQL:
        raise ValueError(f"Tabla WORM no soportada: {table_name}")
    if not isinstance(db, AsyncSession):
        return WORM_GENESIS_HASH, compute_worm_record_hash(WORM_GENESIS_HASH, payload)
    prev_hash = await _obtener_prev_hash_worm(db, table_name, condominio_id)
    rec_hash = compute_worm_record_hash(prev_hash, payload)
    db.sync_session.info.setdefault("_worm_tail", {})[(table_name, condominio_id)] = rec_hash
    return prev_hash, rec_hash


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        session.sync_session.info.setdefault("tenant_id", "")
        yield session
