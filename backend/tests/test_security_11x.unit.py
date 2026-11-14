"""Pruebas unitarias de las salvaguardas de seguridad Nivel 11X."""

from __future__ import annotations

import hashlib
import socket
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.database import get_db
from src.main import _es_produccion, app
from src.redis_client import (
    build_idempotency_key,
    check_and_set_idempotency_key,
    clear_login_failures,
    clear_user_session_revocation,
    get_redis_client,
    get_refresh_token_from_grace_period,
    is_login_locked_out,
    is_session_id_revoked,
    is_user_session_revoked,
    mark_refresh_jti_used,
    record_login_failure,
    reset_local_security_state,
    revoke_session_id,
    revoke_user_session,
    rotate_refresh_token_with_grace_period,
)
from src.routers.auth import LoginData
from src.schemas import (
    AlicuotaUpdateRequest,
    CierreMensualRequest,
    EgresoCreate,
    FacturarPeriodoRequest,
    FondoCondominioCreate,
    PagoRechazo,
    PagoReportar,
    ReciboCreate,
    TasaCambioCreate,
    UsuarioCreate,
)
from src.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    DEFAULT_INSECURE_SECRET_KEY,
    FORBIDDEN_CONTAINER_HOSTS,
    MAX_UPLOAD_SIZE_BYTES,
    PBKDF2_ITERATIONS,
    REFRESH_TOKEN_EXPIRE_DAYS,
    UPLOAD_CHUNK_SIZE,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    decode_token_unverified_exp,
    generate_csrf_token,
    get_password_hash,
    is_csrf_enforced,
    read_uploaded_file_safely,
    should_use_secure_cookie,
    validate_csrf_token,
    validate_file_magic_bytes,
    validate_production_security_settings,
    validate_safe_outgoing_url,
    verify_password,
    verify_websocket_origin,
)


class _DummyUpload:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = list(chunks)

    async def read(self, size: int = -1) -> bytes:
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


def test_pbkdf2_password_hash_and_verify() -> None:
    """Genera hashes con sal única y los verifica en tiempo constante."""
    h1 = get_password_hash("ClaveSuperSegura123!")
    h2 = get_password_hash("ClaveSuperSegura123!")
    assert h1.startswith("pbkdf2_sha256$")
    assert h1 != h2
    assert verify_password("ClaveSuperSegura123!", h1) is True
    assert verify_password("OtraClave", h1) is False


def test_verify_password_malformed_pbkdf2_and_legacy() -> None:
    """Rechaza hashes PBKDF2 malformados y rechaza hashes legacy SHA-256 sin sal (Hito 17.1)."""
    assert verify_password("x", "pbkdf2_sha256$solo_dos_partes") is False
    legacy_hash = hashlib.sha256(b"legacy123").hexdigest()
    assert verify_password("legacy123", legacy_hash) is False
    assert verify_password("wrong", legacy_hash) is False
    assert verify_password("x", "") is False


def test_csrf_token_generation_and_validation() -> None:
    """Genera y valida tokens CSRF HMAC-SHA256."""
    token = generate_csrf_token("session-abc-123")
    assert validate_csrf_token(token, "session-abc-123") is True
    assert validate_csrf_token(token, "otra-sesion") is False
    assert validate_csrf_token("token-adulterado", "session-abc-123") is False
    assert validate_csrf_token("", "session-abc-123") is False
    assert validate_csrf_token(token, "") is False


