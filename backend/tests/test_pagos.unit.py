"""Pruebas unitarias del flujo de reporte y aprobación de pagos en SQLite FK real."""

import hashlib
import json
from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.database import get_db
from src.main import app
from src.models import AuditoriaRecibo, PagoReportado, Recibo, TasaCambio, Usuario
from src.redis_client import (
    acquire_idempotency_slot,
    build_scoped_idempotency_key,
    get_redis_client,
    reset_local_security_state,
)
from src.routers.pagos import _obtener_recibo, _obtener_unidad_bloqueada
from src.security import create_access_token, get_password_hash
from tests._sqlite_helpers import SeededCondoContext, create_sqlite_fk_factory, seed_condo_base

HEADERS = {"Idempotency-Key": "11111111-1111-1111-1111-111111111111"}
HEADERS_ALT = {"Idempotency-Key": "44444444-4444-4444-4444-444444444444"}


@pytest.fixture(autouse=True)
def _limpiar_estado_pagos() -> Generator[None]:
    """Aísla el estado local de idempotencia y overrides entre pruebas."""
    app.dependency_overrides.clear()
    reset_local_security_state()
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        reset_local_security_state()


def _cookies_usuario(correo: str, usuario_id: int, rol: str) -> dict[str, str]:
    token = create_access_token(data={"sub": correo, "id": usuario_id, "rol": rol, "condominio_id": 1})
    return {"access_token": f"Bearer {token}"}


@asynccontextmanager
async def _entorno_pagos(
    *,
    tasa_hoy: Decimal | None = Decimal("36.5000"),
) -> AsyncIterator[tuple[async_sessionmaker[AsyncSession], SeededCondoContext, AsyncClient]]:
    """Prepara SQLite FK real con semilla base y limpieza obligatoria en try...finally."""
    engine, factory = await create_sqlite_fk_factory()
    try:
        ctx = await seed_condo_base(factory)
        async with factory() as session:
            await session.execute(delete(TasaCambio))
            if tasa_hoy is not None:
                session.add(TasaCambio(condominio_id=1, fecha=date.today(), tasa_usd_ves=tasa_hoy))
            await session.commit()

        async def _override_get_db() -> AsyncIterator[AsyncSession]:
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_redis_client] = lambda: None
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
            yield factory, ctx, ac
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def _sembrar_recibo(
    factory: async_sessionmaker[AsyncSession],
    unidad_id: int,
    *,
    monto_usd: str = "100.00",
    pagado_usd: str = "0.00",
    estado: str = "PENDIENTE",
    bloqueado: bool = False,
) -> int:
    async with factory() as session:
        recibo = Recibo(
            condominio_id=1,
            unidad_id=unidad_id,
            periodo="2026-10",
            monto_usd=Decimal(monto_usd),
            monto_pagado_usd=Decimal(pagado_usd),
            estado=estado,
            bloqueado=bloqueado,
        )
        session.add(recibo)
        await session.commit()
        return recibo.id


async def _sembrar_pago(
    factory: async_sessionmaker[AsyncSession],
    recibo_id: int,
    usuario_id: int,
    *,
    monto_usd: str = "40.00",
    estado: str = "EN_REVISION",
    metodo_pago: str = "EFECTIVO",
    referencia: str | None = None,
) -> int:
    async with factory() as session:
        pago = PagoReportado(
            condominio_id=1,
            recibo_id=recibo_id,
            usuario_id=usuario_id,
            monto=Decimal(monto_usd),
            moneda="USD",
            monto_usd=Decimal(monto_usd),
            tasa_cambio=Decimal("36.5000"),
            metodo_pago=metodo_pago,
            numero_referencia=referencia,
            estado=estado,
        )
        session.add(pago)
        await session.commit()
        return pago.id


