"""Pruebas unitarias Nivel 11X para el Hito 11: Gobernanza Digital, Cartas Consulta (Art. 23 LPH) y Asambleas."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.database import get_db
from src.dependencies import get_current_user
from src.finanzas import (
    ErrorFinanciero,
    calcular_ip_hash_voto,
    construir_mensaje_voto_consulta,
    evaluar_escrutinio_consulta,
    generar_firma_voto_consulta,
    umbral_quorum_por_regla,
    verificar_firma_voto_consulta,
)
from src.main import app
from src.models import (
    BitacoraActa,
    ConsultaComunitaria,
    ContratoOcupacion,
    OpcionConsulta,
    Unidad,
    Usuario,
    VotoConsulta,
)
from src.redis_client import get_redis_client
from src.security import get_vote_signing_key
from tests._sqlite_helpers import SeededCondoContext, create_sqlite_fk_factory, seed_condo_base

HEADERS = {"Idempotency-Key": "018f4a12-1111-7000-8000-000000001111"}


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
# 1. FUNCIONES PURAS CRIPTOGRÁFICAS Y DE ESCRUTINIO LPH (src/finanzas.py)
# ==============================================================================


def test_umbral_quorum_por_regla_y_error() -> None:
    assert umbral_quorum_por_regla("DOS_TERCIOS") == Decimal("66.6667")
    assert umbral_quorum_por_regla("MAYORIA_SIMPLE") == Decimal("50.0000")
    assert umbral_quorum_por_regla("UNANIMIDAD") == Decimal("100.0000")
    with pytest.raises(ErrorFinanciero, match="Regla de quórum inválida"):
        umbral_quorum_por_regla("CUARTO")


def test_firma_voto_consulta_y_ip_hash() -> None:
    fecha_iso = "2026-10-30T12:00:00+00:00"
    msg = construir_mensaje_voto_consulta(4, 12, 1, Decimal("25.5"), fecha_iso)
    assert msg == "VOTO|v1|4|12|1|25.5000|2026-10-30T12:00:00+00:00"

    vote_key = get_vote_signing_key()
    firma = generar_firma_voto_consulta(4, 12, 1, Decimal("25.5000"), fecha_iso, vote_key)
    assert len(firma) == 64
    assert verificar_firma_voto_consulta(4, 12, 1, Decimal("25.5000"), fecha_iso, firma, vote_key) is True
    assert verificar_firma_voto_consulta(4, 12, 2, Decimal("25.5000"), fecha_iso, firma, vote_key) is False
    assert verificar_firma_voto_consulta(4, 12, 1, Decimal("25.5000"), fecha_iso, "   ", vote_key) is False

    h1 = calcular_ip_hash_voto("192.168.1.50", 4, vote_key)
    h2 = calcular_ip_hash_voto("", 4, vote_key)
    assert len(h1) == 64 and len(h2) == 64 and h1 != h2


def test_evaluar_escrutinio_consulta_tres_estados() -> None:
    # 1. Sin quórum (participación 45% < 66.67%)
    est_sq, part_sq, aprob_sq = evaluar_escrutinio_consulta(
        Decimal("66.6700"), {1}, {1: Decimal("30.0000"), 2: Decimal("15.0000")}
    )
    assert est_sq == "CERRADA_SIN_QUORUM"
    assert part_sq == Decimal("45.0000")
    assert aprob_sq == Decimal("30.0000")

    # 2. Aprobada (participación 80%, aprobatoria 70% >= 66.67%)
    est_ap, part_ap, aprob_ap = evaluar_escrutinio_consulta(
        Decimal("66.6700"), {1}, {1: Decimal("70.0000"), 2: Decimal("10.0000")}
    )
    assert est_ap == "CERRADA_APROBADA"
    assert part_ap == Decimal("80.0000")
    assert aprob_ap == Decimal("70.0000")

    # 3. Rechazada (participación 80% >= 66.67%, pero aprobatoria 40% < 66.67%)
    est_re, part_re, aprob_re = evaluar_escrutinio_consulta(
        Decimal("66.6700"), {1}, {1: Decimal("40.0000"), 2: Decimal("40.0000")}
    )
    assert est_re == "CERRADA_RECHAZADA"
    assert part_re == Decimal("80.0000")
    assert aprob_re == Decimal("40.0000")


def test_evaluar_escrutinio_dos_tercios_fraccion_racional_exacta() -> None:
    # 66.6666% es estrictamente menor que 2/3 -> sin quórum y aprobatoria insuficiente
    est_sin, part_sin, _ = evaluar_escrutinio_consulta(
        Decimal("66.6667"), {1}, {1: Decimal("66.6666")}, regla_quorum="DOS_TERCIOS"
    )
    assert est_sin == "CERRADA_SIN_QUORUM"
    assert part_sin == Decimal("66.6666")

    est_rech, part_rech, aprob_rech = evaluar_escrutinio_consulta(
        Decimal("66.6667"), {1}, {1: Decimal("66.6666"), 2: Decimal("33.3334")}, regla_quorum="DOS_TERCIOS"
    )
    assert est_rech == "CERRADA_RECHAZADA"
    assert part_rech == Decimal("100.0000")
    assert aprob_rech == Decimal("66.6666")

    # 66.6667% (33.3334% + 33.3333%) supera 2/3 exacto -> CERRADA_APROBADA
    est_ok, part_ok, aprob_ok = evaluar_escrutinio_consulta(
        Decimal("66.6667"), {1}, {1: Decimal("66.6667"), 2: Decimal("0.0000")}, regla_quorum="DOS_TERCIOS"
    )
    assert est_ok == "CERRADA_APROBADA"
    assert part_ok == Decimal("66.6667")
    assert aprob_ok == Decimal("66.6667")


# ==============================================================================
# 2. ENDPOINTS DE CREACIÓN Y CONSULTA (/api/consultas)
# ==============================================================================


async def test_crear_consulta_exitoso_y_validaciones() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        presidente = await _cargar_usuario(factory, ctx.presidente_id)
        secretario = await _cargar_usuario(factory, ctx.secretario_id)
        cierre = datetime.now(UTC) + timedelta(days=5)

        _configurar_overrides(factory, presidente)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.post(
                "/api/consultas",
                headers=HEADERS,
                json={
                    "titulo": "Carta Consulta #04-2026: Impermeabilización Torre A",
                    "descripcion_legal": "Reparación urgente del manto asfáltico conforme al Art. 23 LPH.",
                    "tipo_consulta": "CARTA_CONSULTA_1RA",
                    "regla_quorum": "DOS_TERCIOS",
                    "fecha_cierre": cierre.isoformat(),
                    "opciones": [
                        {"etiqueta": "APROBAR PRESUPUESTO A", "es_opcion_aprobatoria": True},
                        {"etiqueta": "RECHAZAR PROPUESTA", "es_opcion_aprobatoria": False},
                    ],
                },
            )
            assert resp.status_code == 201
            body = resp.json()
            assert body["quorum_minimo_alicuota"] == "66.6667"
            assert body["estado"] == "ABIERTA"
            assert len(body["opciones"]) == 2
            assert body["ya_voto_usuario"] is False

            # Idempotency-Key duplicada -> 409
            _configurar_overrides(factory, secretario, redis_new=False)
            resp_dup = await client.post(
                "/api/consultas",
                headers=HEADERS,
                json={
                    "titulo": "Carta Consulta Duplicada",
                    "descripcion_legal": "Descripción legal suficiente.",
                    "fecha_cierre": cierre.isoformat(),
                    "opciones": [
                        {"etiqueta": "SÍ", "es_opcion_aprobatoria": True},
                        {"etiqueta": "NO", "es_opcion_aprobatoria": False},
                    ],
                },
            )
            assert resp_dup.status_code == 409

        async with factory() as check_db:
            consulta_bd = await check_db.get(ConsultaComunitaria, body["id"])
            assert consulta_bd is not None
            res_ops = await check_db.execute(select(OpcionConsulta).where(OpcionConsulta.consulta_id == consulta_bd.id))
            assert len(res_ops.scalars().all()) == 2
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_listar_y_obtener_detalle_consulta_con_voto_previo() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        ahora = datetime.now(UTC)
        async with factory() as seed_db:
            consulta = ConsultaComunitaria(
                titulo="Carta Consulta Ascensor",
                descripcion_legal="Cambio de guayas.",
                tipo_consulta="CARTA_CONSULTA_1RA",
                regla_quorum="DOS_TERCIOS",
                quorum_minimo_alicuota=Decimal("66.6700"),
                fecha_apertura=ahora,
                fecha_cierre=ahora + timedelta(days=3),
                estado="ABIERTA",
                creada_por_id=ctx.presidente_id,
                acta_bitacora_id=None,
            )
            seed_db.add(consulta)
            await seed_db.flush()
            op1 = OpcionConsulta(consulta_id=consulta.id, etiqueta="Aprobar", es_opcion_aprobatoria=True)
            op2 = OpcionConsulta(consulta_id=consulta.id, etiqueta="Rechazar", es_opcion_aprobatoria=False)
            seed_db.add_all([op1, op2])
            await seed_db.flush()
            seed_db.add(
                VotoConsulta(
                    condominio_id=1,
                    jti=str(uuid.uuid4()),
                    consulta_id=consulta.id,
                    unidad_id=ctx.unidad_a_id,
                    usuario_id=ctx.propietario_id,
                    opcion_id=op1.id,
                    alicuota_capturada=Decimal("35.0000"),
                    fecha_voto=ahora,
                    ip_hash="a" * 64,
                    firma_hmac="b" * 64,
                    prev_hash="0" * 64,
                    record_hash="1" * 64,
                )
            )
            await seed_db.commit()
            consulta_id = consulta.id

        propietario = await _cargar_usuario(factory, ctx.propietario_id)
        _configurar_overrides(factory, propietario)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp_list = await client.get("/api/consultas")
            assert resp_list.status_code == 200
            items = resp_list.json()
            assert len(items) == 1
            assert items[0]["participacion_alicuota"] == "35.0000"
            assert items[0]["ya_voto_usuario"] is True

            resp_det = await client.get(f"/api/consultas/{consulta_id}")
            assert resp_det.status_code == 200
            det = resp_det.json()
            assert det["mi_voto"]["identificador_unidad"] == "1-A"
            assert det["mi_voto"]["firma_hmac"] == "b" * 64

            # 404 cuando no existe
            assert (await client.get("/api/consultas/999")).status_code == 404
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


# ==============================================================================
# 3. VOTACIÓN PONDERADA POR ALÍCUOTA E INVARIANTES NEGATIVAS (/votar)
# ==============================================================================


async def test_votar_en_consulta_propietario_exitoso_e_inquilino_con_y_sin_poder() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        ahora = datetime.now(UTC)
        async with factory() as seed_db:
            consulta = ConsultaComunitaria(
                titulo="Carta Consulta #08",
                descripcion_legal="Pintura de fachada.",
                tipo_consulta="CARTA_CONSULTA_1RA",
                regla_quorum="DOS_TERCIOS",
                quorum_minimo_alicuota=Decimal("66.6700"),
                fecha_apertura=ahora - timedelta(hours=1),
                fecha_cierre=ahora + timedelta(days=3),
                estado="ABIERTA",
                creada_por_id=ctx.presidente_id,
            )
            seed_db.add(consulta)
            await seed_db.flush()
            op = OpcionConsulta(consulta_id=consulta.id, etiqueta="Aprobar Fachada", es_opcion_aprobatoria=True)
            seed_db.add(op)
            await seed_db.commit()
            consulta_id = consulta.id
            opcion_id = op.id

        propietario = await _cargar_usuario(factory, ctx.propietario_id)
        inquilino = await _cargar_usuario(factory, ctx.inquilino_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # Propietario con contrato activo en unidad_a (60.0000%) -> 201
            _configurar_overrides(factory, propietario)
            resp = await client.post(
                f"/api/consultas/{consulta_id}/votar",
                headers=HEADERS,
                json={"unidad_id": ctx.unidad_a_id, "opcion_id": opcion_id},
            )
            assert resp.status_code == 201
            recibo = resp.json()
            assert recibo["identificador_unidad"] == "1-A"
            assert recibo["alicuota_capturada"] == "60.0000"
            assert recibo["participacion_total_alicuota"] == "60.0000"
            assert len(recibo["firma_hmac"]) == 64

            # Inquilino SIN poder registrado en unidad_b -> 403 Forbidden
            _configurar_overrides(factory, inquilino)
            resp_inq = await client.post(
                f"/api/consultas/{consulta_id}/votar",
                headers=HEADERS,
                json={"unidad_id": ctx.unidad_b_id, "opcion_id": opcion_id},
            )
            assert resp_inq.status_code == 403
            assert "propietario titular" in resp_inq.json()["detail"].lower()

            # Con poder registrado en ContratoOcupacion -> Inquilino vota exitosamente -> 201
            async with factory() as upd_db:
                res_c = await upd_db.execute(
                    select(ContratoOcupacion).where(
                        ContratoOcupacion.usuario_id == ctx.inquilino_id,
                        ContratoOcupacion.unidad_id == ctx.unidad_b_id,
                    )
                )
                contrato_inq = res_c.scalars().first()
                assert contrato_inq is not None
                contrato_inq.puede_votar_asamblea = True
                await upd_db.commit()

            resp_inq_ok = await client.post(
                f"/api/consultas/{consulta_id}/votar",
                headers=HEADERS,
                json={"unidad_id": ctx.unidad_b_id, "opcion_id": opcion_id},
            )
            assert resp_inq_ok.status_code == 201
            assert resp_inq_ok.json()["participacion_total_alicuota"] == "100.0000"
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_votar_errores_404_403_409_y_race_condition(monkeypatch: pytest.MonkeyPatch) -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        ahora = datetime.now(UTC)
        async with factory() as seed_db:
            consulta_abierta = ConsultaComunitaria(
                titulo="Consulta",
                descripcion_legal="Texto legal.",
                tipo_consulta="CARTA_CONSULTA_1RA",
                regla_quorum="DOS_TERCIOS",
                quorum_minimo_alicuota=Decimal("66.6700"),
                fecha_apertura=ahora - timedelta(hours=1),
                fecha_cierre=ahora + timedelta(days=2),
                estado="ABIERTA",
                creada_por_id=ctx.presidente_id,
            )
            consulta_cerrada = ConsultaComunitaria(
                titulo="Cerrada",
                descripcion_legal="Texto.",
                tipo_consulta="CARTA_CONSULTA_1RA",
                regla_quorum="DOS_TERCIOS",
                quorum_minimo_alicuota=Decimal("66.6700"),
                fecha_apertura=ahora - timedelta(days=3),
                fecha_cierre=ahora + timedelta(days=2),
                estado="CERRADA_APROBADA",
                creada_por_id=ctx.presidente_id,
            )
            seed_db.add_all([consulta_abierta, consulta_cerrada])
            await seed_db.flush()
            op = OpcionConsulta(consulta_id=consulta_abierta.id, etiqueta="Sí", es_opcion_aprobatoria=True)
            seed_db.add(op)
            await seed_db.commit()
            abierta_id = consulta_abierta.id
            cerrada_id = consulta_cerrada.id
            opcion_id = op.id

        propietario = await _cargar_usuario(factory, ctx.propietario_id)
        payload = {"unidad_id": ctx.unidad_a_id, "opcion_id": opcion_id}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Idempotency-Key duplicada -> 409
            _configurar_overrides(factory, propietario, redis_new=False)
            resp_idem = await client.post(f"/api/consultas/{abierta_id}/votar", headers=HEADERS, json=payload)
            assert resp_idem.status_code == 409

            # 2. Consulta no encontrada -> 404
            _configurar_overrides(factory, propietario)
            assert (await client.post("/api/consultas/999/votar", headers=HEADERS, json=payload)).status_code == 404

            # 3. Consulta cerrada -> 409
            resp_cerrada = await client.post(f"/api/consultas/{cerrada_id}/votar", headers=HEADERS, json=payload)
            assert resp_cerrada.status_code == 409

            # 4. Opción no encontrada -> 404
            assert (
                await client.post(
                    f"/api/consultas/{abierta_id}/votar",
                    headers=HEADERS,
                    json={"unidad_id": ctx.unidad_a_id, "opcion_id": 999},
                )
            ).status_code == 404

            # 5. Unidad no encontrada -> 404
            assert (
                await client.post(
                    f"/api/consultas/{abierta_id}/votar",
                    headers=HEADERS,
                    json={"unidad_id": 999, "opcion_id": opcion_id},
                )
            ).status_code == 404

            # 6. Sin contrato activo sobre la unidad -> 403 (propietario intenta votar en unidad_b)
            assert (
                await client.post(
                    f"/api/consultas/{abierta_id}/votar",
                    headers=HEADERS,
                    json={"unidad_id": ctx.unidad_b_id, "opcion_id": opcion_id},
                )
            ).status_code == 403

            # 7. IntegrityError concurrente en commit sobre sesión SQLite real -> 409
            async with factory() as fault_session:
                monkeypatch.setattr(
                    fault_session,
                    "commit",
                    AsyncMock(side_effect=IntegrityError("dup", {}, Exception("uq_voto_consulta_unidad"))),
                )
                app.dependency_overrides[get_db] = lambda: fault_session
                assert (
                    await client.post(f"/api/consultas/{abierta_id}/votar", headers=HEADERS, json=payload)
                ).status_code == 409

            # 8. Voto previo existente en BD -> 409
            _configurar_overrides(factory, propietario)
            resp_v1 = await client.post(f"/api/consultas/{abierta_id}/votar", headers=HEADERS, json=payload)
            assert resp_v1.status_code == 201
            resp_v2 = await client.post(f"/api/consultas/{abierta_id}/votar", headers=HEADERS, json=payload)
            assert resp_v2.status_code == 409
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


# ==============================================================================
# 4. CIERRE DE CONSULTA Y GENERACIÓN AUTOMÁTICA DE ACTA EN BITÁCORA (/cerrar)
# ==============================================================================


async def test_cerrar_consulta_genera_acta_bitacora_y_maneja_errores() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        ahora = datetime.now(UTC)
        async with factory() as seed_db:
            consulta = ConsultaComunitaria(
                titulo="Carta Consulta #12: Bomba Hidroneumática",
                descripcion_legal="Sustitución de bomba principal.",
                tipo_consulta="CARTA_CONSULTA_1RA",
                regla_quorum="DOS_TERCIOS",
                quorum_minimo_alicuota=Decimal("66.6700"),
                fecha_apertura=ahora - timedelta(days=1),
                fecha_cierre=ahora - timedelta(minutes=1),
                estado="ABIERTA",
                creada_por_id=ctx.presidente_id,
            )
            seed_db.add(consulta)
            await seed_db.flush()
            op_si = OpcionConsulta(consulta_id=consulta.id, etiqueta="Aprobar Bomba", es_opcion_aprobatoria=True)
            op_no = OpcionConsulta(consulta_id=consulta.id, etiqueta="Rechazar", es_opcion_aprobatoria=False)
            seed_db.add_all([op_si, op_no])
            await seed_db.flush()

            u_c = Unidad(
                condominio_id=1,
                identificador="1-C",
                estructura_id=ctx.estructura_id,
                alicuota=Decimal("30.0000"),
            )
            seed_db.add(u_c)
            await seed_db.flush()

            seed_db.add_all(
                [
                    VotoConsulta(
                        condominio_id=1,
                        jti=str(uuid.uuid4()),
                        consulta_id=consulta.id,
                        unidad_id=ctx.unidad_a_id,
                        usuario_id=ctx.propietario_id,
                        opcion_id=op_si.id,
                        alicuota_capturada=Decimal("40.0000"),
                        fecha_voto=ahora,
                        ip_hash="1" * 64,
                        firma_hmac="a" * 64,
                        prev_hash="0" * 64,
                        record_hash="1" * 64,
                    ),
                    VotoConsulta(
                        condominio_id=1,
                        jti=str(uuid.uuid4()),
                        consulta_id=consulta.id,
                        unidad_id=u_c.id,
                        usuario_id=ctx.inquilino_id,
                        opcion_id=op_si.id,
                        alicuota_capturada=Decimal("30.0000"),
                        fecha_voto=ahora,
                        ip_hash="2" * 64,
                        firma_hmac="b" * 64,
                        prev_hash="1" * 64,
                        record_hash="2" * 64,
                    ),
                ]
            )
            await seed_db.commit()
            consulta_id = consulta.id

        secretario = await _cargar_usuario(factory, ctx.secretario_id)
        presidente = await _cargar_usuario(factory, ctx.presidente_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            _configurar_overrides(factory, secretario)
            resp = await client.post(f"/api/consultas/{consulta_id}/cerrar", headers=HEADERS)
            assert resp.status_code == 200
            body = resp.json()
            assert body["estado"] == "CERRADA_APROBADA"
            assert body["participacion_alicuota"] == "70.0000"
            assert body["alicuota_aprobatoria"] == "70.0000"
            assert body["acta_bitacora_id"] >= 1
            assert len(body["hash_global_escrutinio"]) == 64

            # Verificar que el acta se persistió en BitacoraActa dentro de SQLite real
            async with factory() as check_db:
                acta = await check_db.get(BitacoraActa, body["acta_bitacora_id"])
                assert acta is not None
                assert "Bomba Hidroneumática" in acta.contenido

            # Errores: Idempotency-Key duplicada (409), no encontrada (404), ya cerrada (409)
            _configurar_overrides(factory, presidente, redis_new=False)
            assert (await client.post(f"/api/consultas/{consulta_id}/cerrar", headers=HEADERS)).status_code == 409

            _configurar_overrides(factory, presidente)
            assert (await client.post("/api/consultas/999/cerrar", headers=HEADERS)).status_code == 404
            assert (await client.post(f"/api/consultas/{consulta_id}/cerrar", headers=HEADERS)).status_code == 409
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