def test_validate_safe_outgoing_url_valid_public_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Permite URLs HTTPS con IP pública resuelta."""
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )
    url = validate_safe_outgoing_url("https://cdn.condominio.example.com/comprobante.avif")
    assert url == "https://cdn.condominio.example.com/comprobante.avif"


@pytest.mark.parametrize(
    "bad_url",
    [
        "ftp://example.com/archivo.avif",
        "javascript:alert(1)",
        "http:///sin-host",
        "http://localhost:8000/health",
        "http://postgres:5432/",
        "http://redis:6379/",
        "http://keydb:6379/",
        "http://minio:9000/bucket",
    ],
)
def test_validate_safe_outgoing_url_rejects_bad_scheme_or_internal_host(bad_url: str) -> None:
    with pytest.raises(ValueError):
        validate_safe_outgoing_url(bad_url)


@pytest.mark.parametrize(
    "forbidden_ip",
    [
        "127.0.0.1",
        "10.0.0.5",
        "172.16.0.10",
        "192.168.1.20",
        "169.254.169.254",
        "224.0.0.1",
        "0.0.0.0",
    ],
)
def test_validate_safe_outgoing_url_rejects_private_and_metadata_ips(
    monkeypatch: pytest.MonkeyPatch, forbidden_ip: str
) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (forbidden_ip, 0))],
    )
    with pytest.raises(ValueError, match="prohibido"):
        validate_safe_outgoing_url("https://webhook.externo.com/callback")


def test_validate_safe_outgoing_url_dns_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail_dns(host: str, port: object) -> Any:
        raise socket.gaierror("DNS fail")

    monkeypatch.setattr(socket, "getaddrinfo", _fail_dns)
    with pytest.raises(ValueError, match="No se pudo resolver"):
        validate_safe_outgoing_url("https://no-existe.dominio.invalido/test")


async def test_read_uploaded_file_safely_within_quota() -> None:
    dummy = _DummyUpload([b"hola ", b"mundo"])
    data = await read_uploaded_file_safely(dummy, max_bytes=1024)
    assert data == b"hola mundo"


async def test_read_uploaded_file_safely_exceeds_quota_raises_413() -> None:
    dummy = _DummyUpload([b"a" * 600, b"b" * 600])
    with pytest.raises(HTTPException) as exc_info:
        await read_uploaded_file_safely(dummy, max_bytes=1000)
    assert exc_info.value.status_code == 413


async def test_validate_file_magic_bytes_and_upload_enforcement() -> None:
    assert validate_file_magic_bytes(b"%PDF-1.7\n...") == "application/pdf"
    assert validate_file_magic_bytes(b"\x89PNG\r\n\x1a\n...") == "image/png"
    assert validate_file_magic_bytes(b"\xff\xd8\xff\xe0...") == "image/jpeg"
    assert validate_file_magic_bytes(b"RIFF\x24\x00\x00\x00WEBPVP8 ") == "image/webp"
    assert validate_file_magic_bytes(b"\x00\x00\x00\x1cftypavif\x00\x00\x00\x00") == "image/avif"

    with pytest.raises(HTTPException) as exc_info:
        validate_file_magic_bytes(b"MZ\x90\x00executable")
    assert exc_info.value.status_code == 415

    png_upload = _DummyUpload([b"\x89PNG\r\n\x1a\npayload"])
    data = await read_uploaded_file_safely(png_upload, max_bytes=1024, verify_magic_bytes=True)
    assert data.startswith(b"\x89PNG")

    bad_upload = _DummyUpload([b"#!/bin/sh\nrm -rf /"])
    with pytest.raises(HTTPException) as exc_bad:
        await read_uploaded_file_safely(bad_upload, max_bytes=1024, verify_magic_bytes=True)
    assert exc_bad.value.status_code == 415


async def test_redis_user_session_revocation_and_dependency_gate(client: TestClient) -> None:
    mock_redis = AsyncMock()
    await revoke_user_session(mock_redis, 777)
    assert await is_user_session_revoked(mock_redis, 777) is True
    await clear_user_session_revocation(mock_redis, 777)

    mock_redis.get.return_value = "1"
    assert await is_user_session_revoked(mock_redis, 888) is True

    mock_redis.get.side_effect = RuntimeError("redis offline")
    mock_redis.set.side_effect = RuntimeError("redis offline")
    mock_redis.delete.side_effect = RuntimeError("redis offline")
    await revoke_user_session(mock_redis, 999)
    assert await is_user_session_revoked(mock_redis, 999) is True
    await clear_user_session_revocation(mock_redis, 999)
    assert await is_user_session_revoked(mock_redis, 999) is False
    assert await is_user_session_revoked(None, 999) is False

    # Verificar que get_current_user rechaza con 401 si la sesión está revocada
    token = create_access_token(data={"sub": "revocado@test.com", "rol": "PROPIETARIO", "id": 555})
    mock_session = AsyncMock()
    mock_result = MagicMock()

    class RevokedUser:
        id: int = 555
        correo: str = "revocado@test.com"
        nombre: str = "Revocado"
        rol: str = "PROPIETARIO"
        es_activo: bool = True

    mock_result.scalars().first.return_value = RevokedUser()
    mock_session.execute.return_value = mock_result
    app.dependency_overrides[get_db] = lambda: mock_session
    await revoke_user_session(None, 555)
    try:
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401
        assert "revocada" in res.json()["detail"]

        res_dep = client.get("/api/finanzas/tasa", headers={"Authorization": f"Bearer {token}"})
        assert res_dep.status_code == 401
        assert "revocada" in res_dep.json()["detail"]
    finally:
        await clear_user_session_revocation(None, 555)
        app.dependency_overrides = {}


def test_verify_websocket_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.condominio.com,https://admin.condominio.com")
    assert verify_websocket_origin(None) is False
    assert verify_websocket_origin("https://app.condominio.com") is True
    assert verify_websocket_origin("https://evil.com") is False

    monkeypatch.setenv("APP_ENV", "development")
    assert verify_websocket_origin(None) is True
    assert verify_websocket_origin("https://custom.local", allowed_origins={"https://custom.local"}) is True


async def test_redis_scoped_idempotency_and_grace_period() -> None:
    assert build_idempotency_key("user:7", "uuid-1") == "idemp:user:7:uuid-1"
    assert build_idempotency_key("   ", "uuid-1") == "idemp:global:uuid-1"

    mock_redis = AsyncMock()
    mock_redis.set.return_value = True
    is_new = await check_and_set_idempotency_key(mock_redis, "key-123", ttl_seconds=60, scope="user:9")
    assert is_new is True
    mock_redis.set.assert_awaited_once_with("idemp:user:9:key-123", "1", nx=True, ex=60)

    await rotate_refresh_token_with_grace_period(mock_redis, "fam-1", "new-jwt-token", grace_seconds=5)
    mock_redis.set.assert_awaited_with("grace_period:fam-1", "new-jwt-token", ex=5)

    mock_redis.get.return_value = "new-jwt-token"
    assert await get_refresh_token_from_grace_period(mock_redis, "fam-1") == "new-jwt-token"

    mock_redis.get.return_value = None
    assert await get_refresh_token_from_grace_period(mock_redis, "fam-inexistente") is None


def test_get_redis_client_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.redis_client as rc

    monkeypatch.setattr(rc, "_redis_client", None)
    client1 = get_redis_client()
    client2 = get_redis_client()
    assert client1 is client2


def test_mass_assignment_extra_forbid_on_all_input_schemas() -> None:
    """Todos los esquemas de entrada deben rechazar campos no declarados (Patrón 1)."""
    with pytest.raises(ValidationError):
        UsuarioCreate.model_validate(
            {
                "nombre": "A",
                "cedula": "V-1",
                "correo": "a@test.com",
                "telefono": "1",
                "password": "p",
                "unidad_solicitada_id": 1,
                "tipo_ocupante_solicitado": "PROPIETARIO",
                "rol": "TESORERO",
            }
        )
    with pytest.raises(ValidationError):
        LoginData.model_validate({"correo": "a@test.com", "password": "p", "es_activo": True})
    with pytest.raises(ValidationError):
        TasaCambioCreate.model_validate({"tasa_usd_ves": "36.5", "extra": 1})
    with pytest.raises(ValidationError):
        ReciboCreate.model_validate({"unidad_id": 1, "periodo": "2026-10", "monto_usd": "10.00", "bloqueado": True})
    with pytest.raises(ValidationError):
        PagoReportar.model_validate(
            {"recibo_id": 1, "monto": "10.00", "moneda": "USD", "metodo_pago": "EFECTIVO", "estado": "APROBADO"}
        )
    with pytest.raises(ValidationError):
        PagoRechazo.model_validate({"motivo": "X", "extra": "Y"})
    with pytest.raises(ValidationError):
        EgresoCreate.model_validate(
            {
                "periodo": "2026-10",
                "categoria": "A",
                "descripcion": "B",
                "monto": "10.00",
                "moneda": "USD",
                "bloqueado": True,
            }
        )
    with pytest.raises(ValidationError):
        CierreMensualRequest.model_validate({"periodo": "2026-10", "estado": "ABIERTO"})
    with pytest.raises(ValidationError):
        AlicuotaUpdateRequest.model_validate({"alicuota": "10.0000", "extra": 1})
    with pytest.raises(ValidationError):
        FondoCondominioCreate.model_validate({"nombre": "Fondo Reserva", "saldo_actual_usd": "9999.00"})
    with pytest.raises(ValidationError):
        FacturarPeriodoRequest.model_validate({"periodo": "2026-10", "modalidad": "ALICUOTA", "hack": True})


def test_bearer_token_authentication_and_production_422_sanitization(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Valida soporte Authorization: Bearer (M2M/MCP) y sanitización 422 en producción."""
    token = create_access_token(data={"sub": "admin@test.com", "rol": "PRESIDENTE", "id": 1})

    mock_session = AsyncMock()
    mock_result = MagicMock()

    class FakeUser:
        id: int = 1
        correo: str = "admin@test.com"
        nombre: str = "Admin"
        rol: str = "PRESIDENTE"
        es_activo: bool = True

    mock_result.scalars().first.return_value = FakeUser()
    mock_session.execute.return_value = mock_result
    app.dependency_overrides[get_db] = lambda: mock_session

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["rol"] == "PRESIDENTE"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"

    app.dependency_overrides = {}

    # Modo producción: oculta detalle interno en errores 422
    monkeypatch.setenv("APP_ENV", "production")
    assert _es_produccion() is True
    res_422 = client.post("/api/auth/login", json={"correo": "solo_correo"})
    assert res_422.status_code == 422
    assert res_422.json() == {"detail": "Los datos proporcionados no cumplen con los requisitos de validación."}


