# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
"""Pruebas unitarias e integración SQLite FK para el motor de base de datos, RLS y WORM."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, cast

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import StaticPool

from src import database, models
from src.database import (
    DEFAULT_CONDOMINIO_ID,
    WORM_GENESIS_HASH,
    Base,
    _activar_sqlite_foreign_keys,
    _build_engine_kwargs,
    _configurar_rls_al_iniciar_transaccion,
    _obtener_prev_hash_worm,
    apply_rls_session_settings,
    bind_rls_tenant,
    get_db,
    sellar_cadena_worm,
)
from src.models import (
    AuditoriaRecibo,
    ConsultaComunitaria,
    Estructura,
    OpcionConsulta,
    Recibo,
    VotoConsulta,
)
from src.security import compute_worm_record_hash
from tests._sqlite_helpers import create_sqlite_fk_factory, seed_condo_base


@dataclass
class _FakeDialect:
    name: str


class _FakeSyncConnection:
    """Stub mínimo de conexión síncrona para inspeccionar sentencias SQL RLS."""

    def __init__(self, dialect_name: str) -> None:
        self.dialect = _FakeDialect(name=dialect_name)
        self.executed: list[tuple[str, dict[str, Any] | None]] = []

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> None:
        self.executed.append((str(statement), params))


class _FakeSyncSession:
    def __init__(self, info: dict[str, Any]) -> None:
        self.info = info


class _FakeScalarResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value


class _FakePgAsyncSession:
    """Simula un AsyncSession conectado a PostgreSQL únicamente para verificar advisory locks WORM."""

    def __init__(self, last_hash: str | None) -> None:
        self.sync_session = _FakeSyncSession(info={})
        self.executed: list[tuple[str, dict[str, Any] | None]] = []
        self._last_hash = last_hash

    def get_bind(self) -> Any:
        return type("_Bind", (), {"dialect": _FakeDialect(name="postgresql")})()

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _FakeScalarResult:
        sql_txt = str(statement)
        self.executed.append((sql_txt, params))
        if "pg_advisory_xact_lock" in sql_txt:
            return _FakeScalarResult(None)
        return _FakeScalarResult(self._last_hash)


def test_base_metadata_y_constantes() -> None:
    """Verifica que Base.metadata registre las tablas de dominio y constantes esperadas."""
    assert models.Usuario.__tablename__ == "usuarios"
    assert DEFAULT_CONDOMINIO_ID >= 1
    assert WORM_GENESIS_HASH == "0" * 64
    tablas = set(Base.metadata.tables.keys())
    assert {
        "usuarios",
        "estructuras",
        "unidades",
        "recibos",
        "auditoria_recibos",
        "votos_consulta",
        "incidencias",
        "fondos_condominio",
        "reportes_mensuales",
    }.issubset(tablas)


def test_build_engine_kwargs_por_dialecto(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida opciones de pooling para SQLite en memoria, SQLite en archivo y PostgreSQL."""
    mem_kwargs = _build_engine_kwargs("sqlite+aiosqlite:///:memory:")
    assert mem_kwargs["pool_pre_ping"] is True
    assert mem_kwargs["echo"] is False
    assert mem_kwargs["poolclass"] is StaticPool
    assert mem_kwargs["connect_args"] == {"check_same_thread": False}

    file_kwargs = _build_engine_kwargs("sqlite+aiosqlite:///tmp/condominio_test.db")
    assert file_kwargs == {"echo": False, "pool_pre_ping": True}

    monkeypatch.setenv("DB_POOL_SIZE", "12")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "24")
    monkeypatch.setenv("DB_POOL_TIMEOUT", "45")
    monkeypatch.setenv("DB_POOL_RECYCLE", "900")
    pg_kwargs = _build_engine_kwargs("postgresql+asyncpg://user:pass@postgres:5432/condo")
    assert pg_kwargs["pool_size"] == 12
    assert pg_kwargs["max_overflow"] == 24
    assert pg_kwargs["pool_timeout"] == 45
    assert pg_kwargs["pool_recycle"] == 900


def test_activar_sqlite_foreign_keys_filtra_por_modulo() -> None:
    """Solo ejecuta PRAGMA foreign_keys=ON cuando la conexión DBAPI pertenece a sqlite."""
    executed_cmds: list[str] = []
    closed_flag = {"closed": False}

    class _FakeSqliteCursor:
        def execute(self, cmd: str) -> None:
            executed_cmds.append(cmd)

        def close(self) -> None:
            closed_flag["closed"] = True

    class _FakeSqliteConn:
        __module__ = "aiosqlite.core"

        def cursor(self) -> _FakeSqliteCursor:
            return _FakeSqliteCursor()

    class _FakeAsyncpgConn:
        __module__ = "asyncpg.connection"

        def cursor(self) -> Any:
            raise AssertionError("No debe abrir cursor en conexiones no-SQLite")

    _activar_sqlite_foreign_keys(_FakeAsyncpgConn(), None)
    assert executed_cmds == []

    _activar_sqlite_foreign_keys(_FakeSqliteConn(), None)
    assert executed_cmds == ["PRAGMA foreign_keys=ON"]
    assert closed_flag["closed"] is True


