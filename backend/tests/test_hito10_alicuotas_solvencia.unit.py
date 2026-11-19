"""Pruebas unitarias Nivel 11X para el Hito 10: Alícuotas, Cuota Fija, Facturación LPH, Fondos y Solvencia Digital."""

from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.database import get_db
from src.dependencies import get_current_user
from src.facturacion_lph import (
    _anexar_cuota_extraordinaria,
    _cargos_cuota_fija,
    _cargos_variables,
    _crear_recibo_e_items_unidad,
    calcular_cargos_modalidad,
    cargar_contexto_facturacion,
    persistir_lote_facturacion,
)
from src.finanzas import ErrorFinanciero
from src.main import app
from src.models import (
    AuditoriaRecibo,
    Egreso,
    Estructura,
    FondoCondominio,
    PagoReportado,
    Recibo,
    ReciboItem,
    ReporteMensual,
    Unidad,
    Usuario,
)
from src.redis_client import get_redis_client
from src.schemas import FacturarPeriodoRequest
from tests._sqlite_helpers import SeededCondoContext, create_sqlite_fk_factory, seed_condo_base

HEADERS = {"Idempotency-Key": "018f4a12-1010-7000-8000-000000001010"}


async def _preparar_entorno() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession], SeededCondoContext]:
    engine, factory = await create_sqlite_fk_factory()
    ctx = await seed_condo_base(factory)
    return engine, factory, ctx


async def _cargar_usuario(factory: async_sessionmaker[AsyncSession], usuario_id: int) -> Usuario:
    async with factory() as session:
        usuario = await session.get(Usuario, usuario_id)
        assert usuario is not None
        return usuario


def _configurar_overrides(
    factory: async_sessionmaker[AsyncSession],
    usuario: Usuario,
    *,
    redis_new: bool = True,
) -> AsyncMock:
    mock_redis = AsyncMock()
    mock_redis.set.return_value = redis_new

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_redis_client] = lambda: mock_redis
    app.dependency_overrides[get_current_user] = lambda: usuario
    return mock_redis


# ==============================================================================
# 1. ANTI-FRAUDE DE REFERENCIAS BANCARIAS Y SOBREPAGOS EN PAGOS
# ==============================================================================


async def test_reportar_pago_referencia_bancaria_duplicada_devuelve_409() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            recibo = Recibo(
                condominio_id=1,
                unidad_id=ctx.unidad_a_id,
                periodo="2026-10",
                monto_usd=Decimal("100.00"),
                monto_pagado_usd=Decimal("0.00"),
                estado="PENDIENTE",
                bloqueado=False,
            )
            seed_db.add(recibo)
            await seed_db.flush()
            seed_db.add(
                PagoReportado(
                    condominio_id=1,
                    recibo_id=recibo.id,
                    usuario_id=ctx.propietario_id,
                    monto=Decimal("50.00"),
                    moneda="USD",
                    monto_usd=Decimal("50.00"),
                    tasa_cambio=Decimal("45.5000"),
                    metodo_pago="ZELLE",
                    numero_referencia="REF-DUP-001",
                    estado="APROBADO",
                )
            )
            await seed_db.commit()
            recibo_id = recibo.id

        propietario = await _cargar_usuario(factory, ctx.propietario_id)
        _configurar_overrides(factory, propietario)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            res = await client.post(
                "/api/pagos/reportar",
                json={
                    "recibo_id": recibo_id,
                    "monto": "50.00",
                    "moneda": "USD",
                    "metodo_pago": "ZELLE",
                    "numero_referencia": "REF-DUP-001",
                },
                headers=HEADERS,
            )
            assert res.status_code == 409
            assert "referencia bancaria ya fue registrado" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_reportar_pago_referencia_bancaria_unica_exito() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            recibo = Recibo(
                condominio_id=1,
                unidad_id=ctx.unidad_a_id,
                periodo="2026-10",
                monto_usd=Decimal("100.00"),
                monto_pagado_usd=Decimal("0.00"),
                estado="PENDIENTE",
                bloqueado=False,
            )
            seed_db.add(recibo)
            await seed_db.commit()
            recibo_id = recibo.id

        propietario = await _cargar_usuario(factory, ctx.propietario_id)
        _configurar_overrides(factory, propietario)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            res = await client.post(
                "/api/pagos/reportar",
                json={
                    "recibo_id": recibo_id,
                    "monto": "100.00",
                    "moneda": "USD",
                    "metodo_pago": "PAGO_MOVIL",
                    "numero_referencia": "REF-UNICA-999",
                },
                headers=HEADERS,
            )
            assert res.status_code == 201

        async with factory() as check_db:
            pago_bd = await check_db.get(PagoReportado, res.json()["id"])
            assert pago_bd is not None
            assert pago_bd.numero_referencia == "REF-UNICA-999"
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_aprobar_pago_con_sobrepago_acredita_saldo_a_favor_unidad() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            unidad_a = await seed_db.get(Unidad, ctx.unidad_a_id)
            assert unidad_a is not None
            unidad_a.credito_disponible_usd = Decimal("10.00")

            recibo = Recibo(
                condominio_id=1,
                unidad_id=ctx.unidad_a_id,
                periodo="2026-10",
                monto_usd=Decimal("100.00"),
                monto_pagado_usd=Decimal("0.00"),
                estado="PENDIENTE",
                bloqueado=False,
            )
            seed_db.add(recibo)
            await seed_db.flush()
            pago = PagoReportado(
                condominio_id=1,
                recibo_id=recibo.id,
                usuario_id=ctx.propietario_id,
                monto=Decimal("125.00"),
                moneda="USD",
                monto_usd=Decimal("125.00"),
                tasa_cambio=Decimal("45.5000"),
                metodo_pago="ZELLE",
                numero_referencia="REF-OVER-1",
                estado="EN_REVISION",
            )
            seed_db.add(pago)
            await seed_db.commit()
            recibo_id = recibo.id
            pago_id = pago.id

        tesorero = await _cargar_usuario(factory, ctx.tesorero_id)
        _configurar_overrides(factory, tesorero)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            res = await client.put(f"/api/pagos/{pago_id}/aprobar", headers=HEADERS)
            assert res.status_code == 200

        async with factory() as check_db:
            recibo_bd = await check_db.get(Recibo, recibo_id)
            unidad_bd = await check_db.get(Unidad, ctx.unidad_a_id)
            assert recibo_bd is not None and unidad_bd is not None
            assert recibo_bd.estado == "PAGADO"
            assert recibo_bd.monto_pagado_usd == Decimal("100.00")
            assert unidad_bd.credito_disponible_usd == Decimal("35.00")

            res_audit = await check_db.execute(select(AuditoriaRecibo).where(AuditoriaRecibo.recibo_id == recibo_id))
            audit = res_audit.scalars().first()
            assert audit is not None
            assert "Sobrepago acreditado" in audit.motivo
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