@pytest.mark.asyncio
async def test_reportar_pago_success() -> None:
    async with _entorno_pagos() as (factory, ctx, ac):
        recibo_id = await _sembrar_recibo(factory, ctx.unidad_a_id)
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        payload = {"recibo_id": recibo_id, "monto": "100.00", "moneda": "USD", "metodo_pago": "EFECTIVO"}

        response = await ac.post("/api/pagos/reportar", json=payload, headers=HEADERS, cookies=cookies)

        assert response.status_code == 201
        body = response.json()
        assert float(body["monto_usd"]) == 100.0
        assert float(body["tasa_cambio"]) == 36.5
        assert body["estado"] == "EN_REVISION"
        async with factory() as session:
            total = (await session.execute(select(func.count()).select_from(PagoReportado))).scalar_one()
            assert total == 1


@pytest.mark.asyncio
async def test_reportar_pago_ves_convierte_por_tasa_del_dia() -> None:
    async with _entorno_pagos() as (factory, ctx, ac):
        recibo_id = await _sembrar_recibo(factory, ctx.unidad_a_id)
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        payload = {"recibo_id": recibo_id, "monto": "3650.00", "moneda": "VES", "metodo_pago": "EFECTIVO"}

        response = await ac.post("/api/pagos/reportar", json=payload, headers=HEADERS, cookies=cookies)

        assert response.status_code == 201
        assert float(response.json()["monto_usd"]) == 100.0


@pytest.mark.asyncio
async def test_reportar_pago_duplicado() -> None:
    async with _entorno_pagos() as (factory, ctx, ac):
        recibo_id = await _sembrar_recibo(factory, ctx.unidad_a_id)
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        payload = {"recibo_id": recibo_id, "monto": "100.00", "moneda": "USD", "metodo_pago": "EFECTIVO"}
        raw_body = json.dumps(payload).encode("utf-8")
        redis_key = build_scoped_idempotency_key(1, ctx.tesorero_id, "reportar_pago", HEADERS["Idempotency-Key"])
        await acquire_idempotency_slot(None, redis_key, hashlib.sha256(raw_body).hexdigest())

        response = await ac.post(
            "/api/pagos/reportar",
            content=raw_body,
            headers={**HEADERS, "Content-Type": "application/json"},
            cookies=cookies,
        )

        assert response.status_code == 409
        assert "Petición duplicada" in response.json()["detail"]


@pytest.mark.asyncio
async def test_reportar_pago_zelle_sin_referencia_falla() -> None:
    async with _entorno_pagos() as (factory, ctx, ac):
        recibo_id = await _sembrar_recibo(factory, ctx.unidad_a_id)
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        payload = {"recibo_id": recibo_id, "monto": "100.00", "moneda": "USD", "metodo_pago": "ZELLE"}

        response = await ac.post("/api/pagos/reportar", json=payload, headers=HEADERS, cookies=cookies)

        assert response.status_code == 400
        assert "referencia" in response.json()["detail"]


@pytest.mark.asyncio
async def test_reportar_pago_tasa_no_registrada() -> None:
    async with _entorno_pagos(tasa_hoy=None) as (factory, ctx, ac):
        recibo_id = await _sembrar_recibo(factory, ctx.unidad_a_id)
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        payload = {"recibo_id": recibo_id, "monto": "100.00", "moneda": "USD", "metodo_pago": "EFECTIVO"}

        response = await ac.post("/api/pagos/reportar", json=payload, headers=HEADERS, cookies=cookies)

        assert response.status_code == 400
        assert "tasa de cambio" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_reportar_pago_recibo_no_encontrado() -> None:
    async with _entorno_pagos() as (_, ctx, ac):
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        payload = {"recibo_id": 99999, "monto": "100.00", "moneda": "USD", "metodo_pago": "EFECTIVO"}

        response = await ac.post("/api/pagos/reportar", json=payload, headers=HEADERS, cookies=cookies)

        assert response.status_code == 404
        assert "Recibo no encontrado" in response.json()["detail"]