def test_apply_rls_session_settings_postgresql_y_sqlite() -> None:
    """Inyecta rol y variables RLS en PostgreSQL y omite ejecución en SQLite."""
    pg_conn = _FakeSyncConnection("postgresql")
    apply_rls_session_settings(cast(Any, pg_conn), tenant_id="7", is_superadmin=False, enforce_runtime_role=True)
    assert len(pg_conn.executed) == 2
    assert pg_conn.executed[0][0] == "SET LOCAL ROLE condominio_app_runtime"
    assert "set_config('app.current_tenant_id', :tid, true)" in pg_conn.executed[1][0]
    assert pg_conn.executed[1][1] == {"tid": "7", "sa": "false"}

    pg_super = _FakeSyncConnection("postgresql")
    apply_rls_session_settings(cast(Any, pg_super), tenant_id=None, is_superadmin=True, enforce_runtime_role=False)
    assert len(pg_super.executed) == 1
    assert pg_super.executed[0][1] == {"tid": "", "sa": "true"}

    sqlite_conn = _FakeSyncConnection("sqlite")
    apply_rls_session_settings(cast(Any, sqlite_conn), tenant_id="1", is_superadmin=True, enforce_runtime_role=True)
    assert sqlite_conn.executed == []


def test_configurar_rls_al_iniciar_transaccion() -> None:
    """Lee tenant_id, is_superadmin y disable_runtime_role desde session.info."""
    pg_default = _FakeSyncConnection("postgresql")
    _configurar_rls_al_iniciar_transaccion(_FakeSyncSession({}), None, cast(Any, pg_default))
    assert pg_default.executed[0][0] == "SET LOCAL ROLE condominio_app_runtime"
    assert pg_default.executed[1][1] == {"tid": "", "sa": "false"}

    pg_custom = _FakeSyncConnection("postgresql")
    _configurar_rls_al_iniciar_transaccion(
        _FakeSyncSession({"tenant_id": "15", "is_superadmin": True, "disable_runtime_role": True}),
        None,
        cast(Any, pg_custom),
    )
    assert len(pg_custom.executed) == 1
    assert pg_custom.executed[0][1] == {"tid": "15", "sa": "true"}


