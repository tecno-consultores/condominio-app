from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from src.database import get_db
from src.main import app
from src.models import Usuario
from src.redis_client import get_redis_client, reset_local_security_state
from src.security import (
    create_access_token,
    create_refresh_token,
    generate_csrf_token,
    get_password_hash,
)


@pytest.fixture(autouse=True)
def _limpiar_estado_auth(client: TestClient) -> Any:
    """Aísla las cookies del TestClient compartido y el estado local de Redis en memoria."""
    client.cookies.clear()
    reset_local_security_state()
    yield
    client.cookies.clear()
    app.dependency_overrides = {}
    reset_local_security_state()


def test_register_user_success(client: TestClient) -> None:
    """Simula el registro exitoso aislando la base de datos y Redis"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = None
    mock_session.execute.return_value = mock_result
    mock_session.add = MagicMock()

    async def mock_flush(*args: object, **kwargs: object) -> None:
        pass

    mock_session.flush = mock_flush

    async def mock_refresh(instance: Any, *args: object, **kwargs: object) -> None:
        instance.id = 1

    mock_session.refresh = mock_refresh

    mock_redis = AsyncMock()
    mock_redis.set.return_value = True

    app.dependency_overrides[get_db] = lambda: mock_session
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

    payload = {
        "nombre": "Pedro QA",
        "cedula": "V-9999999",
        "correo": "pedro@test.com",
        "telefono": "12345",
        "password": "Mypassword1!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO",
    }
    headers = {"Idempotency-Key": "123e4567-e89b-12d3-a456-426614174000"}
    response = client.post("/api/auth/register", json=payload, headers=headers)

    assert response.status_code == 201
    assert response.json()["es_activo"] is False
    assert response.json()["rol"] == "FANTASMA"

    app.dependency_overrides = {}


def test_register_user_duplicate_idempotency_key(client: TestClient) -> None:
    """Falla con 409 Conflict si la Idempotency-Key ya fue procesada en Redis"""
    mock_session = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.set.return_value = False

    app.dependency_overrides[get_db] = lambda: mock_session
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

    payload = {
        "nombre": "Pedro Duplicado",
        "cedula": "V-9999999",
        "correo": "pedro@test.com",
        "telefono": "12345",
        "password": "Mypassword1!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO",
    }
    headers = {"Idempotency-Key": "123e4567-e89b-12d3-a456-426614174000"}
    response = client.post("/api/auth/register", json=payload, headers=headers)

    assert response.status_code == 409
    assert "Petición duplicada detectada" in response.json()["detail"]

    app.dependency_overrides = {}


def test_register_user_already_registered(client: TestClient) -> None:
    """Falla con 400 si el usuario (correo o cédula) ya existe en base de datos"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = MagicMock()
    mock_session.execute.return_value = mock_result

    mock_redis = AsyncMock()
    mock_redis.set.return_value = True

    app.dependency_overrides[get_db] = lambda: mock_session
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

    payload = {
        "nombre": "Pedro Ya Existe",
        "cedula": "V-9999999",
        "correo": "pedro@test.com",
        "telefono": "12345",
        "password": "Mypassword1!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO",
    }
    headers = {"Idempotency-Key": "unique-idempotency-key-1"}
    response = client.post("/api/auth/register", json=payload, headers=headers)

    assert response.status_code == 409
    assert "Usuario ya registrado" in response.json()["detail"]

    app.dependency_overrides = {}