@pytest.mark.asyncio
async def test_reportar_pago_mes_bloqueado() -> None:
    async with _entorno_pagos() as (factory, ctx, ac):
        recibo_id = await _sembrar_recibo(factory, ctx.unidad_a_id, bloqueado=True)
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        payload = {"recibo_id": recibo_id, "monto": "100.00", "moneda": "USD", "metodo_pago": "EFECTIVO"}

        response = await ac.post("/api/pagos/reportar", json=payload, headers=HEADERS, cookies=cookies)

        assert response.status_code == 409
        assert "Candado Contable" in response.json()["detail"]


@pytest.mark.asyncio
async def test_reportar_pago_moneda_invalida_es_422() -> None:
    async with _entorno_pagos() as (_, ctx, ac):
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        payload = {"recibo_id": 1, "monto": "10.00", "moneda": "EUR", "metodo_pago": "EFECTIVO"}
        response = await ac.post("/api/pagos/reportar", json=payload, headers=HEADERS, cookies=cookies)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_reportar_pago_sin_idempotency_key() -> None:
    async with _entorno_pagos() as (_, ctx, ac):
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        payload = {"recibo_id": 1, "monto": "100.00", "moneda": "USD", "metodo_pago": "EFECTIVO"}
        response = await ac.post("/api/pagos/reportar", json=payload, cookies=cookies)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_reportar_pago_falla_bd(monkeypatch: pytest.MonkeyPatch) -> None:
    async with _entorno_pagos() as (factory, ctx, ac):
        recibo_id = await _sembrar_recibo(factory, ctx.unidad_a_id)
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        payload = {"recibo_id": recibo_id, "monto": "100.00", "moneda": "USD", "metodo_pago": "EFECTIVO"}

        async with factory() as real_session:

            async def _fallar_commit() -> None:
                raise SQLAlchemyError("DB down")

            monkeypatch.setattr(real_session, "commit", _fallar_commit)
            app.dependency_overrides[get_db] = lambda: real_session
            response = await ac.post("/api/pagos/reportar", json=payload, headers=HEADERS, cookies=cookies)

        assert response.status_code == 500
        assert "Error en base de datos" in response.json()["detail"]
        async with factory() as check_session:
            total = (await check_session.execute(select(func.count()).select_from(PagoReportado))).scalar_one()
            assert total == 0


@pytest.mark.asyncio
async def test_listar_pagos_en_revision() -> None:
    async with _entorno_pagos() as (factory, ctx, ac):
        recibo_id = await _sembrar_recibo(factory, ctx.unidad_a_id)
        await _sembrar_pago(factory, recibo_id, ctx.propietario_id, estado="EN_REVISION")
        await _sembrar_pago(factory, recibo_id, ctx.propietario_id, estado="APROBADO")
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")

        response = await ac.get("/api/pagos/revision", cookies=cookies)

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["estado"] == "EN_REVISION"


@pytest.mark.asyncio
async def test_aprobar_pago_parcial() -> None:
    async with _entorno_pagos() as (factory, ctx, ac):
        recibo_id = await _sembrar_recibo(factory, ctx.unidad_a_id)
        pago_id = await _sembrar_pago(factory, recibo_id, ctx.propietario_id, monto_usd="40.00")
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")

        response = await ac.put(f"/api/pagos/{pago_id}/aprobar", headers=HEADERS, cookies=cookies)

        assert response.status_code == 200
        assert response.json()["estado"] == "APROBADO"
        async with factory() as session:
            recibo = await session.get(Recibo, recibo_id)
            audits = list((await session.execute(select(AuditoriaRecibo))).scalars().all())
            assert recibo is not None
            assert recibo.estado == "PAGADO_PARCIAL"
            assert recibo.monto_pagado_usd == Decimal("40.00")
            assert len(audits) == 1