def test_validate_production_security_settings_fail_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida Fail-Fast en producción ante SECRET_KEY débil o DATABASE_URL en memoria (Hito 17.1)."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SECRET_KEY", DEFAULT_INSECURE_SECRET_KEY)
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    validate_production_security_settings()

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@postgres:5432/condominio")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_production_security_settings()

    monkeypatch.setenv("SECRET_KEY", "a" * 31)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_production_security_settings()

    monkeypatch.setenv("SECRET_KEY", "a" * 32)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        validate_production_security_settings()

    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        validate_production_security_settings()

    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@postgres:5432/condominio")
    validate_production_security_settings()


def test_should_use_secure_cookie_and_refresh_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida COOKIE_SECURE adaptable y utilidades JWT de refresh_token y decodificación segura."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    assert should_use_secure_cookie() is False

    monkeypatch.setenv("COOKIE_SECURE", "true")
    assert should_use_secure_cookie() is True

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    assert should_use_secure_cookie() is True

    monkeypatch.setenv("COOKIE_SECURE", "false")
    assert should_use_secure_cookie() is False

    rt = create_refresh_token({"sub": "tok@test.com", "id": 3, "sid": "sid-t"})
    decoded = decode_refresh_token(rt)
    assert decoded["typ"] == "refresh"
    assert decoded["sub"] == "tok@test.com"
    assert decode_token_unverified_exp(rt) is not None
    assert decode_token_unverified_exp("token-malo") is None


