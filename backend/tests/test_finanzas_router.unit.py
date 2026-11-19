"""Pruebas unitarias de tesorería: tasa del día, resumen y Candado Contable en SQLite FK real."""

from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.database import get_db
from src.main import app
from src.models import Egreso, Recibo, ReporteMensual, TasaCambio, Unidad, Usuario
from src.redis_client import get_redis_client, reset_local_security_state
from src.security import create_access_token, get_password_hash
from tests._sqlite_helpers import SeededCondoContext, create_sqlite_fk_factory, seed_condo_base

HEADERS = {"Idempotency-Key": "22222222-2222-2222-2222-222222222222"}
HEADERS_ALT = {"Idempotency-Key": "33333333-3333-3333-3333-333333333333"}


@pytest.fixture(autouse=True)
def _limpiar_estado_finanzas() -> Generator[None]:
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
async def _entorno_finanzas(
    *,
    tasa_hoy: Decimal | None = Decimal("36.5000"),
) -> AsyncIterator[tuple[async_sessionmaker[AsyncSession], SeededCondoContext, AsyncClient]]:
    """Crea un entorno SQLite FK real aislado con limpieza garantizada en try...finally."""
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


@pytest.mark.asyncio
async def test_registrar_tasa_nueva() -> None:
    async with _entorno_finanzas(tasa_hoy=None) as (factory, ctx, ac):
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        response = await ac.post(
            "/api/finanzas/tasa",
            headers=HEADERS,
            cookies=cookies,
            json={"tasa_usd_ves": "36.5000"},
        )

        assert response.status_code == 201
        assert float(response.json()["tasa_usd_ves"]) == 36.5
        async with factory() as session:
            total = (await session.execute(select(func.count()).select_from(TasaCambio))).scalar_one()
            assert total == 1


@pytest.mark.asyncio
async def test_registrar_tasa_existente_actualiza() -> None:
    fecha_obj = date(2026, 10, 12)
    async with _entorno_finanzas(tasa_hoy=None) as (factory, ctx, ac):
        async with factory() as session:
            session.add(TasaCambio(condominio_id=1, fecha=fecha_obj, tasa_usd_ves=Decimal("36.5000")))
            await session.commit()

        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        response = await ac.post(
            "/api/finanzas/tasa",
            headers=HEADERS,
            cookies=cookies,
            json={"fecha": "2026-10-12", "tasa_usd_ves": "40.0000"},
        )

        assert response.status_code == 201
        async with factory() as session:
            tasas = list((await session.execute(select(TasaCambio))).scalars().all())
            assert len(tasas) == 1
            assert tasas[0].tasa_usd_ves == Decimal("40.0000")


@pytest.mark.asyncio
async def test_registrar_tasa_invalida_es_422() -> None:
    async with _entorno_finanzas() as (_, ctx, ac):
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        response = await ac.post("/api/finanzas/tasa", headers=HEADERS, cookies=cookies, json={"tasa_usd_ves": "0"})
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_obtener_tasa_del_dia() -> None:
    async with _entorno_finanzas(tasa_hoy=Decimal("36.5000")) as (_, ctx, ac):
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        response = await ac.get("/api/finanzas/tasa", cookies=cookies)
        assert response.status_code == 200
        assert float(response.json()["tasa_usd_ves"]) == 36.5


@pytest.mark.asyncio
async def test_obtener_tasa_no_registrada() -> None:
    async with _entorno_finanzas(tasa_hoy=None) as (_, ctx, ac):
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        response = await ac.get("/api/finanzas/tasa", cookies=cookies)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_registrar_egreso_success() -> None:
    async with _entorno_finanzas(tasa_hoy=Decimal("36.5000")) as (factory, ctx, ac):
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        payload = {
            "periodo": "2026-10",
            "categoria": "MANTENIMIENTO",
            "descripcion": "Cambio de bombillos",
            "monto": "3650.00",
            "moneda": "VES",
        }
        response = await ac.post("/api/finanzas/egresos", json=payload, headers=HEADERS, cookies=cookies)

        assert response.status_code == 201
        assert float(response.json()["monto_usd"]) == 100.0
        async with factory() as session:
            egreso = (await session.execute(select(Egreso))).scalars().first()
            assert egreso is not None
            assert egreso.monto_usd == Decimal("100.00")


@pytest.mark.asyncio
async def test_registrar_egreso_sin_tasa() -> None:
    async with _entorno_finanzas(tasa_hoy=None) as (_, ctx, ac):
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        payload = {
            "periodo": "2026-10",
            "categoria": "MANTENIMIENTO",
            "descripcion": "X",
            "monto": "100.00",
            "moneda": "USD",
        }
        response = await ac.post("/api/finanzas/egresos", json=payload, headers=HEADERS, cookies=cookies)
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_registrar_egreso_falla_bd(monkeypatch: pytest.MonkeyPatch) -> None:
    async with _entorno_finanzas(tasa_hoy=Decimal("36.5000")) as (factory, ctx, ac):
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        payload = {
            "periodo": "2026-10",
            "categoria": "MANTENIMIENTO",
            "descripcion": "X",
            "monto": "100.00",
            "moneda": "USD",
        }
        async with factory() as real_session:

            async def _fallar_commit() -> None:
                raise SQLAlchemyError("DB down")

            monkeypatch.setattr(real_session, "commit", _fallar_commit)
            app.dependency_overrides[get_db] = lambda: real_session
            response = await ac.post("/api/finanzas/egresos", json=payload, headers=HEADERS, cookies=cookies)

        assert response.status_code == 500
        async with factory() as check_session:
            total = (await check_session.execute(select(func.count()).select_from(Egreso))).scalar_one()
            assert total == 0


