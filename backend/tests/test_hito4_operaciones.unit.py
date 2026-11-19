"""Pruebas unitarias Nivel 11X para el Hito 4 (Administración, Incidencias, Operaciones y Worker)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.database import get_db
from src.dependencies import get_current_user
from src.main import app
from src.models import (
    ContratoOcupacion,
    FotoVocero,
    Incidencia,
    PlantillaTarea,
    TareaDiaria,
    Usuario,
)
from src.redis_client import get_redis_client
from src.worker import (
    convertir_y_subir_avif,
    encolar_notificacion_correo,
    generar_tareas_diarias_desde_plantillas,
)
from tests._sqlite_helpers import SeededCondoContext, create_sqlite_fk_factory, seed_condo_base

HEADERS = {"Idempotency-Key": "44444444-4444-4444-4444-444444444444"}


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
    mock_redis.rpush = AsyncMock(return_value=1)

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_redis_client] = lambda: mock_redis
    app.dependency_overrides[get_current_user] = lambda: usuario
    return mock_redis


# ==============================================================================
# 1. WORKER ASÍNCRONO (AVIF, NOTIFICACIONES Y CRONJOB DE TAREAS)
# ==============================================================================


def test_convertir_y_subir_avif_exitoso_y_vacio() -> None:
    uri = convertir_y_subir_avif(b"\x89PNG\r\n\x1a\ncontenido", "/voceros/2026-10/")
    assert uri.startswith("s3://condominio-media/voceros/2026-10/")
    assert uri.endswith(".avif")

    with pytest.raises(ValueError, match="vacío"):
        convertir_y_subir_avif(b"", "voceros")


async def test_encolar_notificacion_correo_con_y_sin_redis() -> None:
    mock_redis = AsyncMock()
    evento = await encolar_notificacion_correo(
        destinatarios=["presidente@test.com"],
        asunto="Nuevo vecino",
        cuerpo="Solicitud pendiente",
        redis_client=mock_redis,
    )
    assert evento["tipo"] == "EMAIL_NOTIFICATION"
    mock_redis.rpush.assert_awaited_once()

    evento_sin_redis = await encolar_notificacion_correo(
        destinatarios=["vp@test.com"],
        asunto="Aviso",
        cuerpo="Detalle",
        redis_client=None,
    )
    assert evento_sin_redis["destinatarios"] == ["vp@test.com"]

    with pytest.raises(ValueError, match="destinatario"):
        await encolar_notificacion_correo([], "Asunto", "Cuerpo")


async def test_generar_tareas_diarias_desde_plantillas_idempotente() -> None:
    engine, factory = await create_sqlite_fk_factory()
    try:
        # Caso 1: Sin plantillas activas
        async with factory() as session_vacia:
            assert await generar_tareas_diarias_desde_plantillas(session_vacia) == 0

        # Caso 2: 2 plantillas activas, 1 ya generada hoy -> solo crea 1
        fecha_obj = date(2026, 10, 29)
        async with factory() as seed_db:
            p1 = PlantillaTarea(titulo="Limpiar lobby", area="Torre A", frecuencia="DIARIA", activa=True)
            p2 = PlantillaTarea(titulo="Revisar bombas", area="Sótano", frecuencia="DIARIA", activa=True)
            seed_db.add_all([p1, p2])
            await seed_db.flush()
            seed_db.add(
                TareaDiaria(
                    plantilla_id=p1.id,
                    incidencia_id=None,
                    titulo="Limpiar lobby",
                    area="Torre A",
                    fecha=fecha_obj,
                    completada=False,
                )
            )
            await seed_db.commit()

        async with factory() as session:
            creadas = await generar_tareas_diarias_desde_plantillas(session, fecha_objetivo=fecha_obj)
            assert creadas == 1

        async with factory() as check_db:
            res = await check_db.execute(select(TareaDiaria).where(TareaDiaria.fecha == fecha_obj))
            assert len(res.scalars().all()) == 2

        # Caso 3: Todas las plantillas ya fueron generadas hoy -> 0 creadas
        async with factory() as session_completa:
            assert await generar_tareas_diarias_desde_plantillas(session_completa, fecha_objetivo=fecha_obj) == 0
    finally:
        await engine.dispose()


# ==============================================================================
# 2. ADMINISTRACIÓN: ESTRUCTURA, USUARIOS FANTASMA Y JUNTA DE CONDOMINIO
# ==============================================================================


async def test_estructura_listar_y_generar_exitoso_y_errores(monkeypatch: pytest.MonkeyPatch) -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        presidente = await _cargar_usuario(factory, ctx.presidente_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            _configurar_overrides(factory, presidente)
            r_list = await client.get("/api/estructura/unidades")
            assert r_list.status_code == 200
            assert r_list.json()[0]["identificador"] == "1-A"

            # Generación exitosa por Presidente
            r_gen = await client.post(
                "/api/estructura/generar",
                headers={"Idempotency-Key": "idem-est-001"},
                json={"nombre": "Torre A", "tipo": "EDIFICIO", "identificadores": ["A-101", "A-102", "A-101"]},
            )
            assert r_gen.status_code == 201
            assert r_gen.json()["unidades_creadas"] == 2

            # Idempotencia repetida -> 409
            _configurar_overrides(factory, presidente, redis_new=False)
            r_dup = await client.post(
                "/api/estructura/generar",
                headers={"Idempotency-Key": "idem-est-001"},
                json={"nombre": "Torre A", "tipo": "EDIFICIO", "identificadores": ["A-101"]},
            )
            assert r_dup.status_code == 409

            # IntegrityError real sobre identificador de unidad duplicado -> 409
            _configurar_overrides(factory, presidente)
            r_int = await client.post(
                "/api/estructura/generar",
                headers={"Idempotency-Key": "idem-est-002"},
                json={"nombre": "Torre B", "tipo": "EDIFICIO", "identificadores": ["A-101"]},
            )
            assert r_int.status_code == 409

            # Error inesperado de BD sobre sesión SQLite real -> 500
            async with factory() as fault_session:
                monkeypatch.setattr(
                    fault_session,
                    "commit",
                    AsyncMock(side_effect=SQLAlchemyError("db down")),
                )
                app.dependency_overrides[get_db] = lambda: fault_session
                r_err = await client.post(
                    "/api/estructura/generar",
                    headers={"Idempotency-Key": "idem-est-003"},
                    json={"nombre": "Torre C", "tipo": "EDIFICIO", "identificadores": ["C-101"]},
                )
                assert r_err.status_code == 500
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_rbac_bloquea_usuario_fantasma_y_rol_no_autorizado() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            fantasma = Usuario(
                condominio_id=1,
                nombre="Vecino Fantasma",
                cedula="V-90000041",
                correo="fantasma@condo.test",
                telefono="+584140000141",
                password_hash="hash_no_usado",
                es_activo=False,
                rol="FANTASMA",
            )
            seed_db.add(fantasma)
            await seed_db.commit()
            await seed_db.refresh(fantasma)

        propietario = await _cargar_usuario(factory, ctx.propietario_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # Estado A (Usuario Fantasma inactivo) -> 403
            _configurar_overrides(factory, fantasma)
            r_ghost = await client.get("/api/incidencias/abiertas")
            assert r_ghost.status_code == 403

            # Rol PROPIETARIO intentando aprobar usuarios -> 403
            _configurar_overrides(factory, propietario)
            r_forbidden = await client.get("/api/usuarios/pendientes")
            assert r_forbidden.status_code == 403
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_usuarios_pendientes_asignar_y_junta_cargos() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            fantasma = Usuario(
                condominio_id=1,
                nombre="Vecino Nuevo",
                cedula="V-99999999",
                correo="nuevo@condominio.test",
                telefono="04140000000",
                password_hash="hash",
                es_activo=False,
                rol="FANTASMA",
            )
            vicepresidente = Usuario(
                condominio_id=1,
                nombre="Sara Vicepresidenta",
                cedula="V-10000088",
                correo="vp@condominio.test",
                telefono="04140000088",
                password_hash="hash",
                es_activo=True,
                rol="VICEPRESIDENTE",
            )
            seed_db.add_all([fantasma, vicepresidente])
            await seed_db.flush()
            seed_db.add(
                ContratoOcupacion(
                    condominio_id=1,
                    usuario_id=fantasma.id,
                    unidad_id=ctx.unidad_a_id,
                    tipo_ocupante="PROPIETARIO",
                    es_activo=False,
                )
            )
            await seed_db.commit()
            await seed_db.refresh(fantasma)
            await seed_db.refresh(vicepresidente)

        presidente = await _cargar_usuario(factory, ctx.presidente_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Listar pendientes
            _configurar_overrides(factory, presidente)
            r_pend = await client.get("/api/usuarios/pendientes")
            assert r_pend.status_code == 200
            assert len(r_pend.json()) == 1

            # 2. Asignar con contrato previo existente
            r_asig = await client.put(
                f"/api/usuarios/{fantasma.id}/asignar",
                headers=HEADERS,
                json={"unidad_id": ctx.unidad_a_id, "tipo_ocupante": "PROPIETARIO", "rol": "PROPIETARIO"},
            )
            assert r_asig.status_code == 200
            assert r_asig.json()["es_activo"] is True
            assert r_asig.json()["rol"] == "PROPIETARIO"

            # 3. Asignar creando contrato nuevo (sin contrato previo)
            async with factory() as seed_f2:
                fantasma_2 = Usuario(
                    condominio_id=1,
                    nombre="Vecino Dos",
                    cedula="V-99999998",
                    correo="nuevo2@condominio.test",
                    telefono="04140000002",
                    password_hash="hash",
                    es_activo=False,
                    rol="FANTASMA",
                )
                seed_f2.add(fantasma_2)
                await seed_f2.commit()
                await seed_f2.refresh(fantasma_2)

            _configurar_overrides(factory, vicepresidente)
            r_asig_nuevo = await client.put(
                f"/api/usuarios/{fantasma_2.id}/asignar",
                headers=HEADERS,
                json={"unidad_id": ctx.unidad_b_id, "tipo_ocupante": "INQUILINO", "rol": "INQUILINO"},
            )
            assert r_asig_nuevo.status_code == 200
            assert r_asig_nuevo.json()["rol"] == "INQUILINO"

            # 4. Asignar usuario o unidad inexistente -> 404
            _configurar_overrides(factory, presidente)
            assert (
                await client.put(
                    "/api/usuarios/999/asignar",
                    headers=HEADERS,
                    json={"unidad_id": ctx.unidad_a_id, "tipo_ocupante": "PROPIETARIO", "rol": "PROPIETARIO"},
                )
            ).status_code == 404
            assert (
                await client.put(
                    f"/api/usuarios/{fantasma.id}/asignar",
                    headers=HEADERS,
                    json={"unidad_id": 999, "tipo_ocupante": "PROPIETARIO", "rol": "PROPIETARIO"},
                )
            ).status_code == 404

            # 5. Asignar cargo de Junta: usuario inexistente -> 404
            assert (
                await client.put("/api/junta/cargos", headers=HEADERS, json={"usuario_id": 999, "cargo": "TESORERO"})
            ).status_code == 404

            # 6. Asignar cargo de Junta: inquilino sin contrato de propietario -> 400
            r_junta_fail = await client.put(
                "/api/junta/cargos", headers=HEADERS, json={"usuario_id": ctx.inquilino_id, "cargo": "TESORERO"}
            )
            assert r_junta_fail.status_code == 400

            # 7. Asignar cargo de Junta: propietario activo con contrato -> 200
            r_junta_ok = await client.put(
                "/api/junta/cargos", headers=HEADERS, json={"usuario_id": ctx.propietario_id, "cargo": "TESORERO"}
            )
            assert r_junta_ok.status_code == 200
            assert r_junta_ok.json()["rol"] == "TESORERO"
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


# ==============================================================================
# 3. EMBUDO DE INCIDENCIAS Y ADHESIÓN ('ME SUMO')
# ==============================================================================


async def test_flujo_completo_incidencias_y_me_sumo(monkeypatch: pytest.MonkeyPatch) -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            inc = Incidencia(
                usuario_creador_id=ctx.propietario_id,
                area="Ascensor Torre A",
                descripcion="Puerta del piso 3 trabada",
                url_foto=None,
                estado="ABIERTO",
                adhesiones_count=3,
            )
            seed_db.add(inc)
            await seed_db.commit()
            inc_id = inc.id

        propietario = await _cargar_usuario(factory, ctx.propietario_id)
        inquilino = await _cargar_usuario(factory, ctx.inquilino_id)
        vocero = await _cargar_usuario(factory, ctx.vocero_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Listar abiertas
            _configurar_overrides(factory, propietario)
            r_list = await client.get("/api/incidencias/abiertas")
            assert r_list.status_code == 200
            assert r_list.json()[0]["adhesiones_count"] == 3

            # 2. Crear incidencia exitosa
            r_crear = await client.post(
                "/api/incidencias/crear",
                headers={"Idempotency-Key": "inc-key-001"},
                json={"area": "Piscina", "descripcion": "Bomba con ruido", "url_foto": "s3://condominio-media/f.avif"},
            )
            assert r_crear.status_code == 201
            assert r_crear.json()["adhesiones_count"] == 1

            # 3. Crear incidencia con Idempotency-Key repetida -> 409
            _configurar_overrides(factory, propietario, redis_new=False)
            r_dup_key = await client.post(
                "/api/incidencias/crear",
                headers={"Idempotency-Key": "inc-key-001"},
                json={"area": "Piscina", "descripcion": "Bomba con ruido"},
            )
            assert r_dup_key.status_code == 409

            # 4. Crear incidencia con fallo de BD sobre sesión SQLite real -> 500
            _configurar_overrides(factory, propietario)
            async with factory() as fault_session:
                monkeypatch.setattr(
                    fault_session,
                    "commit",
                    AsyncMock(side_effect=SQLAlchemyError("fallo bd")),
                )
                app.dependency_overrides[get_db] = lambda: fault_session
                r_err = await client.post(
                    "/api/incidencias/crear",
                    headers={"Idempotency-Key": "inc-key-002"},
                    json={"area": "Piscina", "descripcion": "Bomba con ruido"},
                )
                assert r_err.status_code == 500

            # 5. Adherir ('Me sumo') exitoso -> incrementa adhesiones_count a 4
            _configurar_overrides(factory, inquilino)
            r_adh = await client.post(f"/api/incidencias/{inc_id}/adherir", headers=HEADERS)
            assert r_adh.status_code == 200
            assert r_adh.json()["adhesiones_count"] == 4

            # 6. Adherir a incidencia inexistente -> 404
            assert (await client.post("/api/incidencias/999/adherir", headers=HEADERS)).status_code == 404

            # 7. Adherir cuando el vecino ya se sumó -> 409
            assert (await client.post(f"/api/incidencias/{inc_id}/adherir", headers=HEADERS)).status_code == 409

            # 8. Adherir con colisión concurrente IntegrityError sobre sesión SQLite real -> 409
            _configurar_overrides(factory, vocero)
            async with factory() as race_session:
                monkeypatch.setattr(
                    race_session,
                    "commit",
                    AsyncMock(side_effect=IntegrityError("dup", {}, Exception("dup"))),
                )
                app.dependency_overrides[get_db] = lambda: race_session
                assert (await client.post(f"/api/incidencias/{inc_id}/adherir", headers=HEADERS)).status_code == 409

            # 9. Adherir a incidencia CERRADA -> 409
            async with factory() as close_db:
                inc_bd = await close_db.get(Incidencia, inc_id)
                assert inc_bd is not None
                inc_bd.estado = "CERRADO"
                await close_db.commit()

            _configurar_overrides(factory, vocero)
            assert (await client.post(f"/api/incidencias/{inc_id}/adherir", headers=HEADERS)).status_code == 409
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


# ==============================================================================
# 4. OPERACIONES: CONSERJERÍA, GALERÍA DE VOCEROS (30 FOTOS), BITÁCORA Y COMUNICADOS
# ==============================================================================


async def test_conserjeria_plantillas_tareas_y_cierre_automatico_incidencia() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            inc = Incidencia(
                usuario_creador_id=ctx.propietario_id,
                area="Portón",
                descripcion="Falta lubricación",
                url_foto=None,
                estado="ABIERTO",
                adhesiones_count=2,
            )
            vicepresidente = Usuario(
                condominio_id=1,
                nombre="Sara Vicepresidenta",
                cedula="V-10000089",
                correo="vp_ops@condominio.test",
                telefono="04140000089",
                password_hash="hash",
                es_activo=True,
                rol="VICEPRESIDENTE",
            )
            seed_db.add_all([inc, vicepresidente])
            await seed_db.commit()
            await seed_db.refresh(vicepresidente)
            inc_id = inc.id

        presidente = await _cargar_usuario(factory, ctx.presidente_id)
        conserje = await _cargar_usuario(factory, ctx.conserje_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Crear plantilla
            _configurar_overrides(factory, presidente)
            r_plant = await client.post(
                "/api/tareas/plantillas",
                headers=HEADERS,
                json={"titulo": "Baldeo de entrada", "area": "Planta Baja", "frecuencia": "DIARIA"},
            )
            assert r_plant.status_code == 201
            assert r_plant.json()["activa"] is True

            # 2. Asignar tarea directa vinculada a incidencia -> pasa incidencia a EN_PROCESO
            r_td = await client.post(
                "/api/tareas/diarias",
                headers=HEADERS,
                json={"titulo": "Lubricar riel de portón", "area": "Portón", "incidencia_id": inc_id},
            )
            assert r_td.status_code == 201
            tarea_inc_id = r_td.json()["id"]
            async with factory() as chk_db:
                inc_proc = await chk_db.get(Incidencia, inc_id)
                assert inc_proc is not None
                assert inc_proc.estado == "EN_PROCESO"

            # 3. Asignar tarea directa con incidencia inexistente -> 404
            r_td_404 = await client.post(
                "/api/tareas/diarias",
                headers=HEADERS,
                json={"titulo": "Revisar foco", "area": "Pasillo", "incidencia_id": 999},
            )
            assert r_td_404.status_code == 404

            # 4. Asignar tarea directa sin incidencia
            _configurar_overrides(factory, vicepresidente)
            r_td_simple = await client.post(
                "/api/tareas/diarias",
                headers=HEADERS,
                json={"titulo": "Limpiar vidrios", "area": "Lobby"},
            )
            assert r_td_simple.status_code == 201
            tarea_simple_id = r_td_simple.json()["id"]

            # 5. Ejecutar cronjob desde endpoint
            _configurar_overrides(factory, presidente)
            r_cron = await client.post("/api/tareas/generar-diarias")
            assert r_cron.status_code == 200
            assert r_cron.json()["tareas_generadas"] == 1

            # 6. Listar tareas del día
            _configurar_overrides(factory, conserje)
            r_list = await client.get("/api/tareas/diarias")
            assert r_list.status_code == 200
            assert len(r_list.json()) >= 1

            # 7. Completar tarea vinculada a incidencia -> cierra incidencia automáticamente
            r_comp = await client.put(
                f"/api/tareas/{tarea_inc_id}/completar",
                headers=HEADERS,
                json={"url_evidencia": "s3://condominio-media/evidencias/porton.avif"},
            )
            assert r_comp.status_code == 200
            assert r_comp.json()["completada"] is True
            async with factory() as chk_close_db:
                inc_cerrada = await chk_close_db.get(Incidencia, inc_id)
                assert inc_cerrada is not None
                assert inc_cerrada.estado == "CERRADO"

            # 8. Completar tarea sin incidencia vinculada
            assert (
                await client.put(f"/api/tareas/{tarea_simple_id}/completar", headers=HEADERS, json={})
            ).status_code == 200

            # 9. Completar tarea inexistente -> 404
            assert (await client.put("/api/tareas/999/completar", headers=HEADERS, json={})).status_code == 404
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_galeria_voceros_limite_estricto_30_fotos_por_mes() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            seed_db.add_all(
                [
                    FotoVocero(
                        usuario_id=ctx.vocero_id,
                        periodo="2026-10",
                        area="Jardines",
                        comentario=f"Foto {i}",
                        url_foto=f"s3://condominio-media/voceros/{i}.avif",
                    )
                    for i in range(1, 30)
                ]
            )
            await seed_db.commit()

        vocero = await _cargar_usuario(factory, ctx.vocero_id)
        propietario = await _cargar_usuario(factory, ctx.propietario_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Subida exitosa cuando hay < 30 fotos en el mes
            _configurar_overrides(factory, vocero)
            r_ok = await client.post(
                "/api/voceros/fotos",
                headers=HEADERS,
                json={
                    "periodo": "2026-10",
                    "area": "Jardines",
                    "comentario": "Foto número 30 permitida",
                    "url_foto": "s3://condominio-media/voceros/30.avif",
                },
            )
            assert r_ok.status_code == 201

            # 2. Subida número 31 en el mismo mes -> Rechazada con 429 Too Many Requests
            r_limite = await client.post(
                "/api/voceros/fotos",
                headers=HEADERS,
                json={
                    "periodo": "2026-10",
                    "area": "Jardines",
                    "comentario": "Intento 31 sobre el límite",
                    "url_foto": "s3://condominio-media/voceros/31.avif",
                },
            )
            assert r_limite.status_code == 429
            assert "30 fotografías" in r_limite.json()["detail"]

            # 3. Consultar galería del mes
            _configurar_overrides(factory, propietario)
            r_gal = await client.get("/api/voceros/galeria?periodo=2026-10")
            assert r_gal.status_code == 200
            assert r_gal.json()["fotos_usadas_mes"] == 30
            assert r_gal.json()["limite_mensual"] == 30
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_bitacora_secretario_y_comunicados_con_anti_ssrf() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        secretario = await _cargar_usuario(factory, ctx.secretario_id)
        propietario = await _cargar_usuario(factory, ctx.propietario_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Crear y listar acta de bitácora
            _configurar_overrides(factory, secretario)
            r_acta = await client.post(
                "/api/bitacora/acta",
                headers=HEADERS,
                json={
                    "fecha": "2026-10-29",
                    "hora": "19:30",
                    "ubicacion": "Salón de Fiestas",
                    "contenido": "Se aprobó el presupuesto de pintura.",
                },
            )
            assert r_acta.status_code == 201

            _configurar_overrides(factory, propietario)
            r_hist = await client.get("/api/bitacora/historial")
            assert r_hist.status_code == 200
            assert len(r_hist.json()) == 1

            # 2. Publicar comunicado sin enlace externo -> 201
            _configurar_overrides(factory, secretario)
            r_com = await client.post(
                "/api/comunicados",
                headers=HEADERS,
                json={"titulo": "Corte programado de agua", "contenido": "Mantenimiento de tanque el sábado."},
            )
            assert r_com.status_code == 201

            # 3. Publicar comunicado con URL interna SSRF -> Bloqueado con 400
            r_ssrf = await client.post(
                "/api/comunicados",
                headers=HEADERS,
                json={
                    "titulo": "Enlace malicioso",
                    "contenido": "Prueba SSRF",
                    "enlace_externo": "http://127.0.0.1:8000/internal",
                },
            )
            assert r_ssrf.status_code == 400

            # 4. Listar comunicados recientes
            _configurar_overrides(factory, propietario)
            r_rec = await client.get("/api/comunicados/recientes")
            assert r_rec.status_code == 200
            assert r_rec.json()[0]["titulo"] == "Corte programado de agua"
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