def test_csrf_middleware_blocks_cookie_mutation_when_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enforce X-CSRF-Token bloquea mutaciones por cookie sin token y permite Bearer o token válido."""
    monkeypatch.setenv("CSRF_ENFORCE", "true")
    client = TestClient(app)
    token = create_access_token({"sub": "csrf@test.com", "rol": "PROPIETARIO", "id": 9, "sid": "sid-csrf"})
    valid_csrf = generate_csrf_token("sid-csrf")

    client.cookies.set("access_token", f"Bearer {token}")
    blocked = client.post("/api/finanzas/tasas", json={})
    assert blocked.status_code == 403
    assert "CSRF" in blocked.json()["detail"]

    # Pre-auth /auth/logout aunque tenga cookie también requiere CSRF? Logout no está excluido si hay sesión cookie
    # Bearer explícito omite validación double-submit
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = None
    mock_session.execute.return_value = mock_result
    app.dependency_overrides[get_db] = lambda: mock_session

    bearer_req = client.post("/api/finanzas/tasas", headers={"Authorization": f"Bearer {token}"}, json={})
    assert bearer_req.status_code != 403

    csrf_ok_req = client.post("/api/finanzas/tasas", headers={"X-CSRF-Token": valid_csrf}, json={})
    assert csrf_ok_req.status_code != 403
    app.dependency_overrides = {}
    client.cookies.clear()


@pytest.mark.asyncio
async def test_redis_fail_closed_in_production_and_sid_revocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """En APP_ENV=production KeyDB caído o None debe fallar cerrado con HTTP 503."""
    reset_local_security_state()
    monkeypatch.setenv("APP_ENV", "production")

    broken_redis = AsyncMock()
    broken_redis.get.side_effect = RuntimeError("KeyDB unreachable")
    broken_redis.set.side_effect = RuntimeError("KeyDB unreachable")
    broken_redis.incr.side_effect = RuntimeError("KeyDB unreachable")

    for client_arg in (None, broken_redis):
        with pytest.raises(HTTPException) as exc_rev:
            await is_session_id_revoked(client_arg, "sid-prod")
        assert exc_rev.value.status_code == 503

        with pytest.raises(HTTPException) as exc_lock:
            await is_login_locked_out(client_arg, "1.1.1.1", "a@b.com")
        assert exc_lock.value.status_code == 503

        with pytest.raises(HTTPException) as exc_fail:
            await record_login_failure(client_arg, "1.1.1.1", "a@b.com")
        assert exc_fail.value.status_code == 503

        with pytest.raises(HTTPException) as exc_jti:
            await mark_refresh_jti_used(client_arg, "jti-prod")
        assert exc_jti.value.status_code == 503

        with pytest.raises(HTTPException) as exc_g1:
            await rotate_refresh_token_with_grace_period(client_arg, "fam-1", "tok")
        assert exc_g1.value.status_code == 503

        with pytest.raises(HTTPException) as exc_g2:
            await get_refresh_token_from_grace_period(client_arg, "fam-1")
        assert exc_g2.value.status_code == 503

    monkeypatch.setenv("APP_ENV", "development")
    ok_redis = AsyncMock()
    ok_redis.get.return_value = "5"
    ok_redis.incr.return_value = 1
    assert await is_login_locked_out(ok_redis, "10.0.0.1", "u@test.com") is True
    assert await record_login_failure(ok_redis, "10.0.0.2", "u@test.com") == 1
    ok_redis.expire.assert_awaited_once()
    await clear_login_failures(ok_redis, "10.0.0.2", "u@test.com")
    await revoke_session_id(ok_redis, "sid-dev-1")
    assert await is_session_id_revoked(None, "sid-dev-1") is True
    assert await mark_refresh_jti_used(None, "") is False
    reset_local_security_state()


@pytest.mark.asyncio
async def test_get_current_user_rejects_revoked_sid(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_current_user rechaza con 401 si el SID fue revocado aunque el usuario esté activo."""
    from types import SimpleNamespace

    from starlette.requests import Request

    from src.dependencies import get_current_user

    monkeypatch.setenv("APP_ENV", "development")
    reset_local_security_state()
    tok = create_access_token({"sub": "siduser@test.com", "id": 51, "sid": "sid-rev-dep"})
    req = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/auth/me",
            "headers": [(b"authorization", f"Bearer {tok}".encode())],
        }
    )
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars().first.return_value = SimpleNamespace(id=51, correo="siduser@test.com", rol="PROPIETARIO")
    mock_db.execute.return_value = mock_res

    mock_redis = AsyncMock()
    mock_redis.get.side_effect = [None, "1"]

    with pytest.raises(HTTPException) as exc:
        await get_current_user(req, db=mock_db, redis_conn=mock_redis)
    assert exc.value.status_code == 401
    assert "Sesión revocada" in exc.value.detail


