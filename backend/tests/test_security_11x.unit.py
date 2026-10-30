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
    clear_user_session_revocation,
    get_redis_client,
    get_refresh_token_from_grace_period,
    is_user_session_revoked,
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
    create_access_token,
    generate_csrf_token,
    get_password_hash,
    read_uploaded_file_safely,
    validate_csrf_token,
    validate_file_magic_bytes,
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
    """Maneja hashes PBKDF2 malformados y hashes legacy SHA-256."""
    assert verify_password("x", "pbkdf2_sha256$solo_dos_partes") is False
    legacy_hash = hashlib.sha256(b"legacy123").hexdigest()
    assert verify_password("legacy123", legacy_hash) is True
    assert verify_password("wrong", legacy_hash) is False


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
