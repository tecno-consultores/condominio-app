# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
"""Helpers compartidos para suites unitarias con SQLite FK real (Anti-Mock Blindness)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from src.models import (
    Base,
    ContratoOcupacion,
    Estructura,
    TasaCambio,
    Unidad,
    Usuario,
)
from src.security import get_password_hash


@dataclass(frozen=True)
class SeededCondoContext:
    """Identificadores y entidades mínimas sembradas en SQLite real con FK activas."""

    estructura_id: int
    unidad_a_id: int
    unidad_b_id: int
    presidente_id: int
    tesorero_id: int
    secretario_id: int
    vocero_id: int
    conserje_id: int
    propietario_id: int
    inquilino_id: int


def _activar_fk_sqlite(dbapi_conn: Any, _rec: Any) -> None:
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async def create_sqlite_fk_factory(
    db_path: Path | None = None,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Crea un engine SQLite con ``PRAGMA foreign_keys=ON`` verificado y todas las 27 tablas."""
    if db_path is None:
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    event.listen(engine.sync_engine, "connect", _activar_fk_sqlite)
    async with engine.begin() as conn:
        fk_state = (await conn.execute(text("PRAGMA foreign_keys"))).scalar_one()
        if fk_state != 1:
            await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, factory


def _crear_usuario_seed(nombre: str, cedula: str, correo: str, rol: str, pw_hash: str) -> Usuario:
    return Usuario(
        condominio_id=1,
        nombre=nombre,
        cedula=cedula,
        correo=correo,
        telefono="+584140000100",
        password_hash=pw_hash,
        es_activo=True,
        rol=rol,
    )


@lru_cache(maxsize=8)
def _hash_password_seed(password_plana: str) -> str:
    """Memoriza el hash PBKDF2-HMAC-SHA256 real por contraseña seed para evitar cuello de CPU en pruebas."""
    return get_password_hash(password_plana)


async def seed_condo_base(
    factory: async_sessionmaker[AsyncSession],
    *,
    password_plana: str = "ClaveReal11X!",
) -> SeededCondoContext:
    """Siembra estructura, unidades (60/40), usuarios por rol y tasa BCV inicial."""
    pw_hash = _hash_password_seed(password_plana)
    async with factory() as session:
        torre = Estructura(condominio_id=1, nombre="Torre Única", tipo="TORRE")
        session.add(torre)
        await session.flush()

        unidad_a = Unidad(
            condominio_id=1,
            identificador="1-A",
            estructura_id=torre.id,
            alicuota=Decimal("60.0000"),
        )
        unidad_b = Unidad(
            condominio_id=1,
            identificador="1-B",
            estructura_id=torre.id,
            alicuota=Decimal("40.0000"),
        )
        session.add_all([unidad_a, unidad_b])
        await session.flush()

        presidente = _crear_usuario_seed("Ana Presidente", "V-10000001", "pres@condo.test", "PRESIDENTE", pw_hash)
        tesorero = _crear_usuario_seed("Luis Tesorero", "V-10000002", "tes@condo.test", "TESORERO", pw_hash)
        secretario = _crear_usuario_seed("Mia Secretaria", "V-10000003", "sec@condo.test", "SECRETARIO", pw_hash)
        vocero = _crear_usuario_seed("Leo Vocero", "V-10000004", "voc@condo.test", "VOCERO", pw_hash)
        conserje = _crear_usuario_seed("Pedro Conserje", "V-10000005", "cons@condo.test", "CONSERJE", pw_hash)
        propietario = _crear_usuario_seed("Carlos Propietario", "V-10000006", "prop@condo.test", "PROPIETARIO", pw_hash)
        inquilino = _crear_usuario_seed("Eva Inquilina", "V-10000007", "inq@condo.test", "INQUILINO", pw_hash)
        session.add_all([presidente, tesorero, secretario, vocero, conserje, propietario, inquilino])
        await session.flush()

        session.add_all(
            [
                ContratoOcupacion(
                    condominio_id=1,
                    usuario_id=propietario.id,
                    unidad_id=unidad_a.id,
                    tipo_ocupante="PROPIETARIO",
                    es_activo=True,
                    puede_votar_asamblea=True,
                ),
                ContratoOcupacion(
                    condominio_id=1,
                    usuario_id=inquilino.id,
                    unidad_id=unidad_b.id,
                    tipo_ocupante="INQUILINO",
                    es_activo=True,
                    puede_votar_asamblea=False,
                ),
                TasaCambio(
                    condominio_id=1,
                    fecha=date.today(),
                    tasa_usd_ves=Decimal("45.5000"),
                ),
            ]
        )
        await session.commit()

        return SeededCondoContext(
            estructura_id=torre.id,
            unidad_a_id=unidad_a.id,
            unidad_b_id=unidad_b.id,
            presidente_id=presidente.id,
            tesorero_id=tesorero.id,
            secretario_id=secretario.id,
            vocero_id=vocero.id,
            conserje_id=conserje.id,
            propietario_id=propietario.id,
            inquilino_id=inquilino.id,
        )