@pytest.mark.asyncio
async def test_security_constants_jwt_magic_bytes_and_upload_boundaries(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pruebas de frontera directas en constantes, CSRF, JWT refresh, magic bytes y uploads (mutación 11X)."""
    from datetime import timedelta

    import jwt

    assert ALGORITHM == "HS256"
    assert ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert REFRESH_TOKEN_EXPIRE_DAYS == 7
    assert PBKDF2_ITERATIONS == 100_000
    assert MAX_UPLOAD_SIZE_BYTES == 2 * 1024 * 1024
    assert UPLOAD_CHUNK_SIZE == 64 * 1024
    assert "localhost" in FORBIDDEN_CONTAINER_HOSTS
    assert "postgres" in FORBIDDEN_CONTAINER_HOSTS
    assert "keydb" in FORBIDDEN_CONTAINER_HOSTS

    hashed = get_password_hash("ClaveBoundary123!")
    parts_hash = hashed.split("$")
    assert len(parts_hash) == 3
    assert parts_hash[0] == "pbkdf2_sha256"
    assert len(parts_hash[1]) == 32
    assert len(parts_hash[2]) == 64
    assert verify_password("ClaveBoundary123!", "pbkdf2_sha256$not_int$salt$digest") is False
    assert verify_password("ClaveBoundary123!", "pbkdf2_sha256$10$salt$a$b") is False
    assert verify_password("ClaveBoundary123!", "pbkdf2_sha256$salt$bad_digest") is False

    # COOKIE_SECURE e is_csrf_enforced solo aceptan "true" explícito (case/espacios normalizados)
    for truthy in ("true", " TRUE "):
        monkeypatch.setenv("COOKIE_SECURE", truthy)
        monkeypatch.setenv("APP_ENV", "development")
        assert should_use_secure_cookie() is True
        monkeypatch.setenv("CSRF_ENFORCE", truthy)
        assert is_csrf_enforced() is True
    for falsy in ("0", "1", "false", "no"):
        monkeypatch.setenv("COOKIE_SECURE", falsy)
        monkeypatch.setenv("APP_ENV", "production")
        assert should_use_secure_cookie() is False
        monkeypatch.setenv("CSRF_ENFORCE", falsy)
        assert is_csrf_enforced() is True
        monkeypatch.setenv("APP_ENV", "development")
        assert is_csrf_enforced() is False

    monkeypatch.delenv("CSRF_ENFORCE", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    assert is_csrf_enforced() is True
    monkeypatch.setenv("APP_ENV", "development")
    assert is_csrf_enforced() is False

    # Refresh token expirado, tipo inválido ("access") y token malformado -> InvalidTokenError
    access_only = create_access_token({"sub": "a@b.com", "id": 1}, expires_delta=timedelta(minutes=5))
    payload_access = decode_token_unverified_exp(access_only)
    assert payload_access is not None and isinstance(payload_access["exp"], int) and payload_access["exp"] > 0

    with pytest.raises(jwt.InvalidTokenError):
        decode_refresh_token(access_only)

    expired_refresh = create_refresh_token({"sub": "a@b.com", "id": 1}, expires_delta=timedelta(seconds=-10))
    payload_exp = decode_token_unverified_exp(expired_refresh)
    assert payload_exp is not None and isinstance(payload_exp["exp"], int)
    with pytest.raises(jwt.InvalidTokenError):
        decode_refresh_token(expired_refresh)

    with pytest.raises(jwt.InvalidTokenError):
        decode_refresh_token("no.jwt.valido")

    rt_fijo = create_refresh_token({"sub": "a@b.com", "jti": "jti-fijo"})
    assert decode_refresh_token(rt_fijo)["jti"] == "jti-fijo"
    rt_auto = create_refresh_token({"sub": "a@b.com"})
    assert len(str(decode_refresh_token(rt_auto)["jti"])) >= 16

    # Magic bytes límites exactos (WEBP len<12, AVI, AVIF variants, JPEG, PDF, PNG truncado)
    assert validate_file_magic_bytes(b"\x89PNG") == "image/png"
    assert validate_file_magic_bytes(b"\x00\x00\x00\x1cftypavis\x00\x00") == "image/avif"
    assert validate_file_magic_bytes(b"\x00\x00\x00\x1cftypmif1\x00\x00") == "image/avif"
    for invalid_bytes in (
        b"",
        b"\x89PN",
        b"RIFF\x24\x00\x00\x00WEB",
        b"RIFF\x24\x00\x00\x00AVI ",
        b"\x00\x00\x00\x1cftypavi",
        b"\x00\x00\x00\x1cftypheic\x00\x00",
    ):
        with pytest.raises(HTTPException) as exc_m:
            validate_file_magic_bytes(invalid_bytes)
        assert exc_m.value.status_code == 415
        assert "Magic Bytes" in exc_m.value.detail

    # Carga en múltiples chunks justo en el límite (exacto == max_bytes pasa, +1 byte -> 413)
    exact_payload = b"%PDF-1.7" + b"X" * 92
    assert (
        await read_uploaded_file_safely(
            _DummyUpload([exact_payload[:50], exact_payload[50:]]),
            max_bytes=100,
            verify_magic_bytes=True,
        )
        == exact_payload
    )
    with pytest.raises(HTTPException) as exc_413:
        await read_uploaded_file_safely(_DummyUpload([exact_payload, b"Z"]), max_bytes=100, verify_magic_bytes=False)
    assert exc_413.value.status_code == 413
    assert "tamaño" in exc_413.value.detail.lower() or "mb" in exc_413.value.detail.lower()

    # SSRF IPv6 loopback / link-local y puerto explícito público
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port: [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", 0, 0, 0))],
    )
    with pytest.raises(ValueError, match="prohibido"):
        validate_safe_outgoing_url("https://ipv6-local.example.com:8443/hook")

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )
    assert validate_safe_outgoing_url("https://cdn.example.com:8443/a.png") == "https://cdn.example.com:8443/a.png"

    # WebSocket origin por defecto con ALLOWED_ORIGINS con espacios
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", " https://a.com ,  https://b.com ")
    assert verify_websocket_origin("https://a.com") is True
    assert verify_websocket_origin("https://b.com") is True
    assert verify_websocket_origin("https://c.com") is False
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    assert verify_websocket_origin("http://localhost:8080") is True
    assert verify_websocket_origin("http://localhost:5173") is True
    assert verify_websocket_origin("   ") is False


@pytest.mark.asyncio
async def test_security_survivor_contracts_and_exact_details(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica contratos exactos de mensajes, normalización, tiempos constantes y límites Magic Bytes."""
    import os

    from fastapi import status as http_status
    import jwt

    from src import security as security_mod

    # Constantes centinela y clave fallback exacta
    assert DEFAULT_INSECURE_SECRET_KEY == "qa-blueprint-11x-secret-key-super-secure-32bytes"
    assert security_mod._FALLBACK_DEV_SENTINEL == DEFAULT_INSECURE_SECRET_KEY
    assert security_mod.SECRET_KEY == os.getenv("SECRET_KEY", DEFAULT_INSECURE_SECRET_KEY)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setattr(security_mod, "SECRET_KEY", "fallback-temporal-32-chars-seguro")
    assert security_mod._get_secret_key() == "fallback-temporal-32-chars-seguro"

    # Normalización de APP_ENV / COOKIE_SECURE / CSRF_ENFORCE con espacios y valores por defecto
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("CSRF_ENFORCE", raising=False)
    assert should_use_secure_cookie() is False
    assert is_csrf_enforced() is False
    validate_production_security_settings()  # No debe fallar fuera de production

    monkeypatch.setenv("APP_ENV", "  PRODUCTION  ")
    assert should_use_secure_cookie() is True
    assert is_csrf_enforced() is True
    monkeypatch.setenv("CSRF_ENFORCE", "  TRUE  ")
    monkeypatch.delenv("APP_ENV", raising=False)
    assert is_csrf_enforced() is True

    # Fail-fast en producción: espacios en SECRET_KEY / DATABASE_URL y mensajes exactos
    monkeypatch.setenv("APP_ENV", "  PRODUCTION  ")
    monkeypatch.setenv("SECRET_KEY", "a" * 30 + "   ")
    with pytest.raises(
        RuntimeError,
        match=r"^Configuración insegura en APP_ENV=production: defina SECRET_KEY criptográfica \(>= 32 caracteres\)\.$",
    ):
        validate_production_security_settings()

    monkeypatch.setenv("SECRET_KEY", "c" * 32)
    for bad_db in ("   ", "sqlite+aiosqlite:///:memory:"):
        monkeypatch.setenv("DATABASE_URL", bad_db)
        with pytest.raises(
            RuntimeError,
            match=(
                r"^Configuración insegura en APP_ENV=production: "
                r"DATABASE_URL no puede estar vacía ni usar SQLite :memory:\.$"
            ),
        ):
            validate_production_security_settings()

    # Lista completa de hosts internos bloqueados por Anti-SSRF
    expected_hosts = frozenset(
        {
            "localhost",
            "api",
            "postgres",
            "keydb",
            "redis",
            "worker",
            "minio",
            "condominio_backend_api",
            "condominio_backend_redis",
            "condominio_backend_postgres",
        }
    )
    assert FORBIDDEN_CONTAINER_HOSTS == expected_hosts
    for host in expected_hosts:
        with pytest.raises(ValueError, match=r"^Acceso prohibido a recursos internos de infraestructura$"):
            validate_safe_outgoing_url(f"https://{host}/webhook")

    # Anti-SSRF errores exactos, esquema http/https y resolución DNS privada
    with pytest.raises(ValueError, match=r"^Esquema no permitido: ftp$"):
        validate_safe_outgoing_url("ftp://public.example.com/archivo.pdf")
    with pytest.raises(ValueError, match=r"^URL sin hostname válido$"):
        validate_safe_outgoing_url("https:///ruta-sin-host")

    def _raise_gai(_host: str, _port: Any) -> list[Any]:
        raise socket.gaierror("fail")

    monkeypatch.setattr(socket, "getaddrinfo", _raise_gai)
    with pytest.raises(ValueError, match=r"^No se pudo resolver el host: bad\.example$"):
        validate_safe_outgoing_url("https://bad.example/hook")

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda _host, _port: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 0))],
    )
    with pytest.raises(ValueError, match=r"^Destino prohibido en red privada o reservada \(10\.0\.0\.5\)$"):
        validate_safe_outgoing_url("https://privado.example/hook")

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda _host, _port: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )
    assert validate_safe_outgoing_url("  http://cdn.example.com/recurso  ") == "http://cdn.example.com/recurso"

    # Anti-enumeración en tiempo constante para hashes inválidos
    digest_calls: list[tuple[str, str]] = []
    real_digest = security_mod._pbkdf2_digest

    def _spy_digest(pw: str, salt: str) -> str:
        digest_calls.append((pw, salt))
        return real_digest(pw, salt)

    monkeypatch.setattr(security_mod, "_pbkdf2_digest", _spy_digest)
    assert verify_password("ClaveDemo123!", "hash-legacy-sin-prefijo") is False
    assert digest_calls == [("ClaveDemo123!", "0" * 32)]

    # Refresh token jti fallback para cadena vacía y coerción str(jti)
    rt_empty_jti = create_refresh_token({"sub": "a@b.com", "jti": ""})
    assert len(str(decode_refresh_token(rt_empty_jti)["jti"])) >= 16
    rt_num_jti = create_refresh_token({"sub": "a@b.com", "jti": 98765})
    assert decode_refresh_token(rt_num_jti)["jti"] == "98765"

    acc_tok = create_access_token({"sub": "a@b.com"})
    with pytest.raises(jwt.InvalidTokenError, match=r"^Tipo de token inválido para renovación\.$"):
        decode_refresh_token(acc_tok)

    # CSRF requiere token Y session_id no vacíos (ni HMAC válido con session_id vacío pasa)
    assert validate_csrf_token(generate_csrf_token(""), "") is False
    assert validate_csrf_token("", "session-abc") is False

    # Magic bytes exactamente en longitud mínima 12 y detalles HTTP exactos
    assert validate_file_magic_bytes(b"RIFF\x00\x00\x00\x00WEBP") == "image/webp"
    assert validate_file_magic_bytes(b"\x00\x00\x00\x1cftypavif") == "image/avif"
    assert validate_file_magic_bytes(b"\x00\x00\x00\x1cftypavis") == "image/avif"
    assert validate_file_magic_bytes(b"\x00\x00\x00\x1cftypmif1") == "image/avif"
    assert validate_file_magic_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF") == "image/jpeg"

    with pytest.raises(HTTPException) as exc_bad_magic:
        await read_uploaded_file_safely(_DummyUpload([b"INVALIDO_BINARIO_16"]), verify_magic_bytes=True)
    assert exc_bad_magic.value.status_code == http_status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert exc_bad_magic.value.detail == "Formato binario de archivo no permitido (Magic Bytes inválidos)."

    with pytest.raises(HTTPException) as exc_too_large:
        await read_uploaded_file_safely(_DummyUpload([b"a" * 11]), max_bytes=10, verify_magic_bytes=False)
    assert exc_too_large.value.status_code == http_status.HTTP_413_CONTENT_TOO_LARGE
    assert exc_too_large.value.detail == "El archivo excede el tamaño máximo permitido de 2 MB."

    # WebSocket Origin vacío o None en desarrollo vs producción
    monkeypatch.delenv("APP_ENV", raising=False)
    assert verify_websocket_origin(None) is True
    assert verify_websocket_origin("") is True
    monkeypatch.setenv("APP_ENV", "production")
    assert verify_websocket_origin(None) is False