@pytest.mark.asyncio
async def test_aprobar_pago_total_exacto() -> None:
    async with _entorno_pagos() as (factory, ctx, ac):
        recibo_id = await _sembrar_recibo(factory, ctx.unidad_a_id)
        pago_id = await _sembrar_pago(factory, recibo_id, ctx.propietario_id, monto_usd="100.00")
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")

        response = await ac.put(f"/api/pagos/{pago_id}/aprobar", headers=HEADERS, cookies=cookies)

        assert response.status_code == 200
        async with factory() as session:
            recibo = await session.get(Recibo, recibo_id)
            assert recibo is not None
            assert recibo.estado == "PAGADO"
            assert recibo.monto_pagado_usd == Decimal("100.00")


@pytest.mark.asyncio
async def test_aprobar_pago_parcial_sobre_saldo_previo() -> None:
    async with _entorno_pagos() as (factory, ctx, ac):
        recibo_id = await _sembrar_recibo(factory, ctx.unidad_a_id, pagado_usd="40.00", estado="PAGADO_PARCIAL")
        pago_id = await _sembrar_pago(factory, recibo_id, ctx.propietario_id, monto_usd="30.00")
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")

        response = await ac.put(f"/api/pagos/{pago_id}/aprobar", headers=HEADERS, cookies=cookies)

        assert response.status_code == 200
        async with factory() as session:
            recibo = await session.get(Recibo, recibo_id)
            assert recibo is not None
            assert recibo.monto_pagado_usd == Decimal("70.00")
            assert recibo.estado == "PAGADO_PARCIAL"


@pytest.mark.asyncio
async def test_aprobar_pago_no_encontrado() -> None:
    async with _entorno_pagos() as (_, ctx, ac):
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        response = await ac.put("/api/pagos/99999/aprobar", headers=HEADERS, cookies=cookies)
        assert response.status_code == 404
        assert "Pago no encontrado" in response.json()["detail"]


@pytest.mark.asyncio
async def test_aprobar_pago_no_esta_en_revision() -> None:
    async with _entorno_pagos() as (factory, ctx, ac):
        recibo_id = await _sembrar_recibo(factory, ctx.unidad_a_id)
        pago_id = await _sembrar_pago(factory, recibo_id, ctx.propietario_id, estado="APROBADO")
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")

        response = await ac.put(f"/api/pagos/{pago_id}/aprobar", headers=HEADERS, cookies=cookies)
        assert response.status_code == 409
        assert "no está en revisión" in response.json()["detail"]


