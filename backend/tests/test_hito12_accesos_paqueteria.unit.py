"""Pruebas unitarias Nivel 11X para el Hito 12: Pases de Visita QR (HMAC-SHA256 + KeyDB Anti-Replay) y Paquetería."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

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
from src.security import SECRET_KEY

HEADERS = {"Idempotency-Key": "018f4a12-1212-7000-8000-000000001212"}


class FakeUser:
    def __init__(self, user_id: int = 1, rol: str = "RESIDENTE", es_activo: bool = True) -> None:
        self.id = user_id
        self.correo = f"{rol.lower()}_{user_id}@condominio.test"
        self.rol = rol
        self.es_activo = es_activo


def _result(value: Any) -> MagicMock:
    res = MagicMock()
    res.scalars().first.return_value = value
    return res


def _result_list(values: list[Any]) -> MagicMock:
    res = MagicMock()
    res.scalars().all.return_value = values
    return res


def _mock_session(*results: Any) -> AsyncMock:
    session = AsyncMock()
    session.execute.side_effect = list(results)
    added: list[Any] = []

    def _add(obj: Any) -> None:
        if getattr(obj, "id", None) is None:
            obj.id = 100 + len(added)
        added.append(obj)

    session.add = MagicMock(side_effect=_add)

    async def _refresh(instance: Any, *args: object, **kwargs: object) -> None:
        if getattr(instance, "id", None) is None:
            instance.id = 200

    session.refresh = _refresh
    return session


def _setup(session: AsyncMock, user: FakeUser | None = None, redis_new: bool = True) -> AsyncMock:
    mock_redis = AsyncMock()
    mock_redis.set.return_value = redis_new
    mock_redis.get.return_value = None
    mock_redis.rpush = AsyncMock(return_value=1)
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_redis_client] = lambda: mock_redis
    app.dependency_overrides[get_current_user] = lambda: user or FakeUser()
    return mock_redis


# ==============================================================================
# 1. CRIPTOGRAFÍA HMAC-SHA256 DE PASES QR Y ANTI-REPLAY KEYDB
# ==============================================================================


def test_pase_qr_claims_firma_y_verificacion_exitosa() -> None:
    jti = "550e8400-e29b-41d4-a716-446655440000"
    exp = 1800000000
    claims = construir_claims_pase_qr(jti, 7, "UNICO_USO", exp)
    assert claims == f"QR|v1|{jti}|7|UNICO_USO|{exp}"

    sig = generar_firma_pase_qr(jti, 7, "UNICO_USO", exp, SECRET_KEY)
    assert len(sig) == 64

    token = construir_token_pase_qr(jti, 7, "UNICO_USO", exp, sig)
    jti_out, uid_out, mod_out, exp_out, sig_out = decodificar_y_verificar_token_pase_qr(token, SECRET_KEY)
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
        decodificar_y_verificar_token_pase_qr(token_invalido, SECRET_KEY)


def test_decodificar_pase_qr_firma_adulterada() -> None:
    jti = "550e8400-e29b-41d4-a716-446655440099"
    sig = generar_firma_pase_qr(jti, 3, "UNICO_USO", 1800000000, SECRET_KEY)
    token = construir_token_pase_qr(jti, 3, "UNICO_USO", 1800000000, "0" * len(sig))
    with pytest.raises(ErrorFinanciero, match="Firma criptográfica de pase QR inválida"):
        decodificar_y_verificar_token_pase_qr(token, SECRET_KEY)


@pytest.mark.anyio
async def test_redis_qr_nonce_helpers() -> None:
    assert build_qr_nonce_key(" abc-123 ") == "qr_used:abc-123"
    assert await burn_qr_nonce(None, "abc-123") is True
    assert await is_qr_nonce_burned(None, "abc-123") is False

    mock_redis = AsyncMock()
    mock_redis.set.return_value = True
    mock_redis.get.return_value = "1"
    assert await burn_qr_nonce(mock_redis, "abc-123", ttl_seconds=300) is True
    assert await is_qr_nonce_burned(mock_redis, "abc-123") is True

    mock_redis.get.side_effect = RuntimeError("KeyDB offline")
    assert await is_qr_nonce_burned(mock_redis, "abc-123") is False


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


def test_crear_pase_visita_exitoso_y_fantasma_bloqueado(client: TestClient) -> None:
    try:
        # 1. Fantasma bloqueado con 403
        _setup(_mock_session(), FakeUser(user_id=9, rol="FANTASMA", es_activo=False))
        r_ghost = client.post(
            "/api/accesos/pases",
            headers=HEADERS,
            json={
                "unidad_id": 1,
                "nombre_visitante": "Carlos Visitante",
                "cedula_visitante": "V-19888777",
            },
        )
        assert r_ghost.status_code == 403

        # 2. Residente con unidad activa crea pase exitosamente
        unidad = Unidad(id=1, estructura_id=1, identificador="PB-01")
        session = _mock_session(_result(unidad), _result_list([1]))
        _setup(session, FakeUser(user_id=2, rol="RESIDENTE"))
        r_ok = client.post(
            "/api/accesos/pases",
            headers=HEADERS,
            json={
                "unidad_id": 1,
                "nombre_visitante": "Carlos Visitante",
                "cedula_visitante": "v-19888777",
                "placa_vehiculo": "ab123cd",
                "modalidad": "UNICO_USO",
                "horas_validez": 12,
            },
        )
        assert r_ok.status_code == 201
        body = r_ok.json()
        assert body["identificador_unidad"] == "PB-01"
        assert body["cedula_visitante"] == "V-19888777"
        assert body["placa_vehiculo"] == "AB123CD"
        assert "." in body["qr_token"]
    finally:
        app.dependency_overrides.clear()


def test_crear_pase_visita_errores_idempotencia_contrato_y_ventana(client: TestClient) -> None:
    try:
        # Idempotency duplicada -> 409
        _setup(_mock_session(), FakeUser(user_id=2, rol="RESIDENTE"), redis_new=False)
        r_dup = client.post(
            "/api/accesos/pases",
            headers=HEADERS,
            json={"unidad_id": 1, "nombre_visitante": "Visitante", "cedula_visitante": "V-11222333"},
        )
        assert r_dup.status_code == 409

        # Unidad no existe -> 404
        _setup(_mock_session(_result(None)), FakeUser(user_id=2, rol="RESIDENTE"))
        r_404 = client.post(
            "/api/accesos/pases",
            headers=HEADERS,
            json={"unidad_id": 99, "nombre_visitante": "Visitante", "cedula_visitante": "V-11222333"},
        )
        assert r_404.status_code == 404

        # Residente sin contrato en unidad -> 403
        unidad = Unidad(id=1, estructura_id=1, identificador="PB-01")
        _setup(_mock_session(_result(unidad), _result_list([2])), FakeUser(user_id=2, rol="RESIDENTE"))
        r_403 = client.post(
            "/api/accesos/pases",
            headers=HEADERS,
            json={"unidad_id": 1, "nombre_visitante": "Visitante", "cedula_visitante": "V-11222333"},
        )
        assert r_403.status_code == 403

        # Presidente con ventana > 72h -> 400
        ahora = datetime.now(UTC)
        _setup(_mock_session(_result(unidad)), FakeUser(user_id=1, rol="PRESIDENTE"))
        r_400 = client.post(
            "/api/accesos/pases",
            headers=HEADERS,
            json={
                "unidad_id": 1,
                "nombre_visitante": "Visitante",
                "cedula_visitante": "V-11222333",
                "valido_desde": ahora.isoformat(),
                "valido_hasta": (ahora + timedelta(hours=90)).isoformat(),
            },
        )
        assert r_400.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_listar_mis_pases_y_revocar_pase(client: TestClient) -> None:
    try:
        ahora = datetime.now(UTC)
        pase_activo = PaseVisita(
            id=10,
            jti="jti-10",
            unidad_id=1,
            creado_por_id=2,
            nombre_visitante="Ana López",
            cedula_visitante="V-20111222",
            placa_vehiculo=None,
            modalidad="UNICO_USO",
            valido_desde=(ahora - timedelta(hours=5)).replace(tzinfo=None),
            valido_hasta=(ahora - timedelta(hours=1)).replace(tzinfo=None),  # ya vencido -> EXPIRADO dinámico
            estado="ACTIVO",
            firma_hmac="a" * 64,
        )
        unidad = Unidad(id=1, estructura_id=1, identificador="1-A")
        session = _mock_session(_result_list([pase_activo]), _result_list([1]), _result_list([unidad]))
        _setup(session, FakeUser(user_id=2, rol="RESIDENTE"))
        r_list = client.get("/api/accesos/pases/mios")
        assert r_list.status_code == 200
        assert r_list.json()[0]["estado"] == "EXPIRADO"

        # Revocar: no encontrado -> 404
        _setup(_mock_session(_result(None)), FakeUser(user_id=2, rol="RESIDENTE"))
        assert client.delete("/api/accesos/pases/999").status_code == 404

        # Revocar: otro residente no creador -> 403
        _setup(_mock_session(_result(pase_activo)), FakeUser(user_id=99, rol="RESIDENTE"))
        assert client.delete("/api/accesos/pases/10").status_code == 403

        # Revocar exitoso por el creador -> 200 REVOCADO
        _setup(_mock_session(_result(pase_activo), _result(unidad)), FakeUser(user_id=2, rol="RESIDENTE"))
        r_del = client.delete("/api/accesos/pases/10")
        assert r_del.status_code == 200
        assert r_del.json()["estado"] == "REVOCADO"
    finally:
        app.dependency_overrides.clear()


def test_verificar_pase_qr_en_garita_flujo_completo_y_anti_replay(client: TestClient) -> None:
    try:
        ahora = datetime.now(UTC)
        desde = ahora - timedelta(minutes=10)
        hasta = ahora + timedelta(hours=4)
        exp_unix = int(hasta.timestamp())
        jti = "550e8400-e29b-41d4-a716-446655440111"
        sig = generar_firma_pase_qr(jti, 1, "UNICO_USO", exp_unix, SECRET_KEY)
        qr_token = construir_token_pase_qr(jti, 1, "UNICO_USO", exp_unix, sig)

        pase = PaseVisita(
            id=50,
            jti=jti,
            unidad_id=1,
            creado_por_id=2,
            nombre_visitante="Técnico Fibra",
            cedula_visitante="V-15000111",
            placa_vehiculo="XYZ-999",
            modalidad="UNICO_USO",
            valido_desde=desde,
            valido_hasta=hasta,
            estado="ACTIVO",
            firma_hmac=sig,
        )
        unidad = Unidad(id=1, estructura_id=1, identificador="PH-1")

        # 1. Primer escaneo por CONSERJE -> 200 OK y pasa a USADO
        session_ok = _mock_session(_result(pase), _result(unidad))
        _setup(session_ok, FakeUser(user_id=5, rol="CONSERJE"))
        r_scan1 = client.post("/api/accesos/verificar-qr", headers=HEADERS, json={"qr_token": qr_token})
        assert r_scan1.status_code == 200
        assert r_scan1.json()["autorizado"] is True
        assert r_scan1.json()["estado"] == "USADO"

        # 2. Segundo escaneo del mismo pase (Anti-Replay) -> 409 Conflict
        session_replay = _mock_session(_result(pase))
        _setup(session_replay, FakeUser(user_id=5, rol="CONSERJE"))
        r_scan2 = client.post("/api/accesos/verificar-qr", headers=HEADERS, json={"qr_token": qr_token})
        assert r_scan2.status_code == 409
        assert "único uso ya fue utilizado" in r_scan2.json()["detail"]

        # 3. Pase revocado -> 409 Conflict
        pase.estado = "REVOCADO"
        _setup(_mock_session(_result(pase)), FakeUser(user_id=5, rol="CONSERJE"))
        r_rev = client.post("/api/accesos/verificar-qr", headers=HEADERS, json={"qr_token": qr_token})
        assert r_rev.status_code == 409
        assert "revocado" in r_rev.json()["detail"]

        # 4. Pase vencido -> 409 Conflict y marca EXPIRADO
        pase.estado = "ACTIVO"
        pase.valido_hasta = ahora - timedelta(minutes=1)
        _setup(_mock_session(_result(pase)), FakeUser(user_id=5, rol="CONSERJE"))
        r_exp = client.post("/api/accesos/verificar-qr", headers=HEADERS, json={"qr_token": qr_token})
        assert r_exp.status_code == 409
        assert pase.estado == "EXPIRADO"

        # 5. Firma adulterada -> 400 Bad Request
        _setup(_mock_session(), FakeUser(user_id=5, rol="CONSERJE"))
        r_bad = client.post(
            "/api/accesos/verificar-qr",
            headers=HEADERS,
            json={"qr_token": qr_token[:-4] + "ffff"},
        )
        assert r_bad.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_verificar_pase_qr_casos_borde_adicionales(client: TestClient) -> None:
    try:
        ahora = datetime.now(UTC)
        hasta = ahora + timedelta(hours=2)
        exp_unix = int(hasta.timestamp())
        jti = "550e8400-e29b-41d4-a716-446655440222"
        sig = generar_firma_pase_qr(jti, 1, "UNICO_USO", exp_unix, SECRET_KEY)
        qr_token = construir_token_pase_qr(jti, 1, "UNICO_USO", exp_unix, sig)

        # Idempotency duplicada -> 409
        _setup(_mock_session(), FakeUser(user_id=5, rol="CONSERJE"), redis_new=False)
        assert client.post("/api/accesos/verificar-qr", headers=HEADERS, json={"qr_token": qr_token}).status_code == 409

        # Pase no existe en DB -> 400
        _setup(_mock_session(_result(None)), FakeUser(user_id=5, rol="CONSERJE"))
        assert client.post("/api/accesos/verificar-qr", headers=HEADERS, json={"qr_token": qr_token}).status_code == 400

        # Condición de carrera en burn_qr_nonce (set NX devuelve False en el segundo check) -> 409
        pase = PaseVisita(
            id=51,
            jti=jti,
            unidad_id=1,
            creado_por_id=2,
            nombre_visitante="Visitante",
            cedula_visitante="V-15000222",
            modalidad="UNICO_USO",
            valido_desde=ahora - timedelta(minutes=5),
            valido_hasta=hasta,
            estado="ACTIVO",
            firma_hmac=sig,
        )
        mock_redis = _setup(_mock_session(_result(pase)), FakeUser(user_id=5, rol="CONSERJE"))
        mock_redis.set.side_effect = [True, False]  # 1ro idempotencia OK, 2do burn_qr_nonce falla
        r_race = client.post("/api/accesos/verificar-qr", headers=HEADERS, json={"qr_token": qr_token})
        assert r_race.status_code == 409
    finally:
        app.dependency_overrides.clear()


# ==============================================================================
# 3. ENDPOINTS DE PAQUETERÍA EN GARITA (/api/paqueteria/*)
# ==============================================================================


def test_registrar_listar_y_entregar_paqueteria(client: TestClient) -> None:
    try:
        unidad = Unidad(id=1, estructura_id=1, identificador="2-B")

        # 1. Registrar paquete con notificación a ocupantes
        session_reg = _mock_session(
            _result(unidad),
            _result_list([2]),
            _result_list(["residente2@condominio.test"]),
        )
        mock_redis = _setup(session_reg, FakeUser(user_id=5, rol="CONSERJE"))
        r_reg = client.post(
            "/api/paqueteria/registrar",
            headers=HEADERS,
            json={
                "unidad_id": 1,
                "empresa_envio": "zoom",
                "descripcion": "Caja mediana MercadoLibre",
                "url_foto_evidencia": "s3://condominio-media/paquetes/foto1.avif",
            },
        )
        assert r_reg.status_code == 201
        assert r_reg.json()["empresa_envio"] == "ZOOM"
        assert r_reg.json()["estado"] == "EN_GARITA"
        mock_redis.rpush.assert_called_once()

        # 2. Listar paquetería como CONSERJE (ve todos) y como RESIDENTE (filtrado por su unidad)
        paquete = PaqueteRecibido(
            id=70,
            unidad_id=1,
            recibido_por_id=5,
            empresa_envio="ZOOM",
            descripcion="Caja mediana",
            url_foto_evidencia=None,
            estado="EN_GARITA",
            fecha_recepcion=datetime.now(UTC),
        )
        _setup(_mock_session(_result_list([paquete]), _result_list([unidad])), FakeUser(user_id=5, rol="CONSERJE"))
        r_list_c = client.get("/api/paqueteria")
        assert r_list_c.status_code == 200
        assert len(r_list_c.json()) == 1

        _setup(
            _mock_session(_result_list([paquete]), _result_list([unidad]), _result_list([1])),
            FakeUser(user_id=2, rol="RESIDENTE"),
        )
        r_list_r = client.get("/api/paqueteria")
        assert r_list_r.status_code == 200
        assert len(r_list_r.json()) == 1

        # 3. Confirmar entrega por residente destinatario -> 200 ENTREGADO
        _setup(
            _mock_session(_result(paquete), _result_list([1]), _result(unidad)),
            FakeUser(user_id=2, rol="RESIDENTE"),
        )
        r_ent = client.put("/api/paqueteria/70/entregar")
        assert r_ent.status_code == 200
        assert r_ent.json()["estado"] == "ENTREGADO"

        # 4. Intentar entregar paquete ya entregado -> 409 Conflict
        _setup(_mock_session(_result(paquete)), FakeUser(user_id=5, rol="CONSERJE"))
        r_ent_dup = client.put("/api/paqueteria/70/entregar")
        assert r_ent_dup.status_code == 409
    finally:
        app.dependency_overrides.clear()


def test_paqueteria_errores_ssrf_permisos_y_404(client: TestClient) -> None:
    try:
        # Idempotency duplicada -> 409
        _setup(_mock_session(), FakeUser(user_id=5, rol="CONSERJE"), redis_new=False)
        r_dup = client.post(
            "/api/paqueteria/registrar",
            headers=HEADERS,
            json={"unidad_id": 1, "empresa_envio": "MRW", "descripcion": "Sobre"},
        )
        assert r_dup.status_code == 409

        # URL HTTP interna bloqueada por Anti-SSRF -> 400
        _setup(_mock_session(), FakeUser(user_id=5, rol="CONSERJE"))
        with patch("src.routers.accesos.validate_safe_outgoing_url", side_effect=ValueError("SSRF bloqueado")):
            r_ssrf = client.post(
                "/api/paqueteria/registrar",
                headers=HEADERS,
                json={
                    "unidad_id": 1,
                    "empresa_envio": "MRW",
                    "descripcion": "Sobre",
                    "url_foto_evidencia": "http://127.0.0.1/internal.png",
                },
            )
            assert r_ssrf.status_code == 400

        # Registrar paquete sin ocupantes en la unidad -> 201 sin encolar correo
        unidad = Unidad(id=1, estructura_id=1, identificador="3-C")
        _setup(_mock_session(_result(unidad), _result_list([])), FakeUser(user_id=5, rol="CONSERJE"))
        r_sin_ocup = client.post(
            "/api/paqueteria/registrar",
            headers=HEADERS,
            json={"unidad_id": 1, "empresa_envio": "TEALCA", "descripcion": "Paquete sin ocupante"},
        )
        assert r_sin_ocup.status_code == 201

        # Entregar paquete inexistente -> 404
        _setup(_mock_session(_result(None)), FakeUser(user_id=5, rol="CONSERJE"))
        assert client.put("/api/paqueteria/999/entregar").status_code == 404

        # Entregar paquete por residente de otra unidad -> 403
        paquete_ajeno = PaqueteRecibido(
            id=71,
            unidad_id=1,
            recibido_por_id=5,
            empresa_envio="MRW",
            descripcion="Sobre",
            estado="EN_GARITA",
            fecha_recepcion=datetime.now(UTC),
        )
        _setup(_mock_session(_result(paquete_ajeno), _result_list([2])), FakeUser(user_id=9, rol="RESIDENTE"))
        assert client.put("/api/paqueteria/71/entregar").status_code == 403
    finally:
        app.dependency_overrides.clear()
