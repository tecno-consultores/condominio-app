"""Pruebas reales SQLite (sin mocks de sesión) para Hito 17.3: restricciones únicas, anti-IDOR y Candado Contable."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.database import Base, get_db
from src.dependencies import get_current_user
from src.main import app
from src.models import (
    ContratoOcupacion,
    Estructura,
    PagoReportado,
    Recibo,
    TasaCambio,
    Unidad,
    Usuario,
)
from src.redis_client import get_redis_client
from src.security import get_password_hash

HEADERS = {"Idempotency-Key": "17300000-0000-4000-8000-000000000173"}


async def _crear_motor_y_datos(tmp_path: Path) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    db_file = f"{tmp_path}/hito17_3.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as s:
        est = Estructura(nombre="Torre Central", tipo="TORRE")
        s.add(est)
        await s.flush()
        u1 = Unidad(identificador="A-01", estructura_id=est.id, alicuota=Decimal("60.0000"))
        u2 = Unidad(identificador="A-02", estructura_id=est.id, alicuota=Decimal("40.0000"))
        s.add_all([u1, u2])
        await s.flush()
        pw = get_password_hash("Password123!")
        tesorero = Usuario(
            nombre="Tesorero Real",
            cedula="V-10000001",
            correo="tesorero.real@test.com",
            telefono="+584140000001",
            password_hash=pw,
            es_activo=True,
            rol="TESORERO",
        )
        vecino1 = Usuario(
            nombre="Vecino Uno",
            cedula="V-10000002",
            correo="vecino1.real@test.com",
            telefono="+584140000002",
            password_hash=pw,
            es_activo=True,
            rol="PROPIETARIO",
        )
        s.add_all([tesorero, vecino1])
        await s.flush()
        s.add(
            ContratoOcupacion(
                usuario_id=vecino1.id,
                unidad_id=u1.id,
                tipo_ocupante="PROPIETARIO",
                es_activo=True,
            )
        )
        s.add(TasaCambio(fecha=date.today(), tasa_usd_ves=Decimal("40.0000")))
        s.add_all(
            [
                Recibo(unidad_id=u1.id, periodo="2026-10", monto_usd=Decimal("100.00")),
                Recibo(unidad_id=u2.id, periodo="2026-10", monto_usd=Decimal("80.00")),
            ]
        )
        await s.commit()
    return engine, session_factory


@pytest.mark.asyncio
async def test_ddl_unicidad_recibo_e_indice_parcial_pagos(tmp_path: Path) -> None:
    db_file = f"{tmp_path}/ddl_constraints.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as s:
        est = Estructura(nombre="Torre Único", tipo="TORRE")
        s.add(est)
        await s.flush()
        u1 = Unidad(identificador="U-1", estructura_id=est.id, alicuota=Decimal("100.0000"))
        usr = Usuario(
            nombre="Titular DDL",
            cedula="V-20000001",
            correo="ddl@test.com",
            telefono="+584140000099",
            password_hash=get_password_hash("Password123!"),
            es_activo=True,
            rol="PROPIETARIO",
        )
        s.add_all([u1, usr])
        await s.flush()

        r1 = Recibo(unidad_id=u1.id, periodo="2026-10", monto_usd=Decimal("50.00"))
        s.add(r1)
        await s.commit()
        r1_id = r1.id
        usr_id = usr.id

        # Segundo recibo misma (unidad_id, periodo) debe violar uq_recibo_unidad_periodo
        s.add(Recibo(unidad_id=u1.id, periodo="2026-10", monto_usd=Decimal("75.00")))
        with pytest.raises(IntegrityError):
            await s.commit()
        await s.rollback()

        # Pago activo con referencia duplicada viola uq_pagos_metodo_ref_activo
        p1 = PagoReportado(
            recibo_id=r1_id,
            usuario_id=usr_id,
            monto=Decimal("50.00"),
            moneda="USD",
            monto_usd=Decimal("50.00"),
            tasa_cambio=Decimal("40.0000"),
            metodo_pago="ZELLE",
            numero_referencia="ZELLE-REF-1",
            estado="EN_REVISION",
        )
        s.add(p1)
        await s.commit()
        p1_id = p1.id

        s.add(
            PagoReportado(
                recibo_id=r1_id,
                usuario_id=usr_id,
                monto=Decimal("50.00"),
                moneda="USD",
                monto_usd=Decimal("50.00"),
                tasa_cambio=Decimal("40.0000"),
                metodo_pago="ZELLE",
                numero_referencia="ZELLE-REF-1",
                estado="EN_REVISION",
            )
        )
        with pytest.raises(IntegrityError):
            await s.commit()
        await s.rollback()

        # Tras pasar p1 a RECHAZADO, la misma referencia SÍ puede reutilizarse en nuevo reporte
        p1_db = await s.get(PagoReportado, p1_id)
        assert p1_db is not None
        p1_db.estado = "RECHAZADO"
        await s.commit()

        s.add(
            PagoReportado(
                recibo_id=r1_id,
                usuario_id=usr_id,
                monto=Decimal("50.00"),
                moneda="USD",
                monto_usd=Decimal("50.00"),
                tasa_cambio=Decimal("40.0000"),
                metodo_pago="ZELLE",
                numero_referencia="ZELLE-REF-1",
                estado="EN_REVISION",
            )
        )
        # Múltiples pagos EFECTIVO con referencia None permitidos por índice parcial
        s.add_all(
            [
                PagoReportado(
                    recibo_id=r1_id,
                    usuario_id=usr_id,
                    monto=Decimal("10.00"),
                    moneda="USD",
                    monto_usd=Decimal("10.00"),
                    tasa_cambio=Decimal("40.0000"),
                    metodo_pago="EFECTIVO",
                    numero_referencia=None,
                    estado="EN_REVISION",
                ),
                PagoReportado(
                    recibo_id=r1_id,
                    usuario_id=usr_id,
                    monto=Decimal("15.00"),
                    moneda="USD",
                    monto_usd=Decimal("15.00"),
                    tasa_cambio=Decimal("40.0000"),
                    metodo_pago="EFECTIVO",
                    numero_referencia=None,
                    estado="EN_REVISION",
                ),
            ]
        )
        await s.commit()

    await engine.dispose()


@pytest.mark.asyncio
async def test_flujo_real_anti_idor_sobrepago_y_candado_contable_egresos(
    client: TestClient,
    tmp_path: Path,
) -> None:
    engine, factory = await _crear_motor_y_datos(tmp_path)

    async def _override_db() -> AsyncIterator[AsyncSession]:
        async with factory() as s:
            yield s

    mock_redis = AsyncMock()
    mock_redis.set.return_value = True

    async with factory() as s:
        tesorero = (await s.execute(select(Usuario).where(Usuario.rol == "TESORERO"))).scalars().one()
        vecino1 = (await s.execute(select(Usuario).where(Usuario.rol == "PROPIETARIO"))).scalars().one()
        recibos = list((await s.execute(select(Recibo).order_by(Recibo.id.asc()))).scalars().all())
        r_u1, r_u2 = recibos[0], recibos[1]

    try:
        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_redis_client] = lambda: mock_redis

        # 1. Vecino1 no puede reportar pago sobre recibo de Unidad 2 (IDOR -> 403)
        app.dependency_overrides[get_current_user] = lambda: vecino1
        res_idor = client.post(
            "/api/pagos/reportar",
            json={
                "recibo_id": r_u2.id,
                "monto": "80.00",
                "moneda": "USD",
                "metodo_pago": "ZELLE",
                "numero_referencia": "REF-IDOR-01",
            },
            headers={"Idempotency-Key": "17300000-0000-4000-8000-000000000001"},
        )
        assert res_idor.status_code == 403

        # 2. Vecino1 reporta sobrepago de $130 sobre su propio recibo de $100 -> 201
        res_pago = client.post(
            "/api/pagos/reportar",
            json={
                "recibo_id": r_u1.id,
                "monto": "130.00",
                "moneda": "USD",
                "metodo_pago": "ZELLE",
                "numero_referencia": "  REF-REAL-001  ",
            },
            headers={"Idempotency-Key": "17300000-0000-4000-8000-000000000002"},
        )
        assert res_pago.status_code == 201
        pago_id = res_pago.json()["id"]
        assert res_pago.json()["numero_referencia"] == "REF-REAL-001"

        # 3. Tesorero aprueba pago atómicamente acreditando $30 a Unidad 1
        app.dependency_overrides[get_current_user] = lambda: tesorero
        res_aprob = client.put(
            f"/api/pagos/{pago_id}/aprobar",
            headers={"Idempotency-Key": "17300000-0000-4000-8000-000000000003"},
        )
        assert res_aprob.status_code == 200
        assert res_aprob.json()["estado"] == "APROBADO"

        async with factory() as s:
            u1_db = (await s.execute(select(Unidad).where(Unidad.identificador == "A-01"))).scalars().one()
            r1_db = (await s.execute(select(Recibo).where(Recibo.id == r_u1.id))).scalars().one()
            assert r1_db.estado == "PAGADO"
            assert r1_db.monto_pagado_usd == Decimal("100.00")
            assert u1_db.credito_disponible_usd == Decimal("30.00")

        # 4. Cierre mensual bloquea nuevos egresos en el mismo periodo (409 Conflict)
        res_cierre = client.post("/api/finanzas/cierre-mensual", json={"periodo": "2026-10"})
        assert res_cierre.status_code == 200

        res_egreso_post_cierre = client.post(
            "/api/finanzas/egresos",
            json={
                "periodo": "2026-10",
                "categoria": "MANTENIMIENTO",
                "descripcion": "Intento tras cierre",
                "monto": "20.00",
                "moneda": "USD",
            },
            headers={"Idempotency-Key": "17300000-0000-4000-8000-000000000004"},
        )
        assert res_egreso_post_cierre.status_code == 409
        assert "Candado Contable" in res_egreso_post_cierre.json()["detail"]
    finally:
        app.dependency_overrides = {}
        await engine.dispose()