@pytest.mark.asyncio
async def test_registrar_egreso_periodo_invalido_es_422() -> None:
    async with _entorno_finanzas() as (_, ctx, ac):
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        payload = {
            "periodo": "2026/10",
            "categoria": "MANTENIMIENTO",
            "descripcion": "X",
            "monto": "100.00",
            "moneda": "USD",
        }
        response = await ac.post("/api/finanzas/egresos", json=payload, headers=HEADERS, cookies=cookies)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_registrar_egreso_tasa_cero_falla() -> None:
    async with _entorno_finanzas(tasa_hoy=Decimal("10.0000")) as (factory, ctx, ac):
        # El CheckConstraint real de SQLite impide persistir tasa <= 0 en BD.
        async with factory() as session:
            session.add(TasaCambio(condominio_id=1, fecha=date(2026, 10, 1), tasa_usd_ves=Decimal("0")))
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        payload = {
            "periodo": "2026-10",
            "categoria": "MANTENIMIENTO",
            "descripcion": "Monto VES que cuantiza a 0.00 USD",
            "monto": "0.01",
            "moneda": "VES",
        }
        response = await ac.post("/api/finanzas/egresos", json=payload, headers=HEADERS, cookies=cookies)
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_registrar_egreso_candado_contable_e_idempotencia() -> None:
    async with _entorno_finanzas(tasa_hoy=Decimal("36.5000")) as (factory, ctx, ac):
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        payload = {
            "periodo": "2026-10",
            "categoria": "MANTENIMIENTO",
            "descripcion": "Gasto extemporáneo tras cierre",
            "monto": "50.00",
            "moneda": "USD",
        }

        # 1. Falta Idempotency-Key -> 422
        assert (await ac.post("/api/finanzas/egresos", json=payload, cookies=cookies)).status_code == 422

        # 2. Idempotency-Key repetida con distinto cuerpo -> 409
        res_ok = await ac.post("/api/finanzas/egresos", json=payload, headers=HEADERS, cookies=cookies)
        assert res_ok.status_code == 201
        res_dup = await ac.post(
            "/api/finanzas/egresos",
            json={**payload, "monto": "55.00"},
            headers=HEADERS,
            cookies=cookies,
        )
        assert res_dup.status_code == 409
        assert "Idempotency-Key" in res_dup.json()["detail"]

        # 3. Periodo cerrado en ReporteMensual -> 409 Candado Contable
        async with factory() as session:
            session.add(ReporteMensual(condominio_id=1, periodo="2026-10", estado="CERRADO"))
            await session.commit()

        res_cerrado = await ac.post("/api/finanzas/egresos", json=payload, headers=HEADERS_ALT, cookies=cookies)
        assert res_cerrado.status_code == 409
        assert "Candado Contable" in res_cerrado.json()["detail"]


@pytest.mark.asyncio
async def test_resumen_financiero() -> None:
    async with _entorno_finanzas(tasa_hoy=Decimal("36.5000")) as (factory, ctx, ac):
        async with factory() as session:
            unidad_c = Unidad(
                condominio_id=1,
                identificador="1-C",
                estructura_id=ctx.estructura_id,
                alicuota=Decimal("0.0000"),
            )
            session.add(unidad_c)
            await session.flush()
            session.add_all(
                [
                    Recibo(
                        condominio_id=1,
                        unidad_id=ctx.unidad_a_id,
                        periodo="2026-10",
                        monto_usd=Decimal("100.00"),
                        monto_pagado_usd=Decimal("0.00"),
                        estado="PENDIENTE",
                        bloqueado=False,
                    ),
                    Recibo(
                        condominio_id=1,
                        unidad_id=ctx.unidad_b_id,
                        periodo="2026-10",
                        monto_usd=Decimal("50.00"),
                        monto_pagado_usd=Decimal("50.00"),
                        estado="PAGADO",
                        bloqueado=False,
                    ),
                    Recibo(
                        condominio_id=1,
                        unidad_id=unidad_c.id,
                        periodo="2026-10",
                        monto_usd=Decimal("200.00"),
                        monto_pagado_usd=Decimal("100.00"),
                        estado="PAGADO_PARCIAL",
                        bloqueado=False,
                    ),
                    Egreso(
                        condominio_id=1,
                        periodo="2026-10",
                        categoria="MANTENIMIENTO",
                        descripcion="Reparación",
                        monto=Decimal("30.00"),
                        moneda="USD",
                        monto_usd=Decimal("30.00"),
                        tasa_cambio=Decimal("36.5000"),
                        bloqueado=False,
                    ),
                    Egreso(
                        condominio_id=1,
                        periodo="2026-10",
                        categoria="LIMPIEZA",
                        descripcion="Insumos",
                        monto=Decimal("70.00"),
                        moneda="USD",
                        monto_usd=Decimal("70.00"),
                        tasa_cambio=Decimal("36.5000"),
                        bloqueado=False,
                    ),
                ]
            )
            await session.commit()

        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        response = await ac.get("/api/finanzas/resumen", cookies=cookies)

        assert response.status_code == 200
        body = response.json()
        assert float(body["deuda_total_usd"]) == 200.0
        assert float(body["total_egresos_usd"]) == 100.0
        assert float(body["gastos_por_categoria"]["MANTENIMIENTO"]) == 30.0
        assert float(body["gastos_por_categoria"]["LIMPIEZA"]) == 70.0
        assert len(body["estado_cobranza"]) == 3