async def test_bind_rls_tenant_noop_y_sqlite_real(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica bind_rls_tenant fuera de AsyncSession, antes y durante transacción real."""
    await bind_rls_tenant(object(), 99, is_superadmin=True)

    engine, factory = await create_sqlite_fk_factory()
    calls: list[tuple[str | None, bool, bool]] = []
    orig_apply = database.apply_rls_session_settings

    def _spy_apply(
        sync_conn: Any,
        tenant_id: str | None,
        is_superadmin: bool = False,
        enforce_runtime_role: bool = True,
    ) -> None:
        calls.append((tenant_id, is_superadmin, enforce_runtime_role))
        orig_apply(
            sync_conn,
            tenant_id,
            is_superadmin=is_superadmin,
            enforce_runtime_role=enforce_runtime_role,
        )

    monkeypatch.setattr(database, "apply_rls_session_settings", _spy_apply)

    try:
        async with factory() as session:
            await bind_rls_tenant(session, None, is_superadmin=False)
            assert session.sync_session.info["tenant_id"] == ""
            assert session.sync_session.info["is_superadmin"] is False
            assert calls == []

            await session.execute(text("SELECT 1"))
            assert session.in_transaction() is True
            session.sync_session.info["disable_runtime_role"] = True
            await bind_rls_tenant(session, 5, is_superadmin=True)
            assert session.sync_session.info["tenant_id"] == "5"
            assert session.sync_session.info["is_superadmin"] is True
            assert ("5", True, False) in calls

            with pytest.raises(IntegrityError):
                await session.execute(
                    text("INSERT INTO unidades (condominio_id, identificador, estructura_id) VALUES (1, 'X-1', 9999)")
                )
            await session.rollback()
    finally:
        await engine.dispose()


async def test_sellar_cadena_worm_y_persistencia_sqlite() -> None:
    """Prueba encadenamiento WORM en memoria, caché de sesión, persistencia SQLite y PostgreSQL lock."""
    with pytest.raises(ValueError, match="Tabla WORM no soportada"):
        await sellar_cadena_worm(object(), "tabla_invalida", 1, "payload")

    prev_stub, hash_stub = await sellar_cadena_worm(object(), "auditoria_recibos", 1, "evento|1")
    assert prev_stub == WORM_GENESIS_HASH
    assert hash_stub == compute_worm_record_hash(WORM_GENESIS_HASH, "evento|1")

    pg_fake = _FakePgAsyncSession(last_hash="ab" * 32)
    prev_pg = await _obtener_prev_hash_worm(cast(AsyncSession, pg_fake), "votos_consulta", 3)
    assert prev_pg == "ab" * 32
    assert any("pg_advisory_xact_lock" in sql for sql, _ in pg_fake.executed)

    engine, factory = await create_sqlite_fk_factory()
    try:
        ctx = await seed_condo_base(factory)
        async with factory() as session:
            recibo = Recibo(
                condominio_id=1,
                unidad_id=ctx.unidad_a_id,
                periodo="2026-11",
                monto_usd=Decimal("50.00"),
                monto_pagado_usd=Decimal("0.00"),
                estado="PENDIENTE",
            )
            session.add(recibo)
            await session.flush()

            p1, h1 = await sellar_cadena_worm(session, "auditoria_recibos", 1, "paso-1")
            assert p1 == WORM_GENESIS_HASH
            p2, h2 = await sellar_cadena_worm(session, "auditoria_recibos", 1, "paso-2")
            assert p2 == h1
            assert h2 != h1

            session.add(
                AuditoriaRecibo(
                    condominio_id=1,
                    recibo_id=recibo.id,
                    usuario_id=ctx.presidente_id,
                    estado_viejo="INEXISTENTE",
                    estado_nuevo="PENDIENTE",
                    motivo="Emisión inicial",
                    prev_hash=p1,
                    record_hash=h1,
                )
            )
            await session.commit()

        async with factory() as session2:
            p3, h3 = await sellar_cadena_worm(session2, "auditoria_recibos", 1, "paso-3")
            assert p3 == h1
            assert h3 == compute_worm_record_hash(h1, "paso-3")

            consulta = ConsultaComunitaria(
                condominio_id=1,
                titulo="Asamblea",
                descripcion_legal="Votación de mantenimiento",
                fecha_cierre=datetime.now(UTC) + timedelta(days=3),
                creada_por_id=ctx.presidente_id,
                estado="ABIERTA",
            )
            session2.add(consulta)
            await session2.flush()
            opcion = OpcionConsulta(condominio_id=1, consulta_id=consulta.id, etiqueta="Sí")
            session2.add(opcion)
            await session2.flush()
            pv, hv = await sellar_cadena_worm(session2, "votos_consulta", 1, "voto-1")
            assert pv == WORM_GENESIS_HASH
            session2.add(
                VotoConsulta(
                    condominio_id=1,
                    consulta_id=consulta.id,
                    opcion_id=opcion.id,
                    usuario_id=ctx.propietario_id,
                    unidad_id=ctx.unidad_a_id,
                    alicuota_capturada=Decimal("60.0000"),
                    ip_hash="a" * 64,
                    firma_hmac="b" * 64,
                    prev_hash=pv,
                    record_hash=hv,
                )
            )
            await session2.commit()

        async with factory() as session3:
            pv2, _ = await sellar_cadena_worm(session3, "votos_consulta", 1, "voto-2")
            assert pv2 == hv
    finally:
        await engine.dispose()


async def test_get_db_commit_y_rollback_en_excepcion(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica el generador get_db: inyecta tenant_id='', persiste commits y no guarda cambios tras excepción."""
    engine, factory = await create_sqlite_fk_factory()
    monkeypatch.setattr(database, "AsyncSessionLocal", factory)
    try:
        gen = get_db()
        session = await anext(gen)
        assert isinstance(session, AsyncSession)
        assert session.sync_session.info["tenant_id"] == ""
        session.add(Estructura(condominio_id=1, nombre="Edificio Commit", tipo="EDIFICIO"))
        await session.commit()
        await gen.aclose()

        gen_err = get_db()
        session_err = await anext(gen_err)
        session_err.add(Estructura(condominio_id=1, nombre="Edificio Rollback", tipo="EDIFICIO"))
        await session_err.flush()
        with pytest.raises(RuntimeError, match="fallo simulado"):
            await gen_err.athrow(RuntimeError("fallo simulado"))

        async with factory() as verify_session:
            rows = (await verify_session.execute(text("SELECT nombre FROM estructuras"))).scalars().all()
            assert rows == ["Edificio Commit"]
    finally:
        await engine.dispose()