def test_register_missing_idempotency_key(client: TestClient) -> None:
    """Falla con 422 si no se envía el header de idempotencia"""
    payload = {
        "nombre": "Pedro QA",
        "cedula": "V-9999999",
        "correo": "pedro@test.com",
        "telefono": "12345",
        "password": "Mypassword1!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


def test_register_user_db_failure(client: TestClient) -> None:
    """Simula una falla catastrófica en la BD durante el registro"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = None
    mock_session.execute.return_value = mock_result
    mock_session.add = MagicMock()
    mock_session.commit.side_effect = Exception("DB Connection Lost")

    mock_redis = AsyncMock()
    mock_redis.set.return_value = True

    app.dependency_overrides[get_db] = lambda: mock_session
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

    payload = {
        "nombre": "Pedro Error",
        "cedula": "V-1111111",
        "correo": "error@test.com",
        "telefono": "123",
        "password": "Mypassword1!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO",
    }
    headers = {"Idempotency-Key": "123e4567-e89b-12d3-a456-426614174001"}
    response = client.post("/api/auth/register", json=payload, headers=headers)

    assert response.status_code == 500
    assert "Error en base de datos" in response.json()["detail"]

    app.dependency_overrides = {}


def test_register_user_integrity_error(client: TestClient) -> None:
    """Un error de integridad en BD se traduce en 400 (dato inválido), nunca en 500"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = None
    mock_session.execute.return_value = mock_result
    mock_session.add = MagicMock()
    mock_session.commit.side_effect = IntegrityError("INSERT usuarios", {}, Exception("duplicado"))

    mock_redis = AsyncMock()
    mock_redis.set.return_value = True

    app.dependency_overrides[get_db] = lambda: mock_session
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

    payload = {
        "nombre": "Pedro Integridad",
        "cedula": "V-2222222",
        "correo": "integridad@test.com",
        "telefono": "123",
        "password": "Mypassword1!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO",
    }
    headers = {"Idempotency-Key": "integridad-key-1"}
    response = client.post("/api/auth/register", json=payload, headers=headers)

    assert response.status_code == 400
    assert "Datos inválidos o duplicados" in response.json()["detail"]

    app.dependency_overrides = {}


def test_login_set_httponly_cookie(client: TestClient) -> None:
    """Simula un login exitoso validando la creación de la cookie HttpOnly"""
    mock_session = AsyncMock()
    mock_result = MagicMock()

    class FakeUser:
        id: int = 1
        correo: str = "admin@test.com"
        rol: str = "PRESIDENTE"
        password_hash: str = get_password_hash("secure")

    mock_result.scalars().first.return_value = FakeUser()
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_session

    payload = {"correo": "admin@test.com", "password": "secure"}
    response = client.post("/api/auth/login", json=payload)

    assert response.status_code == 200
    if hasattr(response.headers, "get_list"):
        cookies = response.headers.get_list("set-cookie")
    else:
        raw = response.headers.get("set-cookie", "")
        cookies = [raw] if raw else []
    assert any("access_token" in c and "HttpOnly" in c for c in cookies)

    app.dependency_overrides = {}


def test_login_invalid_credentials(client: TestClient) -> None:
    """Simula un login con credenciales erróneas devolviendo 401"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = None
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_session

    payload = {"correo": "noexiste@test.com", "password": "wrong"}
    response = client.post("/api/auth/login", json=payload)

    assert response.status_code == 401
    assert "Credenciales inválidas" in response.json()["detail"]

    app.dependency_overrides = {}


def test_me_without_cookie_fails(client: TestClient) -> None:
    """Llamada a /api/auth/me sin cookie debe responder 401"""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "No autenticado" in response.json()["detail"]


def test_me_with_valid_token_success(client: TestClient) -> None:
    """Llamada a /api/auth/me con token válido y usuario en base de datos"""
    token = create_access_token(data={"sub": "pedro@test.com", "rol": "FANTASMA", "id": 5})

    mock_session = AsyncMock()
    mock_result = MagicMock()

    class FakeUser:
        id: int = 5
        correo: str = "pedro@test.com"
        nombre: str = "Pedro QA"
        rol: str = "FANTASMA"
        es_activo: bool = False

    mock_result.scalars().first.return_value = FakeUser()
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_session

    client.cookies.set("access_token", f"Bearer {token}")
    response = client.get("/api/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 5
    assert data["correo"] == "pedro@test.com"
    assert data["rol"] == "FANTASMA"
    assert data["es_activo"] is False

    client.cookies.clear()
    app.dependency_overrides = {}


def test_me_with_expired_token(client: TestClient) -> None:
    """Llamada a /api/auth/me con token expirado debe responder 401"""
    expired_token = create_access_token(data={"sub": "expired@test.com"}, expires_delta=timedelta(seconds=-10))

    client.cookies.set("access_token", f"Bearer {expired_token}")
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert "Token expirado" in response.json()["detail"]

    client.cookies.clear()


def test_me_with_invalid_token(client: TestClient) -> None:
    """Llamada a /api/auth/me con token adulterado/inválido debe responder 401"""
    client.cookies.set("access_token", "Bearer token_completamente_invalido")
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert "Token inválido" in response.json()["detail"]

    client.cookies.clear()


def test_logout_revokes_session_and_clears_cookies(client: TestClient) -> None:
    """POST /api/auth/logout revoca user/sid/jti en KeyDB, purga cookies y emite Clear-Site-Data."""
    mock_redis = AsyncMock()
    mock_redis.set.return_value = True
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

    access = create_access_token({"sub": "logout@test.com", "rol": "PROPIETARIO", "id": 77, "sid": "sid-logout-1"})
    refresh = create_refresh_token({"sub": "logout@test.com", "id": 77, "sid": "sid-logout-1"})
    client.cookies.set("access_token", f"Bearer {access}")
    client.cookies.set("refresh_token", refresh)

    res = client.post("/api/auth/logout")
    assert res.status_code == 200
    assert res.json()["message"] == "Sesión cerrada exitosamente"
    assert res.headers.get("clear-site-data") == '"cookies", "storage", "cache"'
    assert mock_redis.set.await_count >= 3


def test_refresh_token_rotation_grace_period_and_replay(client: TestClient) -> None:
    """POST /api/auth/refresh rota refresh_token, soporta grace period 5s y revoca en replay tardío."""
    res_missing = client.post("/api/auth/refresh")
    assert res_missing.status_code == 401

    expired_refresh = create_refresh_token(
        {"sub": "ref@test.com", "id": 15, "sid": "sid-ref-1"},
        expires_delta=timedelta(seconds=-5),
    )
    res_exp = client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {expired_refresh}"})
    assert res_exp.status_code == 401
    assert "expirado" in res_exp.json()["detail"]

    res_bad = client.post("/api/auth/refresh", headers={"Authorization": "Bearer invalido"})
    assert res_bad.status_code == 401

    incomplete_refresh = create_refresh_token({"id": 15, "sid": "sid-no-sub"})
    res_nosub = client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {incomplete_refresh}"})
    assert res_nosub.status_code == 401

    no_jti_access = create_access_token({"sub": "ref@test.com", "id": 15, "sid": "sid-ref-1"})
    res_missing_jti = client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {no_jti_access}"})
    assert res_missing_jti.status_code == 401

    mock_session = AsyncMock()
    mock_result = MagicMock()

    class FakeRefreshUser:
        id: int = 15
        correo: str = "ref@test.com"
        rol: str = "PROPIETARIO"

    mock_result.scalars().first.return_value = FakeRefreshUser()
    mock_session.execute.return_value = mock_result

    kv: dict[str, str] = {}

    class _FakeRedis:
        async def set(self, key: str, value: str, nx: bool = False, ex: int | None = None) -> bool:
            _ = ex
            if nx and key in kv:
                return False
            kv[key] = value
            return True

        async def get(self, key: str) -> str | None:
            return kv.get(key)

    app.dependency_overrides[get_db] = lambda: mock_session
    app.dependency_overrides[get_redis_client] = lambda: _FakeRedis()

    valid_refresh = create_refresh_token({"sub": "ref@test.com", "id": 15, "sid": "sid-ref-1"})
    client.cookies.set("refresh_token", valid_refresh)

    res_ok = client.post("/api/auth/refresh")
    assert res_ok.status_code == 200
    assert res_ok.headers.get("x-csrf-token")

    # Segunda pestaña concurrente aún con el token previo dentro del grace period de 5s
    client.cookies.clear()
    client.cookies.set("refresh_token", valid_refresh)
    res_grace = client.post("/api/auth/refresh")
    assert res_grace.status_code == 200
    assert res_grace.json()["csrf_token"] == res_ok.json()["csrf_token"]

    # Expirado el grace period -> replay tardío revoca usuario/sid y devuelve 401 con Clear-Site-Data
    for key in [k for k in kv if k.startswith("grace_period:")]:
        del kv[key]
    client.cookies.clear()
    client.cookies.set("refresh_token", valid_refresh)
    res_replay = client.post("/api/auth/refresh")
    assert res_replay.status_code == 401
    assert "reutilizado" in res_replay.json()["detail"]
    assert res_replay.headers.get("clear-site-data") == '"cookies", "storage", "cache"'
    assert kv.get("revoked_user:15") == "1"
    assert kv.get("revoked_sid:sid-ref-1") == "1"


def test_me_real_orm_usuario_and_revoked_sid(client: TestClient) -> None:
    """GET /api/auth/me resuelve cedula, telefono, unidad_activa_id y rechaza SID revocado o sin sub."""
    token_no_sub = create_access_token(data={"rol": "PROPIETARIO"})
    client.cookies.set("access_token", f"Bearer {token_no_sub}")
    res_no_sub = client.get("/api/auth/me")
    assert res_no_sub.status_code == 401

    sid_unico = f"sid-rev-{uuid4().hex[:8]}"
    token_revoked = create_access_token(data={"sub": "real@test.com", "id": 22, "sid": sid_unico})
    mock_session = AsyncMock()
    res_user = MagicMock()
    res_user.scalars().first.return_value = Usuario(
        id=22,
        nombre="Real ORM",
        cedula="V-12345678",
        correo="real@test.com",
        telefono="04141234567",
        password_hash="h",
        rol="PROPIETARIO",
        es_activo=True,
    )
    res_unidad = MagicMock()
    res_unidad.scalars().first.return_value = 42
    mock_session.execute.side_effect = [res_user, res_unidad, res_user]

    app.dependency_overrides[get_db] = lambda: mock_session
    client.cookies.set("access_token", f"Bearer {token_revoked}")
    ok_resp = client.get("/api/auth/me")
    assert ok_resp.status_code == 200
    body = ok_resp.json()
    assert body["cedula"] == "V-12345678"
    assert body["telefono"] == "04141234567"
    assert body["unidad_activa_id"] == 42
    assert ok_resp.headers.get("x-csrf-token") == generate_csrf_token(sid_unico)

    # Revocamos mediante logout y validamos rechazo 401 por SID revocado
    mock_session.execute.side_effect = [res_user, res_unidad]
    client.post("/api/auth/logout")
    client.cookies.set("access_token", f"Bearer {token_revoked}")
    revoked_resp = client.get("/api/auth/me")
    assert revoked_resp.status_code == 401


def test_login_lockout_429_and_short_idempotency_key(client: TestClient) -> None:
    """Lockout 429 tras 5 fallos (ip, correo) y rechazo 422 de Idempotency-Key < 8 caracteres."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = None
    mock_session.execute.return_value = mock_result
    app.dependency_overrides[get_db] = lambda: mock_session

    uid = uuid4()
    hdrs = {"X-Forwarded-For": f"203.{uid.bytes[0]}.{uid.bytes[1]}.{uid.bytes[2] % 250 + 1}"}
    correo_brute = f"brute-{uid.hex[:8]}@test.com"
    for _ in range(5):
        r = client.post("/api/auth/login", json={"correo": correo_brute, "password": "wrong"}, headers=hdrs)
        assert r.status_code == 401

    blocked = client.post("/api/auth/login", json={"correo": correo_brute, "password": "wrong"}, headers=hdrs)
    assert blocked.status_code == 429
    assert "Demasiados intentos" in blocked.json()["detail"]

    res_short = client.post(
        "/api/auth/register",
        json={
            "nombre": "Corto",
            "cedula": "V-9991112",
            "correo": "corto@test.com",
            "telefono": "0414",
            "password": "Mypassword1!",
            "unidad_solicitada_id": 1,
            "tipo_ocupante_solicitado": "PROPIETARIO",
        },
        headers={"Idempotency-Key": "short"},
    )
    assert res_short.status_code == 422