@pytest.mark.asyncio
async def test_aprobar_recibo_no_encontrado() -> None:
    async with _entorno_pagos() as (factory, ctx, _):
        # PRAGMA foreign_keys=ON impide insertar PagoReportado sin recibo válido; validamos FK y la guardia 404 real.
        async with factory() as session:
            session.add(
                PagoReportado(
                    condominio_id=1,
                    recibo_id=99999,
                    usuario_id=ctx.propietario_id,
                    monto=Decimal("10.00"),
                    moneda="USD",
                    monto_usd=Decimal("10.00"),
                    tasa_cambio=Decimal("36.5000"),
                    metodo_pago="EFECTIVO",
                    estado="EN_REVISION",
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

            with pytest.raises(HTTPException) as exc_rec:
                await _obtener_recibo(session, 99999, for_update=True)
            assert exc_rec.value.status_code == 404
            assert "Recibo no encontrado" in exc_rec.value.detail


@pytest.mark.asyncio
async def test_aprobar_mes_bloqueado() -> None:
    async with _entorno_pagos() as (factory, ctx, ac):
        recibo_id = await _sembrar_recibo(factory, ctx.unidad_a_id, bloqueado=True)
        pago_id = await _sembrar_pago(factory, recibo_id, ctx.propietario_id)
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")

        response = await ac.put(f"/api/pagos/{pago_id}/aprobar", headers=HEADERS, cookies=cookies)
        assert response.status_code == 409
        assert "Candado Contable" in response.json()["detail"]


@pytest.mark.asyncio
async def test_rechazar_pago_success() -> None:
    async with _entorno_pagos() as (factory, ctx, ac):
        recibo_id = await _sembrar_recibo(factory, ctx.unidad_a_id)
        pago_id = await _sembrar_pago(factory, recibo_id, ctx.propietario_id)
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")

        response = await ac.put(
            f"/api/pagos/{pago_id}/rechazar",
            headers=HEADERS,
            cookies=cookies,
            json={"motivo": "Comprobante ilegible"},
        )

        assert response.status_code == 200
        assert response.json()["estado"] == "RECHAZADO"
        async with factory() as session:
            pago = await session.get(PagoReportado, pago_id)
            audit = (await session.execute(select(AuditoriaRecibo))).scalars().first()
            assert pago is not None and pago.estado == "RECHAZADO"
            assert audit is not None
            assert audit.motivo == "Comprobante ilegible"
            assert audit.estado_viejo == "PENDIENTE"
            assert audit.estado_nuevo == "PENDIENTE"


@pytest.mark.asyncio
async def test_rechazar_pago_sin_motivo_es_422() -> None:
    async with _entorno_pagos() as (_, ctx, ac):
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        response = await ac.put("/api/pagos/5/rechazar", headers=HEADERS, cookies=cookies, json={"motivo": ""})
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_rechazar_pago_no_encontrado() -> None:
    async with _entorno_pagos() as (_, ctx, ac):
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        response = await ac.put("/api/pagos/99999/rechazar", headers=HEADERS, cookies=cookies, json={"motivo": "X"})
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_rechazar_pago_no_esta_en_revision() -> None:
    async with _entorno_pagos() as (factory, ctx, ac):
        recibo_id = await _sembrar_recibo(factory, ctx.unidad_a_id)
        pago_id = await _sembrar_pago(factory, recibo_id, ctx.propietario_id, estado="RECHAZADO")
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")

        response = await ac.put(
            f"/api/pagos/{pago_id}/rechazar", headers=HEADERS, cookies=cookies, json={"motivo": "X"}
        )
        assert response.status_code == 409


@pytest.mark.asyncio
async def test_rechazar_mes_bloqueado() -> None:
    async with _entorno_pagos() as (factory, ctx, ac):
        recibo_id = await _sembrar_recibo(factory, ctx.unidad_a_id, bloqueado=True)
        pago_id = await _sembrar_pago(factory, recibo_id, ctx.propietario_id)
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")

        response = await ac.put(
            f"/api/pagos/{pago_id}/rechazar", headers=HEADERS, cookies=cookies, json={"motivo": "X"}
        )
        assert response.status_code == 409
        assert "Candado Contable" in response.json()["detail"]


@pytest.mark.asyncio
async def test_pagos_rbac_y_bloqueo_fantasma() -> None:
    async with _entorno_pagos() as (factory, ctx, ac):
        recibo_id = await _sembrar_recibo(factory, ctx.unidad_a_id)
        pago_id = await _sembrar_pago(factory, recibo_id, ctx.propietario_id)
        async with factory() as session:
            fantasma = Usuario(
                condominio_id=1,
                nombre="Fantasma",
                cedula="V-99999999",
                correo="fantasma@test.com",
                telefono="0414",
                password_hash=get_password_hash("Clave1234!"),
                es_activo=False,
                rol="FANTASMA",
            )
            session.add(fantasma)
            await session.commit()
            fantasma_id = fantasma.id

        cookies_ghost = _cookies_usuario("fantasma@test.com", fantasma_id, "FANTASMA")
        payload = {"recibo_id": recibo_id, "monto": "100.00", "moneda": "USD", "metodo_pago": "EFECTIVO"}
        res_ghost = await ac.post("/api/pagos/reportar", json=payload, headers=HEADERS, cookies=cookies_ghost)
        assert res_ghost.status_code == 403

        cookies_prop = _cookies_usuario("prop@condo.test", ctx.propietario_id, "PROPIETARIO")
        assert (await ac.get("/api/pagos/revision", cookies=cookies_prop)).status_code == 403
        assert (await ac.put(f"/api/pagos/{pago_id}/aprobar", headers=HEADERS, cookies=cookies_prop)).status_code == 403
        assert (
            await ac.put(
                f"/api/pagos/{pago_id}/rechazar",
                headers=HEADERS,
                cookies=cookies_prop,
                json={"motivo": "Motivo válido"},
            )
        ).status_code == 403


@pytest.mark.asyncio
async def test_aprobar_pago_sin_idempotency_key_duplicado_y_unidad_inexistente() -> None:
    async with _entorno_pagos() as (factory, ctx, ac):
        recibo_id = await _sembrar_recibo(factory, ctx.unidad_a_id)
        pago_id = await _sembrar_pago(factory, recibo_id, ctx.propietario_id)
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")

        assert (await ac.put(f"/api/pagos/{pago_id}/aprobar", cookies=cookies)).status_code == 422

        res_ok = await ac.put(f"/api/pagos/{pago_id}/aprobar", headers=HEADERS, cookies=cookies)
        assert res_ok.status_code == 200
        res_dup = await ac.put(f"/api/pagos/{pago_id}/aprobar", headers=HEADERS, content=b"{}", cookies=cookies)
        assert res_dup.status_code == 409
        assert "Idempotency-Key" in res_dup.json()["detail"]

        # PRAGMA foreign_keys=ON impide crear recibos con unidad inexistente; validamos FK y la guardia 404 real.
        async with factory() as session:
            session.add(
                Recibo(
                    condominio_id=1,
                    unidad_id=99999,
                    periodo="2026-11",
                    monto_usd=Decimal("10.00"),
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

            with pytest.raises(HTTPException) as exc_uni:
                await _obtener_unidad_bloqueada(session, 99999)
            assert exc_uni.value.status_code == 404
            assert "Unidad" in exc_uni.value.detail


@pytest.mark.asyncio
async def test_reportar_pago_anti_idor_y_colision_integrity_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async with _entorno_pagos() as (factory, ctx, ac):
        recibo_id = await _sembrar_recibo(factory, ctx.unidad_a_id)
        payload = {"recibo_id": recibo_id, "monto": "100.00", "moneda": "USD", "metodo_pago": "EFECTIVO"}

        # Inquilino sin ContratoOcupacion sobre unidad_a_id -> 403 anti-IDOR
        cookies_inq = _cookies_usuario("inq@condo.test", ctx.inquilino_id, "INQUILINO")
        res_idor = await ac.post("/api/pagos/reportar", json=payload, headers=HEADERS, cookies=cookies_inq)
        assert res_idor.status_code == 403
        assert "autorización" in res_idor.json()["detail"]

        # Propietario con ContratoOcupacion activo sobre unidad_a_id -> 201 OK
        cookies_prop = _cookies_usuario("prop@condo.test", ctx.propietario_id, "PROPIETARIO")
        res_ok = await ac.post("/api/pagos/reportar", json=payload, headers=HEADERS, cookies=cookies_prop)
        assert res_ok.status_code == 201

        # IntegrityError concurrente sobre referencia única parcial -> 409 Conflict
        cookies_tes = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        async with factory() as real_session:

            async def _fallar_integridad() -> None:
                raise IntegrityError("dup", {}, Exception("uq_pagos_metodo_ref_activo"))

            monkeypatch.setattr(real_session, "commit", _fallar_integridad)
            app.dependency_overrides[get_db] = lambda: real_session
            res_ie = await ac.post(
                "/api/pagos/reportar",
                json={
                    "recibo_id": recibo_id,
                    "monto": "100.00",
                    "moneda": "USD",
                    "metodo_pago": "ZELLE",
                    "numero_referencia": "REF-RACE-01",
                },
                headers=HEADERS_ALT,
                cookies=cookies_tes,
            )

        assert res_ie.status_code == 409
        assert "referencia bancaria" in res_ie.json()["detail"]
