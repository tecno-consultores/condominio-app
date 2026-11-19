"""Pruebas unitarias Nivel 11X para el Hito 13: Reserva de Áreas Sociales e Inspección Post-Evento."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.database import get_db
from src.dependencies import get_current_user
from src.main import app
from src.models import AreaSocial, Recibo, ReciboItem, ReservaAreaSocial, TareaDiaria, Usuario
from src.redis_client import get_redis_client
from tests._sqlite_helpers import SeededCondoContext, create_sqlite_fk_factory, seed_condo_base

HEADERS = {"Idempotency-Key": "018f4a13-1313-7000-8000-000000001313"}


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
# 1. CONFIGURACIÓN Y LISTADO DE ÁREAS SOCIALES (/api/reservas/areas)
# ==============================================================================


async def test_crear_area_social_exitosa_y_duplicada() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        presidente = await _cargar_usuario(factory, ctx.presidente_id)
        tesorero = await _cargar_usuario(factory, ctx.tesorero_id)
        propietario = await _cargar_usuario(factory, ctx.propietario_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            _configurar_overrides(factory, presidente)
            resp = await client.post(
                "/api/reservas/areas",
                headers=HEADERS,
                json={
                    "nombre": "Salón de Fiestas Principal",
                    "aforo_maximo": 80,
                    "costo_uso_usd": "35.00",
                    "deposito_garantia_usd": "100.00",
                    "requiere_solvencia_estricta": True,
                },
            )
            assert resp.status_code == 201
            body = resp.json()
            assert body["nombre"] == "Salón de Fiestas Principal"
            assert body["aforo_maximo"] == 80
            assert Decimal(body["deposito_garantia_usd"]) == Decimal("100.00")

            # Nombre duplicado -> 409
            _configurar_overrides(factory, tesorero)
            resp_dup = await client.post(
                "/api/reservas/areas",
                headers=HEADERS,
                json={
                    "nombre": "Salón de Fiestas Principal",
                    "aforo_maximo": 50,
                },
            )
            assert resp_dup.status_code == 409

            # Idempotency-Key repetida -> 409
            _configurar_overrides(factory, presidente, redis_new=False)
            resp_idem = await client.post(
                "/api/reservas/areas",
                headers=HEADERS,
                json={"nombre": "Caney Parrillero", "aforo_maximo": 25},
            )
            assert resp_idem.status_code == 409

            # Rol no autorizado (PROPIETARIO) -> 403
            _configurar_overrides(factory, propietario)
            resp_rol = await client.post(
                "/api/reservas/areas",
                headers=HEADERS,
                json={"nombre": "Caney Parrillero", "aforo_maximo": 25},
            )
            assert resp_rol.status_code == 403
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_listar_areas_sociales_y_bloqueo_fantasma() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            area = AreaSocial(
                nombre="Parrillera Norte",
                aforo_maximo=20,
                costo_uso_usd=Decimal("15.00"),
                deposito_garantia_usd=Decimal("50.00"),
                requiere_solvencia_estricta=True,
                es_activa=True,
            )
            fantasma = Usuario(
                condominio_id=1,
                nombre="Vecino Fantasma",
                cedula="V-90000099",
                correo="fantasma@condo.test",
                telefono="+584140000199",
                password_hash="hash_no_usado",
                es_activo=False,
                rol="FANTASMA",
            )
            seed_db.add_all([area, fantasma])
            await seed_db.commit()
            await seed_db.refresh(fantasma)

        propietario = await _cargar_usuario(factory, ctx.propietario_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            _configurar_overrides(factory, propietario)
            resp = await client.get("/api/reservas/areas")
            assert resp.status_code == 200
            assert len(resp.json()) == 1
            assert resp.json()[0]["nombre"] == "Parrillera Norte"

            # Usuario Fantasma -> 403
            _configurar_overrides(factory, fantasma)
            resp_ghost = await client.get("/api/reservas/areas")
            assert resp_ghost.status_code == 403
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


# ==============================================================================
# 2. SOLICITUD DE RESERVA CON CANDADO DE SOLVENCIA ESTRICTA Y TAREA DIARIA
# ==============================================================================


async def test_solicitar_reserva_unidad_solvente_crea_tarea_inspeccion() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            area = AreaSocial(
                nombre="Salón de Usos Múltiples",
                aforo_maximo=60,
                costo_uso_usd=Decimal("25.00"),
                deposito_garantia_usd=Decimal("80.00"),
                requiere_solvencia_estricta=True,
                es_activa=True,
            )
            recibo_pagado = Recibo(
                condominio_id=1,
                periodo="2026-10",
                unidad_id=ctx.unidad_a_id,
                monto_usd=Decimal("45.00"),
                monto_pagado_usd=Decimal("45.00"),
                estado="PAGADO",
            )
            seed_db.add_all([area, recibo_pagado])
            await seed_db.commit()
            area_id = area.id

        propietario = await _cargar_usuario(factory, ctx.propietario_id)
        _configurar_overrides(factory, propietario)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.post(
                "/api/reservas/solicitar",
                headers=HEADERS,
                json={
                    "area_id": area_id,
                    "unidad_id": ctx.unidad_a_id,
                    "fecha_evento": "2026-12-15",
                    "motivo_evento": "Cumpleaños familiar infantil",
                },
            )
            assert resp.status_code == 201
            body = resp.json()
            assert body["estado"] == "CONFIRMADA"
            assert body["nombre_area"] == "Salón de Usos Múltiples"
            assert body["identificador_unidad"] == "1-A"
            assert body["tarea_inspeccion_id"] >= 1

        async with factory() as check_db:
            tarea = await check_db.get(TareaDiaria, body["tarea_inspeccion_id"])
            assert tarea is not None
            assert tarea.completada is False
            res_items = await check_db.execute(select(ReciboItem).where(ReciboItem.tipo_item == "USO_AREA_SOCIAL"))
            assert len(res_items.scalars().all()) == 1
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_solicitar_reserva_rechazada_por_morosidad_403() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            area = AreaSocial(
                nombre="Salón de Fiestas",
                aforo_maximo=60,
                costo_uso_usd=Decimal("25.00"),
                deposito_garantia_usd=Decimal("80.00"),
                requiere_solvencia_estricta=True,
                es_activa=True,
            )
            recibo_moroso = Recibo(
                condominio_id=1,
                periodo="2026-10",
                unidad_id=ctx.unidad_a_id,
                monto_usd=Decimal("50.00"),
                monto_pagado_usd=Decimal("10.00"),
                estado="PARCIAL",
            )
            seed_db.add_all([area, recibo_moroso])
            await seed_db.commit()
            area_id = area.id

        propietario = await _cargar_usuario(factory, ctx.propietario_id)
        _configurar_overrides(factory, propietario)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.post(
                "/api/reservas/solicitar",
                headers=HEADERS,
                json={
                    "area_id": area_id,
                    "unidad_id": ctx.unidad_a_id,
                    "fecha_evento": "2026-12-20",
                    "motivo_evento": "Reunión de fin de año",
                },
            )
            assert resp.status_code == 403
            assert "Reserva bloqueada por morosidad" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_solicitar_reserva_conflictos_fecha_unidad_area_e_idempotencia() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            area_sin_candado = AreaSocial(
                nombre="Cancha Múltiple",
                aforo_maximo=30,
                costo_uso_usd=Decimal("0.00"),
                deposito_garantia_usd=Decimal("0.00"),
                requiere_solvencia_estricta=False,
                es_activa=True,
            )
            seed_db.add(area_sin_candado)
            await seed_db.flush()
            reserva_ocupada = ReservaAreaSocial(
                area_id=area_sin_candado.id,
                unidad_id=ctx.unidad_b_id,
                solicitante_id=ctx.inquilino_id,
                fecha_evento=date(2026, 12, 24),
                motivo_evento="Torneo deportivo",
                estado="CONFIRMADA",
            )
            seed_db.add(reserva_ocupada)
            await seed_db.commit()
            area_id = area_sin_candado.id

        presidente = await _cargar_usuario(factory, ctx.presidente_id)
        propietario = await _cargar_usuario(factory, ctx.propietario_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Fecha ya ocupada -> 409 Conflict
            _configurar_overrides(factory, presidente)
            resp_409 = await client.post(
                "/api/reservas/solicitar",
                headers=HEADERS,
                json={
                    "area_id": area_id,
                    "unidad_id": ctx.unidad_a_id,
                    "fecha_evento": "2026-12-24",
                    "motivo_evento": "Partido amistoso vecinal",
                },
            )
            assert resp_409.status_code == 409
            assert "ya se encuentra reservada" in resp_409.json()["detail"]

            # 2. Unidad inexistente -> 404
            resp_u404 = await client.post(
                "/api/reservas/solicitar",
                headers=HEADERS,
                json={
                    "area_id": area_id,
                    "unidad_id": 999,
                    "fecha_evento": "2026-12-25",
                    "motivo_evento": "Evento vecinal",
                },
            )
            assert resp_u404.status_code == 404

            # 3. Usuario sin contrato en unidad -> 403 (propietario pide unidad_b)
            _configurar_overrides(factory, propietario)
            resp_u403 = await client.post(
                "/api/reservas/solicitar",
                headers=HEADERS,
                json={
                    "area_id": area_id,
                    "unidad_id": ctx.unidad_b_id,
                    "fecha_evento": "2026-12-25",
                    "motivo_evento": "Evento vecinal",
                },
            )
            assert resp_u403.status_code == 403

            # 4. Área inexistente o inactiva -> 404
            _configurar_overrides(factory, presidente)
            resp_a404 = await client.post(
                "/api/reservas/solicitar",
                headers=HEADERS,
                json={
                    "area_id": 999,
                    "unidad_id": ctx.unidad_a_id,
                    "fecha_evento": "2026-12-25",
                    "motivo_evento": "Evento vecinal",
                },
            )
            assert resp_a404.status_code == 404

            # 5. Idempotency-Key duplicada -> 409
            _configurar_overrides(factory, presidente, redis_new=False)
            resp_idem = await client.post(
                "/api/reservas/solicitar",
                headers=HEADERS,
                json={
                    "area_id": area_id,
                    "unidad_id": ctx.unidad_a_id,
                    "fecha_evento": "2026-12-25",
                    "motivo_evento": "Evento vecinal",
                },
            )
            assert resp_idem.status_code == 409
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


# ==============================================================================
# 3. LISTADO E INSPECCIÓN POST-EVENTO (/api/reservas y /inspeccionar)
# ==============================================================================


async def test_listar_reservas_junta_y_propietario() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            area = AreaSocial(nombre="Salón Principal", aforo_maximo=50)
            seed_db.add(area)
            await seed_db.flush()
            r1 = ReservaAreaSocial(
                area_id=area.id,
                unidad_id=ctx.unidad_a_id,
                solicitante_id=ctx.propietario_id,
                fecha_evento=date(2026, 12, 15),
                motivo_evento="Cumpleaños",
                estado="CONFIRMADA",
                creado_en=datetime(2026, 10, 30, 12, 0, 0),  # naive datetime para cubrir rama tzinfo is None
            )
            r2 = ReservaAreaSocial(
                area_id=area.id,
                unidad_id=ctx.unidad_b_id,
                solicitante_id=ctx.inquilino_id,
                fecha_evento=date(2026, 12, 16),
                motivo_evento="Aniversario",
                estado="CONFIRMADA",
            )
            seed_db.add_all([r1, r2])
            await seed_db.commit()

        conserje = await _cargar_usuario(factory, ctx.conserje_id)
        propietario = await _cargar_usuario(factory, ctx.propietario_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # Conserje ve todas las reservas
            _configurar_overrides(factory, conserje)
            resp_all = await client.get("/api/reservas")
            assert resp_all.status_code == 200
            assert len(resp_all.json()) == 2

            # Propietario ve solo las de su unidad
            _configurar_overrides(factory, propietario)
            resp_own = await client.get("/api/reservas")
            assert resp_own.status_code == 200
            assert len(resp_own.json()) == 1
            assert resp_own.json()[0]["identificador_unidad"] == "1-A"
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_inspeccionar_entrega_area_social_completa_tarea_conserje() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            area = AreaSocial(
                nombre="Salón Principal",
                aforo_maximo=50,
                deposito_garantia_usd=Decimal("80.00"),
            )
            tarea = TareaDiaria(
                titulo="Inspeccionar entrega de Salón Principal tras reserva de Unidad 1-A",
                area="Salón Principal",
                fecha=date(2026, 12, 15),
                completada=False,
            )
            seed_db.add_all([area, tarea])
            await seed_db.flush()
            reserva = ReservaAreaSocial(
                area_id=area.id,
                unidad_id=ctx.unidad_a_id,
                solicitante_id=ctx.propietario_id,
                fecha_evento=date(2026, 12, 15),
                motivo_evento="Cumpleaños",
                estado="CONFIRMADA",
                tarea_inspeccion_id=tarea.id,
            )
            reserva_sin_tarea = ReservaAreaSocial(
                area_id=area.id,
                unidad_id=ctx.unidad_b_id,
                solicitante_id=ctx.inquilino_id,
                fecha_evento=date(2026, 12, 18),
                motivo_evento="Cena",
                estado="CONFIRMADA",
                tarea_inspeccion_id=None,
            )
            seed_db.add_all([reserva, reserva_sin_tarea])
            await seed_db.commit()
            reserva_id = reserva.id
            reserva_sin_tarea_id = reserva_sin_tarea.id
            tarea_id = tarea.id

        conserje = await _cargar_usuario(factory, ctx.conserje_id)
        presidente = await _cargar_usuario(factory, ctx.presidente_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            _configurar_overrides(factory, conserje)
            resp = await client.put(
                f"/api/reservas/{reserva_id}/inspeccionar",
                headers=HEADERS,
                json={
                    "estado": "FINALIZADA_SIN_DANOS",
                    "observaciones_inspeccion": "Instalaciones entregadas limpias y sin novedades.",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["estado"] == "FINALIZADA_SIN_DANOS"
            assert body["observaciones_inspeccion"] == "Instalaciones entregadas limpias y sin novedades."

            async with factory() as check_db:
                tarea_bd = await check_db.get(TareaDiaria, tarea_id)
                assert tarea_bd is not None
                assert tarea_bd.completada is True
                assert tarea_bd.completada_en is not None

            # Re-inspeccionar una reserva ya cerrada -> 409 Conflict
            resp_409 = await client.put(
                f"/api/reservas/{reserva_id}/inspeccionar",
                headers=HEADERS,
                json={
                    "estado": "FINALIZADA_CON_DANOS",
                    "observaciones_inspeccion": "Intento duplicado",
                },
            )
            assert resp_409.status_code == 409

            # Reserva sin tarea_inspeccion_id asociada -> 200 OK y genera cargo por daños
            _configurar_overrides(factory, presidente)
            resp_sin_tarea = await client.put(
                f"/api/reservas/{reserva_sin_tarea_id}/inspeccionar",
                headers=HEADERS,
                json={
                    "estado": "FINALIZADA_CON_DANOS",
                    "observaciones_inspeccion": "Silla plástica rota en terraza.",
                },
            )
            assert resp_sin_tarea.status_code == 200
            assert resp_sin_tarea.json()["estado"] == "FINALIZADA_CON_DANOS"

            async with factory() as check_danos_db:
                res_danos = await check_danos_db.execute(
                    select(ReciboItem).where(ReciboItem.tipo_item == "DANOS_AREA_SOCIAL")
                )
                assert len(res_danos.scalars().all()) == 1

            # Reserva inexistente -> 404
            _configurar_overrides(factory, conserje)
            resp_404 = await client.put(
                "/api/reservas/999/inspeccionar",
                headers=HEADERS,
                json={
                    "estado": "FINALIZADA_SIN_DANOS",
                    "observaciones_inspeccion": "No existe",
                },
            )
            assert resp_404.status_code == 404
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