@pytest.mark.asyncio
async def test_cierre_mensual_success() -> None:
    async with _entorno_finanzas() as (factory, ctx, ac):
        async with factory() as session:
            recibo = Recibo(
                condominio_id=1,
                unidad_id=ctx.unidad_a_id,
                periodo="2026-10",
                monto_usd=Decimal("100.00"),
                monto_pagado_usd=Decimal("0.00"),
                estado="PENDIENTE",
                bloqueado=False,
            )
            egreso = Egreso(
                condominio_id=1,
                periodo="2026-10",
                categoria="MANTENIMIENTO",
                descripcion="Pago servicio",
                monto=Decimal("30.00"),
                moneda="USD",
                monto_usd=Decimal("30.00"),
                tasa_cambio=Decimal("36.5000"),
                bloqueado=False,
            )
            session.add_all([recibo, egreso])
            await session.commit()
            recibo_id, egreso_id = recibo.id, egreso.id

        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        response = await ac.post(
            "/api/finanzas/cierre-mensual",
            headers=HEADERS,
            cookies=cookies,
            json={"periodo": "2026-10"},
        )

        assert response.status_code == 200
        assert response.json()["estado"] == "CERRADO"
        async with factory() as session:
            rec_db = await session.get(Recibo, recibo_id)
            egr_db = await session.get(Egreso, egreso_id)
            rep_db = (
                (await session.execute(select(ReporteMensual).where(ReporteMensual.periodo == "2026-10")))
                .scalars()
                .first()
            )
            assert rec_db is not None and rec_db.bloqueado is True
            assert egr_db is not None and egr_db.bloqueado is True
            assert rep_db is not None and rep_db.estado == "CERRADO"


@pytest.mark.asyncio
async def test_cierre_mensual_ya_cerrado_es_inmutable() -> None:
    async with _entorno_finanzas() as (factory, ctx, ac):
        async with factory() as session:
            session.add(ReporteMensual(condominio_id=1, periodo="2026-10", estado="CERRADO"))
            await session.commit()

        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        response = await ac.post(
            "/api/finanzas/cierre-mensual",
            headers=HEADERS,
            cookies=cookies,
            json={"periodo": "2026-10"},
        )
        assert response.status_code == 409
        assert "inmutable" in response.json()["detail"]


@pytest.mark.asyncio
async def test_cierre_mensual_periodo_invalido_es_422() -> None:
    async with _entorno_finanzas() as (_, ctx, ac):
        cookies = _cookies_usuario("tes@condo.test", ctx.tesorero_id, "TESORERO")
        response = await ac.post(
            "/api/finanzas/cierre-mensual",
            headers=HEADERS,
            cookies=cookies,
            json={"periodo": "2026-1"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_finanzas_rbac_y_bloqueo_fantasma() -> None:
    async with _entorno_finanzas() as (factory, ctx, ac):
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
        assert (await ac.get("/api/finanzas/resumen", cookies=cookies_ghost)).status_code == 403
        assert (await ac.get("/api/finanzas/tasa", cookies=cookies_ghost)).status_code == 403

        cookies_prop = _cookies_usuario("prop@condo.test", ctx.propietario_id, "PROPIETARIO")
        assert (
            await ac.post(
                "/api/finanzas/tasa",
                headers=HEADERS,
                cookies=cookies_prop,
                json={"tasa_usd_ves": "36.5000"},
            )
        ).status_code == 403
        assert (
            await ac.post(
                "/api/finanzas/egresos",
                json={"periodo": "2026-10", "categoria": "A", "descripcion": "X", "monto": "10.00", "moneda": "USD"},
                headers=HEADERS,
                cookies=cookies_prop,
            )
        ).status_code == 403
        assert (
            await ac.post(
                "/api/finanzas/cierre-mensual",
                headers=HEADERS,
                cookies=cookies_prop,
                json={"periodo": "2026-10"},
            )
        ).status_code == 403