# ==============================================================================
# 2. ACTUALIZACIÓN DE ALÍCUOTA Y CUOTA FIJA EN UNIDAD
# ==============================================================================


async def test_actualizar_alicuota_unidad_exito_y_errores() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        tesorero = await _cargar_usuario(factory, ctx.tesorero_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            _configurar_overrides(factory, tesorero)
            res = await client.put(
                f"/api/estructura/unidades/{ctx.unidad_a_id}/alicuota",
                json={"alicuota": "33.3333", "cuota_fija_usd": "25.00"},
                headers=HEADERS,
            )
            assert res.status_code == 200
            body = res.json()
            assert Decimal(body["alicuota"]) == Decimal("33.3333")
            assert Decimal(body["cuota_fija_usd"]) == Decimal("25.00")

            # 404 Unidad no encontrada
            res_404 = await client.put(
                "/api/estructura/unidades/999/alicuota",
                json={"alicuota": "10.0000"},
                headers=HEADERS,
            )
            assert res_404.status_code == 404

            # 409 Idempotencia duplicada
            _configurar_overrides(factory, tesorero, redis_new=False)
            res_409 = await client.put(
                f"/api/estructura/unidades/{ctx.unidad_a_id}/alicuota",
                json={"alicuota": "10.0000"},
                headers=HEADERS,
            )
            assert res_409.status_code == 409
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


# ==============================================================================
# 3. FONDOS PATRIMONIALES DEL CONDOMINIO
# ==============================================================================


async def test_crear_y_listar_fondos_condominio() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        tesorero = await _cargar_usuario(factory, ctx.tesorero_id)
        propietario = await _cargar_usuario(factory, ctx.propietario_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            _configurar_overrides(factory, tesorero)
            res = await client.post(
                "/api/finanzas/fondos",
                json={"nombre": "Fondo de Reserva Legal", "tipo": "RESERVA_LEGAL", "porcentaje_recargo": "10.00"},
                headers=HEADERS,
            )
            assert res.status_code == 201
            assert res.json()["nombre"] == "Fondo de Reserva Legal"

            # 409 Nombre duplicado
            res_dup = await client.post(
                "/api/finanzas/fondos",
                json={"nombre": "Fondo de Reserva Legal"},
                headers=HEADERS,
            )
            assert res_dup.status_code == 409

            # 409 Idempotencia duplicada
            _configurar_overrides(factory, tesorero, redis_new=False)
            res_idemp = await client.post(
                "/api/finanzas/fondos",
                json={"nombre": "Caja Chica", "tipo": "CAJA_CHICA"},
                headers=HEADERS,
            )
            assert res_idemp.status_code == 409

            # GET /api/finanzas/fondos
            _configurar_overrides(factory, propietario)
            res_list = await client.get("/api/finanzas/fondos")
            assert res_list.status_code == 200
            assert len(res_list.json()) == 1
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


# ==============================================================================
# 4. FACTURACIÓN TRIMODAL (ALICUOTA, CUOTA_FIJA, PARTES_IGUALES) Y DESGLOSE
# ==============================================================================


async def test_facturar_periodo_modalidad_alicuota_con_credito_y_fondo() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            u_a = await seed_db.get(Unidad, ctx.unidad_a_id)
            u_b = await seed_db.get(Unidad, ctx.unidad_b_id)
            assert u_a is not None and u_b is not None
            u_a.alicuota = Decimal("33.3333")
            u_a.credito_disponible_usd = Decimal("50.00")
            u_b.alicuota = Decimal("33.3333")
            u_b.credito_disponible_usd = Decimal("10.00")
            u_c = Unidad(
                condominio_id=1,
                identificador="1-C",
                estructura_id=ctx.estructura_id,
                alicuota=Decimal("33.3334"),
                credito_disponible_usd=Decimal("0.00"),
            )
            egreso = Egreso(
                condominio_id=1,
                periodo="2026-10",
                categoria="MANTENIMIENTO",
                descripcion="Bomba de agua",
                monto=Decimal("100.00"),
                moneda="USD",
                monto_usd=Decimal("100.00"),
                tasa_cambio=Decimal("45.5000"),
                es_gasto_comun=True,
            )
            fondo = FondoCondominio(
                condominio_id=1,
                nombre="Fondo de Reserva Legal",
                tipo="RESERVA_LEGAL",
                porcentaje_recargo=Decimal("10.00"),
                saldo_actual_usd=Decimal("200.00"),
                es_activo=True,
            )
            seed_db.add_all([u_c, egreso, fondo])
            await seed_db.commit()
            fondo_id = fondo.id

        tesorero = await _cargar_usuario(factory, ctx.tesorero_id)
        _configurar_overrides(factory, tesorero)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            res = await client.post(
                "/api/finanzas/facturar-periodo",
                json={
                    "periodo": "2026-10",
                    "modalidad": "ALICUOTA",
                    "incluir_fondo_reserva": True,
                    "cuota_extraordinaria_total_usd": "30.00",
                    "descripcion_cuota_extraordinaria": "Pintura fachada",
                },
                headers=HEADERS,
            )
            assert res.status_code == 201
            body = res.json()
            assert body["recibos_emitidos"] == 3
            assert Decimal(body["total_egresos_comunes_usd"]) == Decimal("100.00")
            assert Decimal(body["recargo_fondo_reserva_usd"]) == Decimal("10.00")
            assert Decimal(body["cuota_extraordinaria_total_usd"]) == Decimal("30.00")
            assert Decimal(body["total_facturado_bruto_usd"]) == Decimal("140.00")

        async with factory() as check_db:
            fondo_bd = await check_db.get(FondoCondominio, fondo_id)
            u_a_bd = await check_db.get(Unidad, ctx.unidad_a_id)
            u_b_bd = await check_db.get(Unidad, ctx.unidad_b_id)
            assert fondo_bd is not None and u_a_bd is not None and u_b_bd is not None
            assert fondo_bd.saldo_actual_usd == Decimal("210.00")
            # Unidad A tenía $50 de crédito y su cargo bruto era ~$46.67 -> queda cubierta al 100%
            assert u_a_bd.credito_disponible_usd > Decimal("0.00")
            assert u_b_bd.credito_disponible_usd == Decimal("0.00")
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_facturar_periodo_modalidad_cuota_fija_y_partes_iguales() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            u_a = await seed_db.get(Unidad, ctx.unidad_a_id)
            assert u_a is not None
            u_a.cuota_fija_usd = Decimal("35.00")

            egreso_nov = Egreso(
                condominio_id=1,
                periodo="2026-11",
                categoria="VIGILANCIA",
                descripcion="Servicio garita",
                monto=Decimal("40.00"),
                moneda="USD",
                monto_usd=Decimal("40.00"),
                tasa_cambio=Decimal("45.5000"),
                es_gasto_comun=True,
            )
            egreso_dic = Egreso(
                condominio_id=1,
                periodo="2026-12",
                categoria="VIGILANCIA",
                descripcion="Servicio garita",
                monto=Decimal("40.00"),
                moneda="USD",
                monto_usd=Decimal("40.00"),
                tasa_cambio=Decimal("45.5000"),
                es_gasto_comun=True,
            )
            fondo = FondoCondominio(
                condominio_id=1,
                nombre="Fondo de Reserva Legal",
                tipo="RESERVA_LEGAL",
                porcentaje_recargo=Decimal("10.00"),
                saldo_actual_usd=Decimal("100.00"),
                es_activo=True,
            )
            seed_db.add_all([egreso_nov, egreso_dic, fondo])
            await seed_db.commit()
            fondo_id = fondo.id

        tesorero = await _cargar_usuario(factory, ctx.tesorero_id)
        _configurar_overrides(factory, tesorero)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            res_fija = await client.post(
                "/api/finanzas/facturar-periodo",
                json={
                    "periodo": "2026-11",
                    "modalidad": "CUOTA_FIJA",
                    "monto_cuota_fija_usd": "25.00",
                },
                headers=HEADERS,
            )
            assert res_fija.status_code == 201
            body_fija = res_fija.json()
            # 35.00 + 25.00 = 60.00 facturado - 40.00 egresos = +20.00 superávit al fondo
            assert Decimal(body_fija["total_facturado_bruto_usd"]) == Decimal("60.00")
            assert Decimal(body_fija["superavit_conciliado_fondo_usd"]) == Decimal("20.00")

            async with factory() as check_db:
                fondo_bd = await check_db.get(FondoCondominio, fondo_id)
                assert fondo_bd is not None
                assert fondo_bd.saldo_actual_usd == Decimal("120.00")

            # Modalidad PARTES_IGUALES
            res_iguales = await client.post(
                "/api/finanzas/facturar-periodo",
                json={
                    "periodo": "2026-12",
                    "modalidad": "PARTES_IGUALES",
                    "incluir_fondo_reserva": False,
                },
                headers=HEADERS,
            )
            assert res_iguales.status_code == 201
            assert Decimal(res_iguales.json()["total_facturado_bruto_usd"]) == Decimal("40.00")
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_facturar_periodo_errores_y_bloqueos(monkeypatch: pytest.MonkeyPatch) -> None:
    engine, factory, ctx = await _preparar_entorno()
    engine_vacio, factory_vacio = await create_sqlite_fk_factory()
    try:
        async with factory() as seed_db:
            seed_db.add(ReporteMensual(condominio_id=1, periodo="2026-10", estado="CERRADO"))
            recibo_ya = Recibo(
                condominio_id=1,
                unidad_id=ctx.unidad_a_id,
                periodo="2026-11",
                monto_usd=Decimal("10.00"),
                monto_pagado_usd=Decimal("0.00"),
                estado="PENDIENTE",
            )
            seed_db.add(recibo_ya)
            await seed_db.flush()
            seed_db.add(
                ReciboItem(
                    condominio_id=1,
                    recibo_id=recibo_ya.id,
                    tipo_item="GASTO_COMUN",
                    descripcion="Gasto común",
                    monto_usd=Decimal("10.00"),
                )
            )
            await seed_db.commit()

        async with factory_vacio() as seed_vacio:
            tesorero_vacio = Usuario(
                condominio_id=1,
                nombre="Tesorero Sin Unidades",
                cedula="V-90000010",
                correo="tes_vacio@condo.test",
                telefono="+584140000110",
                password_hash="hash_no_usado",
                es_activo=True,
                rol="TESORERO",
            )
            seed_vacio.add(tesorero_vacio)
            await seed_vacio.commit()
            await seed_vacio.refresh(tesorero_vacio)

        tesorero = await _cargar_usuario(factory, ctx.tesorero_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Idempotencia duplicada -> 409
            _configurar_overrides(factory, tesorero, redis_new=False)
            assert (
                await client.post("/api/finanzas/facturar-periodo", json={"periodo": "2026-10"}, headers=HEADERS)
            ).status_code == 409

            # 2. Periodo cerrado por Candado Contable -> 409
            _configurar_overrides(factory, tesorero)
            assert (
                await client.post("/api/finanzas/facturar-periodo", json={"periodo": "2026-10"}, headers=HEADERS)
            ).status_code == 409

            # 3. Periodo ya facturado -> 409
            assert (
                await client.post("/api/finanzas/facturar-periodo", json={"periodo": "2026-11"}, headers=HEADERS)
            ).status_code == 409

            # 4. Sin unidades registradas -> 400
            _configurar_overrides(factory_vacio, tesorero_vacio)
            assert (
                await client.post("/api/finanzas/facturar-periodo", json={"periodo": "2026-12"}, headers=HEADERS)
            ).status_code == 400

            # 5. CUOTA_FIJA sin monto_cuota_fija_usd y unidad sin cuota_fija_usd -> 400
            _configurar_overrides(factory, tesorero)
            assert (
                await client.post(
                    "/api/finanzas/facturar-periodo",
                    json={"periodo": "2026-12", "modalidad": "CUOTA_FIJA"},
                    headers=HEADERS,
                )
            ).status_code == 400

            # 6. Modalidad ALICUOTA con suma de alícuotas != 100.0000% -> 400
            async with factory() as upd_db:
                u_a = await upd_db.get(Unidad, ctx.unidad_a_id)
                u_b = await upd_db.get(Unidad, ctx.unidad_b_id)
                assert u_a is not None and u_b is not None
                u_a.alicuota = Decimal("50.0000")
                u_b.alicuota = Decimal("30.0000")
                await upd_db.commit()

            res_bad_alic = await client.post(
                "/api/finanzas/facturar-periodo",
                json={"periodo": "2026-12", "modalidad": "ALICUOTA", "incluir_fondo_reserva": False},
                headers=HEADERS,
            )
            assert res_bad_alic.status_code == 400
            assert "100.0000%" in res_bad_alic.json()["detail"]

            # 7. Colisión concurrente IntegrityError sobre uq_recibo_unidad_periodo -> 409 Conflict
            async with factory() as fix_db:
                u_a = await fix_db.get(Unidad, ctx.unidad_a_id)
                u_b = await fix_db.get(Unidad, ctx.unidad_b_id)
                assert u_a is not None and u_b is not None
                u_a.alicuota = Decimal("60.0000")
                u_b.alicuota = Decimal("40.0000")
                await fix_db.commit()

            async with factory() as fault_session:
                monkeypatch.setattr(
                    fault_session,
                    "commit",
                    AsyncMock(side_effect=IntegrityError("dup", {}, Exception("uq_recibo_unidad_periodo"))),
                )
                app.dependency_overrides[get_db] = lambda: fault_session
                res_ie = await client.post(
                    "/api/finanzas/facturar-periodo",
                    json={"periodo": "2026-12", "modalidad": "ALICUOTA", "incluir_fondo_reserva": False},
                    headers=HEADERS,
                )
                assert res_ie.status_code == 409
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
        await engine_vacio.dispose()


async def test_facturar_periodo_cuota_extraordinaria_prorrateada_por_alicuota() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            u_a = await seed_db.get(Unidad, ctx.unidad_a_id)
            u_b = await seed_db.get(Unidad, ctx.unidad_b_id)
            assert u_a is not None and u_b is not None
            u_a.alicuota = Decimal("50.0000")
            u_b.alicuota = Decimal("30.0000")
            seed_db.add(
                Unidad(
                    condominio_id=1,
                    identificador="1-C",
                    estructura_id=ctx.estructura_id,
                    alicuota=Decimal("20.0000"),
                    credito_disponible_usd=Decimal("0.00"),
                )
            )
            await seed_db.commit()

        tesorero = await _cargar_usuario(factory, ctx.tesorero_id)
        _configurar_overrides(factory, tesorero)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            res = await client.post(
                "/api/finanzas/facturar-periodo",
                json={
                    "periodo": "2027-01",
                    "modalidad": "ALICUOTA",
                    "incluir_fondo_reserva": False,
                    "cuota_extraordinaria_total_usd": "100.00",
                    "descripcion_cuota_extraordinaria": "Impermeabilización techo",
                },
                headers=HEADERS,
            )
            assert res.status_code == 201

        async with factory() as check_db:
            res_items = await check_db.execute(select(ReciboItem).where(ReciboItem.tipo_item == "CUOTA_EXTRAORDINARIA"))
            montos_extra = sorted(item.monto_usd for item in res_items.scalars().all())
            assert montos_extra == [Decimal("20.00"), Decimal("30.00"), Decimal("50.00")]
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_obtener_desglose_recibo_exito_y_permisos() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            recibo = Recibo(
                condominio_id=1,
                unidad_id=ctx.unidad_a_id,
                periodo="2026-10",
                monto_usd=Decimal("35.00"),
                monto_pagado_usd=Decimal("0.00"),
                estado="PENDIENTE",
                bloqueado=False,
            )
            seed_db.add(recibo)
            await seed_db.flush()
            seed_db.add_all(
                [
                    ReciboItem(
                        condominio_id=1,
                        recibo_id=recibo.id,
                        tipo_item="GASTO_COMUN",
                        descripcion="Gasto común",
                        monto_usd=Decimal("45.00"),
                    ),
                    ReciboItem(
                        condominio_id=1,
                        recibo_id=recibo.id,
                        tipo_item="ABONO_CREDITO_PREVIO",
                        descripcion="Abono previo",
                        monto_usd=Decimal("-10.00"),
                    ),
                ]
            )
            await seed_db.commit()
            recibo_id = recibo.id

        tesorero = await _cargar_usuario(factory, ctx.tesorero_id)
        inquilino = await _cargar_usuario(factory, ctx.inquilino_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            _configurar_overrides(factory, tesorero)
            res = await client.get(f"/api/finanzas/recibos/{recibo_id}/desglose")
            assert res.status_code == 200
            body = res.json()
            assert body["identificador_unidad"] == "1-A"
            assert Decimal(body["credito_descontado_usd"]) == Decimal("10.00")
            assert len(body["items"]) == 2

            # Ocupante de otra unidad recibe 403
            _configurar_overrides(factory, inquilino)
            assert (await client.get(f"/api/finanzas/recibos/{recibo_id}/desglose")).status_code == 403

            # Recibo inexistente devuelve 404
            _configurar_overrides(factory, tesorero)
            assert (await client.get("/api/finanzas/recibos/999/desglose")).status_code == 404
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


# ==============================================================================
# 5. CERTIFICADO DIGITAL DE SOLVENCIA (HMAC-SHA256)
# ==============================================================================


async def test_emitir_y_verificar_certificado_solvencia() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        propietario = await _cargar_usuario(factory, ctx.propietario_id)
        tesorero = await _cargar_usuario(factory, ctx.tesorero_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            _configurar_overrides(factory, propietario)
            res = await client.post(f"/api/finanzas/solvencia/{ctx.unidad_a_id}", headers=HEADERS)
            assert res.status_code == 201
            cert_data = res.json()
            assert cert_data["identificador_unidad"] == "1-A"
            assert Decimal(cert_data["deuda_verificada_usd"]) == Decimal("0.00")
            assert cert_data["qr_token"].endswith(cert_data["firma_hmac"])

            # Verificar el certificado emitido contra SQLite real
            _configurar_overrides(factory, tesorero)
            res_verif = await client.get(
                f"/api/finanzas/solvencia/verificar/{cert_data['folio']}?sig={cert_data['firma_hmac']}"
            )
            assert res_verif.status_code == 200
            assert res_verif.json()["valido"] is True

            # Firma adulterada devuelve 400
            res_bad = await client.get(f"/api/finanzas/solvencia/verificar/{cert_data['folio']}?sig=firma_falsa")
            assert res_bad.status_code == 400

            # Folio no encontrado devuelve 404
            assert (await client.get("/api/finanzas/solvencia/verificar/SOLV-NO-EXISTE?sig=abc")).status_code == 404
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_emitir_solvencia_con_deuda_pendiente_devuelve_409() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            seed_db.add(
                Recibo(
                    condominio_id=1,
                    unidad_id=ctx.unidad_a_id,
                    periodo="2026-10",
                    monto_usd=Decimal("60.00"),
                    monto_pagado_usd=Decimal("0.00"),
                    estado="PENDIENTE",
                    bloqueado=False,
                )
            )
            await seed_db.commit()

        tesorero = await _cargar_usuario(factory, ctx.tesorero_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            _configurar_overrides(factory, tesorero)
            res = await client.post(f"/api/finanzas/solvencia/{ctx.unidad_a_id}", headers=HEADERS)
            assert res.status_code == 409
            assert "60.00 USD" in res.json()["detail"]

            # Unidad no encontrada -> 404
            assert (await client.post("/api/finanzas/solvencia/999", headers=HEADERS)).status_code == 404

            # Idempotencia duplicada -> 409
            _configurar_overrides(factory, tesorero, redis_new=False)
            assert (await client.post(f"/api/finanzas/solvencia/{ctx.unidad_a_id}", headers=HEADERS)).status_code == 409
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


def test_facturacion_lph_nucleo_helpers_cuota_fija_variables_y_recibos() -> None:
    """Ataque unitario directo a helpers de facturacion_lph.py para cobertura de mutantes."""
    u1 = Unidad(
        id=1,
        identificador="A-01",
        estructura_id=1,
        alicuota=Decimal("60.0000"),
        cuota_fija_usd=Decimal("40.00"),
        credito_disponible_usd=Decimal("50.00"),
    )
    u2 = Unidad(
        id=2,
        identificador="A-02",
        estructura_id=1,
        alicuota=Decimal("40.0000"),
        cuota_fija_usd=None,
        credito_disponible_usd=Decimal("5.00"),
    )

    req_fija = FacturarPeriodoRequest(periodo="2026-10", modalidad="CUOTA_FIJA", monto_cuota_fija_usd=Decimal("20.00"))
    items_fija, superavit = _cargos_cuota_fija(req_fija, [u1, u2], Decimal("50.00"))
    assert items_fija[1][0][0] == "CUOTA_FIJA"
    assert items_fija[1][0][1] == "Cuota fija mensual (2026-10)"
    assert items_fija[1][0][2] == Decimal("40.00")
    assert items_fija[2][0][2] == Decimal("20.00")
    assert superavit == Decimal("10.00")

    # Cuota fija explícita en 0.00 no hace fallback falsy al monto global -> exige cuota > 0
    u_cero = Unidad(
        id=9,
        identificador="A-09",
        estructura_id=1,
        alicuota=Decimal("0.0000"),
        cuota_fija_usd=Decimal("0"),
    )
    with pytest.raises(ErrorFinanciero, match="CUOTA_FIJA"):
        _cargos_cuota_fija(req_fija, [u_cero], Decimal("10.00"))

    # Si total fijo < total egresos, retorna diferencia negativa sin truncar
    _, superavit_cero = _cargos_cuota_fija(req_fija, [u1, u2], Decimal("80.00"))
    assert superavit_cero == Decimal("-20.00")

    # Error si una unidad no tiene cuota individual (>0) ni global
    req_fija_sin_monto = FacturarPeriodoRequest(periodo="2026-10", modalidad="CUOTA_FIJA", monto_cuota_fija_usd=None)
    with pytest.raises(ErrorFinanciero, match="CUOTA_FIJA"):
        _cargos_cuota_fija(req_fija_sin_monto, [u1, u2], Decimal("10.00"))

    # Cargos variables: PARTES_IGUALES sin fondo de reserva (> 0)
    req_pi = FacturarPeriodoRequest(periodo="2026-10", modalidad="PARTES_IGUALES", incluir_fondo_reserva=False)
    items_pi = _cargos_variables(req_pi, [u1, u2], Decimal("100.00"), Decimal("0.00"))
    assert len(items_pi[1]) == 1
    assert items_pi[1][0][0] == "GASTO_COMUN"
    assert items_pi[1][0][1] == "Cuota parte de gastos comunes (2026-10)"
    assert items_pi[1][0][2] == Decimal("50.00")
    assert items_pi[2][0][2] == Decimal("50.00")

    # Cargos variables: ALICUOTA con reserva > 0 emite GASTO_COMUN y FONDO_RESERVA
    req_al = FacturarPeriodoRequest(periodo="2026-10", modalidad="ALICUOTA", incluir_fondo_reserva=True)
    items_al = _cargos_variables(req_al, [u1, u2], Decimal("100.00"), Decimal("10.00"))
    assert [t[0] for t in items_al[1]] == ["GASTO_COMUN", "FONDO_RESERVA"]
    assert items_al[1][0][1] == "Cuota parte de gastos comunes (2026-10)"
    assert items_al[1][1][1] == "Aporte al Fondo de Reserva Legal"
    assert items_al[1][0][2] == Decimal("60.00")
    assert items_al[1][1][2] == Decimal("6.00")
    assert items_al[2][0][2] == Decimal("40.00")
    assert items_al[2][1][2] == Decimal("4.00")

    # Cuota extraordinaria <= 0 no agrega ítems; > 0 prorratea por alícuota y agrega fallback desc
    _anexar_cuota_extraordinaria(req_al, [u1, u2], items_al)
    assert len(items_al[1]) == 2

    req_ext_pi = FacturarPeriodoRequest(
        periodo="2026-10",
        modalidad="PARTES_IGUALES",
        cuota_extraordinaria_total_usd=Decimal("30.00"),
    )
    items_ext: dict[int, list[tuple[str, str, Decimal]]] = {1: [], 2: []}
    _anexar_cuota_extraordinaria(req_ext_pi, [u1, u2], items_ext)
    assert items_ext[1][0][0] == "CUOTA_EXTRAORDINARIA"
    assert items_ext[1][0][1] == "Cuota extraordinaria aprobada"
    assert items_ext[1][0][2] == Decimal("15.00")
    assert items_ext[2][0][2] == Decimal("15.00")

    # Cuota extraordinaria en ALICUOTA con alícuotas que no suman 100% -> 400
    req_ext_al = FacturarPeriodoRequest(
        periodo="2026-10",
        modalidad="ALICUOTA",
        cuota_extraordinaria_total_usd=Decimal("30.00"),
    )
    u_bad = Unidad(
        id=3,
        identificador="A-03",
        estructura_id=1,
        alicuota=Decimal("10.0000"),
        credito_disponible_usd=Decimal("0.00"),
    )
    with pytest.raises(ErrorFinanciero, match="100.0000%"):
        _anexar_cuota_extraordinaria(req_ext_al, [u1, u_bad], {1: [], 3: []})

    # Pruebas directas sobre calcular_cargos_modalidad (CUOTA_FIJA y ALICUOTA con extraordinaria)
    req_mod_fija = FacturarPeriodoRequest(
        periodo="2026-10",
        modalidad="CUOTA_FIJA",
        monto_cuota_fija_usd=Decimal("20.00"),
        cuota_extraordinaria_total_usd=Decimal("20.00"),
    )
    items_mod_fija, sup_mod = calcular_cargos_modalidad(req_mod_fija, [u1, u2], Decimal("50.00"), Decimal("0.00"))
    assert sup_mod == Decimal("10.00")
    assert [t[0] for t in items_mod_fija[1]] == ["CUOTA_FIJA", "CUOTA_EXTRAORDINARIA"]

    req_mod_al = FacturarPeriodoRequest(
        periodo="2026-10",
        modalidad="ALICUOTA",
        incluir_fondo_reserva=True,
        cuota_extraordinaria_total_usd=Decimal("20.00"),
    )
    items_mod_al, sup_mod_al = calcular_cargos_modalidad(req_mod_al, [u1, u2], Decimal("100.00"), Decimal("10.00"))
    assert sup_mod_al == Decimal("0.00")
    assert [t[0] for t in items_mod_al[1]] == ["GASTO_COMUN", "FONDO_RESERVA", "CUOTA_EXTRAORDINARIA"]
    assert items_mod_al[1][2][2] == Decimal("12.00")
    assert items_mod_al[2][2][2] == Decimal("8.00")

    # _crear_recibo_e_items_unidad: crédito cubre 100% -> Recibo.monto_usd == 0.00 cuadra con sum(items) == 0.00
    recibo_pagado, r_items, bruto_1, cred_1 = _crear_recibo_e_items_unidad(
        u1,
        "2026-10",
        [("CUOTA_FIJA", "Cuota", Decimal("40.00"))],
    )
    assert bruto_1 == Decimal("40.00")
    assert cred_1 == Decimal("40.00")
    assert recibo_pagado.monto_usd == Decimal("0.00")
    assert recibo_pagado.monto_pagado_usd == Decimal("0.00")
    assert recibo_pagado.estado == "PAGADO"
    assert recibo_pagado.bloqueado is False
    assert sum(it.monto_usd for it in r_items) == Decimal("0.00")
    assert u1.credito_disponible_usd == Decimal("10.00")
    assert r_items[-1].tipo_item == "ABONO_CREDITO_PREVIO"
    assert r_items[-1].descripcion == "Abono automático de saldo a favor disponible"
    assert r_items[-1].monto_usd == Decimal("-40.00")

    # Cargo bruto cero produce recibo en 0.00 marcado como PAGADO sin abono
    recibo_cero, items_cero, bruto_cero, cred_cero = _crear_recibo_e_items_unidad(u1, "2026-10", [])
    assert bruto_cero == Decimal("0.00")
    assert cred_cero == Decimal("0.00")
    assert recibo_cero.monto_usd == Decimal("0.00")
    assert recibo_cero.monto_pagado_usd == Decimal("0.00")
    assert recibo_cero.estado == "PAGADO"
    assert items_cero == []

    # Crédito parcial deja recibo PENDIENTE y consume todo el crédito
    recibo_pend, r_items2, bruto_2, cred_2 = _crear_recibo_e_items_unidad(
        u2,
        "2026-10",
        [("GASTO_COMUN", "Gasto", Decimal("25.00"))],
    )
    assert bruto_2 == Decimal("25.00")
    assert cred_2 == Decimal("5.00")
    assert recibo_pend.monto_usd == Decimal("20.00")
    assert recibo_pend.estado == "PENDIENTE"
    assert u2.credito_disponible_usd == Decimal("0.00")
    assert len(r_items2) == 2


async def test_cargar_contexto_facturacion_respaldo_diez_por_ciento() -> None:
    """Sin fondo RESERVA_LEGAL activo, incluir_fondo_reserva=True exige existencia del fondo (ErrorFinanciero)."""
    engine, factory = await create_sqlite_fk_factory()
    try:
        async with factory() as seed_db:
            torre = Estructura(condominio_id=1, nombre="Torre Única", tipo="TORRE")
            seed_db.add(torre)
            await seed_db.flush()
            u = Unidad(condominio_id=1, identificador="A-01", estructura_id=torre.id, alicuota=Decimal("100.0000"))
            egreso = Egreso(
                condominio_id=1,
                periodo="2026-10",
                categoria="MANT",
                descripcion="Bomba",
                monto=Decimal("200.00"),
                moneda="USD",
                monto_usd=Decimal("200.00"),
                tasa_cambio=Decimal("36.5000"),
                es_gasto_comun=True,
            )
            seed_db.add_all([u, egreso])
            await seed_db.commit()

        async with factory() as session:
            req_con_fondo = FacturarPeriodoRequest(periodo="2026-10", modalidad="ALICUOTA", incluir_fondo_reserva=True)
            with pytest.raises(ErrorFinanciero, match="Fondo de Reserva Legal"):
                await cargar_contexto_facturacion(session, req_con_fondo)

            req_sin_fondo = FacturarPeriodoRequest(periodo="2026-10", modalidad="ALICUOTA", incluir_fondo_reserva=False)
            unidades, total_eg, fondo, recargo = await cargar_contexto_facturacion(session, req_sin_fondo)
            assert len(unidades) == 1
            assert total_eg == Decimal("200.00")
            assert fondo is None
            assert recargo == Decimal("0.00")
    finally:
        await engine.dispose()


async def test_persistir_lote_facturacion_actualiza_fondos_y_recibos() -> None:
    """Verifica actualización de fondo según modalidad, flush, recibo_id en ítems y totales netos."""
    engine, factory = await create_sqlite_fk_factory()
    try:
        async with factory() as seed_db:
            torre = Estructura(condominio_id=1, nombre="Torre Única", tipo="TORRE")
            seed_db.add(torre)
            await seed_db.flush()
            u1 = Unidad(
                condominio_id=1,
                identificador="A-01",
                estructura_id=torre.id,
                alicuota=Decimal("100.0000"),
                credito_disponible_usd=Decimal("10.00"),
            )
            fondo_fija = FondoCondominio(
                condominio_id=1,
                nombre="Reserva",
                tipo="RESERVA_LEGAL",
                porcentaje_recargo=Decimal("10.00"),
                saldo_actual_usd=Decimal("100.00"),
                es_activo=True,
            )
            seed_db.add_all([u1, fondo_fija])
            await seed_db.commit()
            torre_id = torre.id
            u1_id = u1.id
            fondo_fija_id = fondo_fija.id

        async with factory() as session_fija:
            u1_db = await session_fija.get(Unidad, u1_id)
            fondo_fija_db = await session_fija.get(FondoCondominio, fondo_fija_id)
            assert u1_db is not None and fondo_fija_db is not None
            tot_bruto, tot_cred, tot_neto = await persistir_lote_facturacion(
                session_fija,
                [u1_db],
                "2026-10",
                "CUOTA_FIJA",
                {u1_db.id: [("CUOTA_FIJA", "Cuota fija mensual (2026-10)", Decimal("40.00"))]},
                fondo_fija_db,
                Decimal("5.00"),
                Decimal("12.00"),
            )
            assert (tot_bruto, tot_cred, tot_neto) == (Decimal("40.00"), Decimal("10.00"), Decimal("30.00"))

        async with factory() as check_db:
            fondo_chk = await check_db.get(FondoCondominio, fondo_fija_id)
            assert fondo_chk is not None
            assert fondo_chk.saldo_actual_usd == Decimal("112.00")
            res_rec = await check_db.execute(
                select(Recibo).where(Recibo.unidad_id == u1_id, Recibo.periodo == "2026-10")
            )
            rec_fija = res_rec.scalars().first()
            assert rec_fija is not None
            res_items = await check_db.execute(select(ReciboItem).where(ReciboItem.recibo_id == rec_fija.id))
            items_fija = list(res_items.scalars().all())
            assert len(items_fija) == 2
            assert all(it.recibo_id == rec_fija.id for it in items_fija)

        async with factory() as seed_al_db:
            u2 = Unidad(
                condominio_id=1,
                identificador="A-02",
                estructura_id=torre_id,
                alicuota=Decimal("100.0000"),
                credito_disponible_usd=Decimal("0.00"),
            )
            fondo_al = FondoCondominio(
                condominio_id=1,
                nombre="Reserva 2",
                tipo="RESERVA_LEGAL",
                porcentaje_recargo=Decimal("10.00"),
                saldo_actual_usd=Decimal("50.00"),
                es_activo=True,
            )
            seed_al_db.add_all([u2, fondo_al])
            await seed_al_db.commit()
            u2_id = u2.id
            fondo_al_id = fondo_al.id

        async with factory() as session_al:
            u2_db = await session_al.get(Unidad, u2_id)
            fondo_al_db = await session_al.get(FondoCondominio, fondo_al_id)
            assert u2_db is not None and fondo_al_db is not None
            b2, c2, n2 = await persistir_lote_facturacion(
                session_al,
                [u2_db],
                "2026-11",
                "ALICUOTA",
                {u2_db.id: [("GASTO_COMUN", "Cuota parte", Decimal("60.00"))]},
                fondo_al_db,
                Decimal("6.00"),
                Decimal("99.00"),
            )
            assert (b2, c2, n2) == (Decimal("60.00"), Decimal("0.00"), Decimal("60.00"))

        async with factory() as check_al_db:
            fondo_al_chk = await check_al_db.get(FondoCondominio, fondo_al_id)
            assert fondo_al_chk is not None
            assert fondo_al_chk.saldo_actual_usd == Decimal("56.00")
    finally:
        await engine.dispose()
