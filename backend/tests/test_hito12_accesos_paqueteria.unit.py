"""Pruebas unitarias Nivel 11X para el Hito 12: Pases de Visita QR (HMAC-SHA256 + KeyDB Anti-Replay) y Paquetería."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.database import get_db
from src.dependencies import get_current_user
from src.finanzas import (
    ErrorFinanciero,
    construir_claims_pase_qr,
    construir_token_pase_qr,
    decodificar_y_verificar_token_pase_qr,
    generar_firma_pase_qr,
)
from src.main import app
from src.models import PaqueteRecibido, PaseVisita, Unidad, Usuario
from src.redis_client import (
    build_qr_nonce_key,
    burn_qr_nonce,
    get_redis_client,
    is_qr_nonce_burned,
)
from src.schemas import PaseVisitaCreate
from src.security import get_qr_signing_key
from tests._sqlite_helpers import SeededCondoContext, create_sqlite_fk_factory, seed_condo_base

HEADERS = {"Idempotency-Key": "018f4a12-1212-7000-8000-000000001212"}


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
    mock_redis.get.return_value = None
    mock_redis.rpush = AsyncMock(return_value=1)

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_redis_client] = lambda: mock_redis
    app.dependency_overrides[get_current_user] = lambda: usuario
    return mock_redis


# ==============================================================================
# 1. CRIPTOGRAFÍA HMAC-SHA256 DE PASES QR Y ANTI-REPLAY KEYDB
# ==============================================================================


def test_pase_qr_claims_firma_y_verificacion_exitosa() -> None:
    jti = "550e8400-e29b-41d4-a716-446655440000"
    exp = 1800000000
    claims = construir_claims_pase_qr(jti, 7, "UNICO_USO", exp)
    assert claims == f"QR|v1|{jti}|7|UNICO_USO|{exp}"

    qr_key = get_qr_signing_key()
    sig = generar_firma_pase_qr(jti, 7, "UNICO_USO", exp, qr_key)
    assert len(sig) == 64

    token = construir_token_pase_qr(jti, 7, "UNICO_USO", exp, sig)
    jti_out, uid_out, mod_out, exp_out, sig_out = decodificar_y_verificar_token_pase_qr(token, qr_key)
    assert jti_out == jti
    assert uid_out == 7
    assert mod_out == "UNICO_USO"
    assert exp_out == exp
    assert sig_out == sig


@pytest.mark.parametrize(
    "token_invalido",
    [
        "",
        "sin_punto_separador",
        ".solo_firma",
        "solo_payload.",
        "!!!base64_corrupto!!!.abcdef",
        "UVJ8djF8c29sb190cmVz.abcdef",  # menos de 6 partes
        "UVJ8djF8anRpfG5vX2ludHxVTklDT19VU098MTIz.abcdef",  # unidad_id no entero
    ],
)
def test_decodificar_pase_qr_formatos_invalidos(token_invalido: str) -> None:
    with pytest.raises(ErrorFinanciero, match="Firma criptográfica de pase QR inválida"):
        decodificar_y_verificar_token_pase_qr(token_invalido, get_qr_signing_key())


def test_decodificar_pase_qr_firma_adulterada() -> None:
    jti = "550e8400-e29b-41d4-a716-446655440099"
    sig = generar_firma_pase_qr(jti, 3, "UNICO_USO", 1800000000, get_qr_signing_key())
    token = construir_token_pase_qr(jti, 3, "UNICO_USO", 1800000000, "0" * len(sig))
    with pytest.raises(ErrorFinanciero, match="Firma criptográfica de pase QR inválida"):
        decodificar_y_verificar_token_pase_qr(token, get_qr_signing_key())


@pytest.mark.anyio
async def test_redis_qr_nonce_helpers() -> None:
    from src.redis_client import reset_local_security_state

    reset_local_security_state()
    assert build_qr_nonce_key(" abc-123 ") == "qr_used:abc-123"
    assert await burn_qr_nonce(None, "abc-123") is True
    assert await is_qr_nonce_burned(None, "abc-123") is True
    assert await is_qr_nonce_burned(None, "no-quemado") is False

    mock_redis = AsyncMock()
    mock_redis.set.return_value = True
    mock_redis.get.return_value = "1"
    assert await burn_qr_nonce(mock_redis, "remoto-1", ttl_seconds=300) is True
    assert await is_qr_nonce_burned(mock_redis, "remoto-1") is True

    mock_redis.get.side_effect = RuntimeError("KeyDB offline")
    assert await is_qr_nonce_burned(mock_redis, "remoto-1") is False
    reset_local_security_state()


def test_schema_pase_visita_normaliza_timezone() -> None:
    naive_dt = datetime(2026, 10, 30, 12, 0, 0)
    schema = PaseVisitaCreate(
        unidad_id=1,
        nombre_visitante="Pedro Pérez",
        cedula_visitante="V-12345678",
        valido_desde=naive_dt,
        valido_hasta=naive_dt + timedelta(hours=4),
    )
    assert schema.valido_desde is not None and schema.valido_desde.tzinfo == UTC
    assert schema.valido_hasta is not None and schema.valido_hasta.tzinfo == UTC


# ==============================================================================
# 2. ENDPOINTS DE PASES DE VISITA QR (/api/accesos/*)
# ==============================================================================


async def test_crear_pase_visita_exitoso_y_fantasma_bloqueado() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            fantasma = Usuario(
                condominio_id=1,
                nombre="Vecino Fantasma",
                cedula="V-90000081",
                correo="fantasma@condo.test",
                telefono="+584140000181",
                password_hash="hash_no_usado",
                es_activo=False,
                rol="FANTASMA",
            )
            seed_db.add(fantasma)
            await seed_db.commit()
            await seed_db.refresh(fantasma)

        propietario = await _cargar_usuario(factory, ctx.propietario_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Fantasma bloqueado con 403
            _configurar_overrides(factory, fantasma)
            r_ghost = await client.post(
                "/api/accesos/pases",
                headers=HEADERS,
                json={
                    "unidad_id": ctx.unidad_a_id,
                    "nombre_visitante": "Carlos Visitante",
                    "cedula_visitante": "V-19888777",
                },
            )
            assert r_ghost.status_code == 403

            # 2. Propietario con unidad activa crea pase exitosamente
            _configurar_overrides(factory, propietario)
            r_ok = await client.post(
                "/api/accesos/pases",
                headers=HEADERS,
                json={
                    "unidad_id": ctx.unidad_a_id,
                    "nombre_visitante": "Carlos Visitante",
                    "cedula_visitante": "v-19888777",
                    "placa_vehiculo": "ab123cd",
                    "modalidad": "UNICO_USO",
                    "horas_validez": 12,
                },
            )
            assert r_ok.status_code == 201
            body = r_ok.json()
            assert body["identificador_unidad"] == "1-A"
            assert body["cedula_visitante"] == "V-19888777"
            assert body["placa_vehiculo"] == "AB123CD"
            assert "." in body["qr_token"]

        async with factory() as check_db:
            pase_bd = await check_db.get(PaseVisita, body["id"])
            assert pase_bd is not None
            assert pase_bd.estado == "ACTIVO"
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_crear_pase_visita_errores_idempotencia_contrato_y_ventana() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        propietario = await _cargar_usuario(factory, ctx.propietario_id)
        presidente = await _cargar_usuario(factory, ctx.presidente_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # Idempotency duplicada -> 409
            _configurar_overrides(factory, propietario, redis_new=False)
            r_dup = await client.post(
                "/api/accesos/pases",
                headers=HEADERS,
                json={"unidad_id": ctx.unidad_a_id, "nombre_visitante": "Visitante", "cedula_visitante": "V-11222333"},
            )
            assert r_dup.status_code == 409

            # Unidad no existe -> 404
            _configurar_overrides(factory, propietario)
            r_404 = await client.post(
                "/api/accesos/pases",
                headers=HEADERS,
                json={"unidad_id": 999, "nombre_visitante": "Visitante", "cedula_visitante": "V-11222333"},
            )
            assert r_404.status_code == 404

            # Propietario sin contrato en unidad_b -> 403
            r_403 = await client.post(
                "/api/accesos/pases",
                headers=HEADERS,
                json={"unidad_id": ctx.unidad_b_id, "nombre_visitante": "Visitante", "cedula_visitante": "V-11222333"},
            )
            assert r_403.status_code == 403

            # Presidente con ventana > 72h -> 400
            ahora = datetime.now(UTC)
            _configurar_overrides(factory, presidente)
            r_400 = await client.post(
                "/api/accesos/pases",
                headers=HEADERS,
                json={
                    "unidad_id": ctx.unidad_a_id,
                    "nombre_visitante": "Visitante",
                    "cedula_visitante": "V-11222333",
                    "valido_desde": ahora.isoformat(),
                    "valido_hasta": (ahora + timedelta(hours=90)).isoformat(),
                },
            )
            assert r_400.status_code == 400
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_listar_mis_pases_y_revocar_pase() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        ahora = datetime.now(UTC)
        async with factory() as seed_db:
            pase_activo = PaseVisita(
                jti="jti-10",
                unidad_id=ctx.unidad_a_id,
                creado_por_id=ctx.propietario_id,
                nombre_visitante="Ana López",
                cedula_visitante="V-20111222",
                placa_vehiculo=None,
                modalidad="UNICO_USO",
                valido_desde=(ahora - timedelta(hours=5)).replace(tzinfo=None),
                valido_hasta=(ahora - timedelta(hours=1)).replace(tzinfo=None),  # ya vencido -> EXPIRADO dinámico
                estado="ACTIVO",
                firma_hmac="a" * 64,
            )
            seed_db.add(pase_activo)
            await seed_db.commit()
            pase_id = pase_activo.id

        propietario = await _cargar_usuario(factory, ctx.propietario_id)
        inquilino = await _cargar_usuario(factory, ctx.inquilino_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            _configurar_overrides(factory, propietario)
            r_list = await client.get("/api/accesos/pases/mios")
            assert r_list.status_code == 200
            assert r_list.json()[0]["estado"] == "EXPIRADO"

            # Revocar: no encontrado -> 404
            assert (await client.delete("/api/accesos/pases/999")).status_code == 404

            # Revocar: otro ocupante no creador -> 403
            _configurar_overrides(factory, inquilino)
            assert (await client.delete(f"/api/accesos/pases/{pase_id}")).status_code == 403

            # Revocar exitoso por el creador -> 200 REVOCADO
            _configurar_overrides(factory, propietario)
            r_del = await client.delete(f"/api/accesos/pases/{pase_id}")
            assert r_del.status_code == 200
            assert r_del.json()["estado"] == "REVOCADO"
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_verificar_pase_qr_en_garita_flujo_completo_y_anti_replay() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        ahora = datetime.now(UTC)
        desde = ahora - timedelta(minutes=10)
        hasta = ahora + timedelta(hours=4)
        exp_unix = int(hasta.timestamp())
        qr_key = get_qr_signing_key()

        jti_ok = "550e8400-e29b-41d4-a716-446655440111"
        sig_ok = generar_firma_pase_qr(jti_ok, ctx.unidad_a_id, "UNICO_USO", exp_unix, qr_key)
        qr_token = construir_token_pase_qr(jti_ok, ctx.unidad_a_id, "UNICO_USO", exp_unix, sig_ok)

        jti_rev = "550e8400-e29b-41d4-a716-446655440112"
        sig_rev = generar_firma_pase_qr(jti_rev, ctx.unidad_a_id, "UNICO_USO", exp_unix, qr_key)
        qr_token_rev = construir_token_pase_qr(jti_rev, ctx.unidad_a_id, "UNICO_USO", exp_unix, sig_rev)

        hasta_venc = ahora - timedelta(minutes=1)
        exp_venc = int(hasta_venc.timestamp())
        jti_exp = "550e8400-e29b-41d4-a716-446655440113"
        sig_exp = generar_firma_pase_qr(jti_exp, ctx.unidad_a_id, "UNICO_USO", exp_venc, qr_key)
        qr_token_exp = construir_token_pase_qr(jti_exp, ctx.unidad_a_id, "UNICO_USO", exp_venc, sig_exp)

        async with factory() as seed_db:
            pase_ok = PaseVisita(
                jti=jti_ok,
                unidad_id=ctx.unidad_a_id,
                creado_por_id=ctx.propietario_id,
                nombre_visitante="Técnico Fibra",
                cedula_visitante="V-15000111",
                placa_vehiculo="XYZ-999",
                modalidad="UNICO_USO",
                valido_desde=desde,
                valido_hasta=hasta,
                estado="ACTIVO",
                firma_hmac=sig_ok,
            )
            pase_rev = PaseVisita(
                jti=jti_rev,
                unidad_id=ctx.unidad_a_id,
                creado_por_id=ctx.propietario_id,
                nombre_visitante="Visita Revocada",
                cedula_visitante="V-15000112",
                modalidad="UNICO_USO",
                valido_desde=desde,
                valido_hasta=hasta,
                estado="REVOCADO",
                firma_hmac=sig_rev,
            )
            pase_exp = PaseVisita(
                jti=jti_exp,
                unidad_id=ctx.unidad_a_id,
                creado_por_id=ctx.propietario_id,
                nombre_visitante="Visita Expirada",
                cedula_visitante="V-15000113",
                modalidad="UNICO_USO",
                valido_desde=desde - timedelta(hours=2),
                valido_hasta=hasta_venc,
                estado="ACTIVO",
                firma_hmac=sig_exp,
            )
            seed_db.add_all([pase_ok, pase_rev, pase_exp])
            await seed_db.commit()
            pase_exp_id = pase_exp.id

        conserje = await _cargar_usuario(factory, ctx.conserje_id)
        _configurar_overrides(factory, conserje)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Primer escaneo por CONSERJE -> 200 OK y pasa a USADO
            r_scan1 = await client.post("/api/accesos/verificar-qr", headers=HEADERS, json={"qr_token": qr_token})
            assert r_scan1.status_code == 200
            assert r_scan1.json()["autorizado"] is True
            assert r_scan1.json()["estado"] == "USADO"

            # 2. Segundo escaneo del mismo pase (Anti-Replay) -> 409 Conflict
            r_scan2 = await client.post("/api/accesos/verificar-qr", headers=HEADERS, json={"qr_token": qr_token})
            assert r_scan2.status_code == 409
            assert "único uso ya fue utilizado" in r_scan2.json()["detail"]

            # 3. Pase revocado -> 409 Conflict
            r_rev = await client.post("/api/accesos/verificar-qr", headers=HEADERS, json={"qr_token": qr_token_rev})
            assert r_rev.status_code == 409
            assert "revocado" in r_rev.json()["detail"]

            # 4. Pase vencido -> 409 Conflict y marca EXPIRADO en SQLite
            r_exp = await client.post("/api/accesos/verificar-qr", headers=HEADERS, json={"qr_token": qr_token_exp})
            assert r_exp.status_code == 409
            async with factory() as check_db:
                pase_exp_bd = await check_db.get(PaseVisita, pase_exp_id)
                assert pase_exp_bd is not None
                assert pase_exp_bd.estado == "EXPIRADO"

            # 5. Firma adulterada -> 400 Bad Request
            r_bad = await client.post(
                "/api/accesos/verificar-qr",
                headers=HEADERS,
                json={"qr_token": qr_token[:-4] + "ffff"},
            )
            assert r_bad.status_code == 400
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_verificar_pase_qr_casos_borde_adicionales() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        ahora = datetime.now(UTC)
        hasta = ahora + timedelta(hours=2)
        exp_unix = int(hasta.timestamp())
        jti = "550e8400-e29b-41d4-a716-446655440222"
        sig = generar_firma_pase_qr(jti, ctx.unidad_a_id, "UNICO_USO", exp_unix, get_qr_signing_key())
        qr_token = construir_token_pase_qr(jti, ctx.unidad_a_id, "UNICO_USO", exp_unix, sig)

        conserje = await _cargar_usuario(factory, ctx.conserje_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # Idempotency duplicada -> 409
            _configurar_overrides(factory, conserje, redis_new=False)
            assert (
                await client.post("/api/accesos/verificar-qr", headers=HEADERS, json={"qr_token": qr_token})
            ).status_code == 409

            # Pase no existe en DB -> 400
            _configurar_overrides(factory, conserje)
            assert (
                await client.post("/api/accesos/verificar-qr", headers=HEADERS, json={"qr_token": qr_token})
            ).status_code == 400

            # Condición de carrera en burn_qr_nonce (set NX devuelve False en el segundo check) -> 409
            async with factory() as seed_db:
                seed_db.add(
                    PaseVisita(
                        jti=jti,
                        unidad_id=ctx.unidad_a_id,
                        creado_por_id=ctx.propietario_id,
                        nombre_visitante="Visitante",
                        cedula_visitante="V-15000222",
                        modalidad="UNICO_USO",
                        valido_desde=ahora - timedelta(minutes=5),
                        valido_hasta=hasta,
                        estado="ACTIVO",
                        firma_hmac=sig,
                    )
                )
                await seed_db.commit()

            mock_redis = _configurar_overrides(factory, conserje)
            mock_redis.set.side_effect = [True, False]  # 1ro idempotencia OK, 2do burn_qr_nonce falla
            r_race = await client.post("/api/accesos/verificar-qr", headers=HEADERS, json={"qr_token": qr_token})
            assert r_race.status_code == 409
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


# ==============================================================================
# 3. ENDPOINTS DE PAQUETERÍA EN GARITA (/api/paqueteria/*)
# ==============================================================================


async def test_registrar_listar_y_entregar_paqueteria() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        conserje = await _cargar_usuario(factory, ctx.conserje_id)
        propietario = await _cargar_usuario(factory, ctx.propietario_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Registrar paquete con notificación a ocupantes de unidad_a
            mock_redis = _configurar_overrides(factory, conserje)
            r_reg = await client.post(
                "/api/paqueteria/registrar",
                headers=HEADERS,
                json={
                    "unidad_id": ctx.unidad_a_id,
                    "empresa_envio": "zoom",
                    "descripcion": "Caja mediana MercadoLibre",
                    "url_foto_evidencia": "s3://condominio-media/paquetes/foto1.avif",
                },
            )
            assert r_reg.status_code == 201
            paquete_id = r_reg.json()["id"]
            assert r_reg.json()["empresa_envio"] == "ZOOM"
            assert r_reg.json()["estado"] == "EN_GARITA"
            mock_redis.rpush.assert_called_once()

            # 2. Listar paquetería como CONSERJE (ve todos) y como PROPIETARIO (filtrado por su unidad)
            r_list_c = await client.get("/api/paqueteria")
            assert r_list_c.status_code == 200
            assert len(r_list_c.json()) == 1

            _configurar_overrides(factory, propietario)
            r_list_p = await client.get("/api/paqueteria")
            assert r_list_p.status_code == 200
            assert len(r_list_p.json()) == 1

            # 3. Confirmar entrega por propietario destinatario -> 200 ENTREGADO
            r_ent = await client.put(f"/api/paqueteria/{paquete_id}/entregar", headers=HEADERS)
            assert r_ent.status_code == 200
            assert r_ent.json()["estado"] == "ENTREGADO"

            # 4. Intentar entregar paquete ya entregado -> 409 Conflict
            _configurar_overrides(factory, conserje)
            r_ent_dup = await client.put(f"/api/paqueteria/{paquete_id}/entregar", headers=HEADERS)
            assert r_ent_dup.status_code == 409
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_paqueteria_errores_ssrf_permisos_y_404() -> None:
    engine, factory, ctx = await _preparar_entorno()
    try:
        async with factory() as seed_db:
            unidad_sin_ocupantes = Unidad(
                condominio_id=1,
                estructura_id=ctx.estructura_id,
                identificador="3-C",
            )
            paquete_ajeno = PaqueteRecibido(
                unidad_id=ctx.unidad_a_id,
                recibido_por_id=ctx.conserje_id,
                empresa_envio="MRW",
                descripcion="Sobre",
                estado="EN_GARITA",
                fecha_recepcion=datetime.now(UTC),
            )
            seed_db.add_all([unidad_sin_ocupantes, paquete_ajeno])
            await seed_db.commit()
            unidad_libre_id = unidad_sin_ocupantes.id
            paquete_ajeno_id = paquete_ajeno.id

        conserje = await _cargar_usuario(factory, ctx.conserje_id)
        inquilino = await _cargar_usuario(factory, ctx.inquilino_id)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # Idempotency duplicada -> 409
            _configurar_overrides(factory, conserje, redis_new=False)
            r_dup = await client.post(
                "/api/paqueteria/registrar",
                headers=HEADERS,
                json={"unidad_id": ctx.unidad_a_id, "empresa_envio": "MRW", "descripcion": "Sobre"},
            )
            assert r_dup.status_code == 409

            # URL HTTP interna bloqueada por Anti-SSRF -> 400
            _configurar_overrides(factory, conserje)
            with patch(
                "src.routers.accesos.validate_safe_outgoing_url_async",
                side_effect=ValueError("SSRF bloqueado"),
            ):
                r_ssrf = await client.post(
                    "/api/paqueteria/registrar",
                    headers=HEADERS,
                    json={
                        "unidad_id": ctx.unidad_a_id,
                        "empresa_envio": "MRW",
                        "descripcion": "Sobre",
                        "url_foto_evidencia": "http://127.0.0.1/internal.png",
                    },
                )
                assert r_ssrf.status_code == 400

            # Registrar paquete sin ocupantes en la unidad -> 201 sin encolar correo
            mock_redis = _configurar_overrides(factory, conserje)
            r_sin_ocup = await client.post(
                "/api/paqueteria/registrar",
                headers=HEADERS,
                json={"unidad_id": unidad_libre_id, "empresa_envio": "TEALCA", "descripcion": "Paquete sin ocupante"},
            )
            assert r_sin_ocup.status_code == 201
            mock_redis.rpush.assert_not_called()

            # Entregar paquete inexistente -> 404
            assert (await client.put("/api/paqueteria/999/entregar", headers=HEADERS)).status_code == 404

            # Entregar paquete por ocupante de otra unidad -> 403
            _configurar_overrides(factory, inquilino)
            assert (
                await client.put(f"/api/paqueteria/{paquete_ajeno_id}/entregar", headers=HEADERS)
            ).status_code == 403

        async with factory() as check_db:
            res = await check_db.execute(select(PaqueteRecibido).where(PaqueteRecibido.unidad_id == unidad_libre_id))
            assert res.scalars().first() is not None
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
