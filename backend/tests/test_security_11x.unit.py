"""Pruebas unitarias de las salvaguardas de seguridad Nivel 11X."""

from __future__ import annotations

import hashlib
import hmac
import inspect
import socket
from collections.abc import AsyncIterator, Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src import schemas as schemas_module
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
from src.routers import auth as auth_module
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
    JWT_AUDIENCE,
    JWT_ISSUER,
    MAX_UPLOAD_SIZE_BYTES,
    PBKDF2_ITERATIONS,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
    UPLOAD_CHUNK_SIZE,
    compute_worm_record_hash,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    decode_token_unverified_exp,
    derive_subkey,
    generate_csrf_token,
    get_password_hash,
    get_password_hash_async,
    get_qr_signing_key,
    get_solvency_signing_key,
    get_vote_signing_key,
    get_worm_signing_key,
    is_csrf_enforced,
    is_trusted_proxy_ip,
    read_uploaded_file_safely,
    should_use_secure_cookie,
    validate_csrf_token,
    validate_file_magic_bytes,
    validate_production_security_settings,
    validate_safe_outgoing_url,
    validate_safe_outgoing_url_async,
    verify_password,
    verify_password_async,
    verify_websocket_origin,
)
from tests._sqlite_helpers import create_sqlite_fk_factory, seed_condo_base


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


def _build_sqlite_db_override(
    factory: async_sessionmaker[AsyncSession],
) -> Callable[[], AsyncIterator[AsyncSession]]:
    """Construye un override de get_db respaldado por sesiones SQLite reales."""

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    return _override_get_db


@pytest.mark.asyncio
async def test_redis_user_session_revocation_and_dependency_gate() -> None:
    mock_redis = AsyncMock()
    mock_redis.get.return_value = "1"
    await revoke_user_session(mock_redis, 777)
    mock_redis.set.assert_awaited()
    assert await is_user_session_revoked(mock_redis, 777) is True
    await clear_user_session_revocation(mock_redis, 777)
    mock_redis.delete.assert_awaited()

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

    # Verificar que get_current_user rechaza con 401 si la sesión está revocada (SQLite FK real)
    engine, factory = await create_sqlite_fk_factory()
    revoked_user_id: int | None = None
    try:
        ctx = await seed_condo_base(factory)
        revoked_user_id = ctx.propietario_id
        token = create_access_token(data={"sub": "prop@condo.test", "rol": "PROPIETARIO", "id": revoked_user_id})
        app.dependency_overrides[get_db] = _build_sqlite_db_override(factory)
        await revoke_user_session(None, revoked_user_id)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as async_client:
            res = await async_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 401
            assert "revocada" in res.json()["detail"]

            res_dep = await async_client.get("/api/finanzas/tasa", headers={"Authorization": f"Bearer {token}"})
            assert res_dep.status_code == 401
            assert "revocada" in res_dep.json()["detail"]
    finally:
        if revoked_user_id is not None:
            await clear_user_session_revocation(None, revoked_user_id)
        app.dependency_overrides.clear()
        await engine.dispose()


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
                "password": "PasswordValida123!",
                "unidad_solicitada_id": 1,
                "tipo_ocupante_solicitado": "PROPIETARIO",
                "rol": "TESORERO",
            }
        )
    with pytest.raises(ValidationError):
        LoginData.model_validate({"correo": "a@test.com", "password": "PasswordValida123!", "es_activo": True})
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


def _descubrir_esquemas_entrada() -> dict[str, type[BaseModel]]:
    """Descubre todos los esquemas de entrada Pydantic en src.schemas y src.routers.auth."""
    esquemas: dict[str, type[BaseModel]] = {}
    for modulo in (schemas_module, auth_module):
        for nombre, cls in inspect.getmembers(modulo, inspect.isclass):
            if (
                issubclass(cls, BaseModel)
                and cls is not BaseModel
                and cls.__module__ == modulo.__name__
                and not nombre.startswith("_")
                and not nombre.endswith("Response")
            ):
                esquemas[nombre] = cls
    return esquemas


def test_extra_forbid_dinamico_en_todos_los_esquemas_de_entrada() -> None:
    """Valida extra='forbid' y rechazo de campo fantasma en TODOS los esquemas de entrada."""
    esquemas_entrada = _descubrir_esquemas_entrada()
    assert len(esquemas_entrada) >= 31

    for nombre, cls in sorted(esquemas_entrada.items()):
        assert cls.model_config.get("extra") == "forbid", (
            f"El esquema de entrada {nombre} debe configurar extra='forbid'"
        )
        with pytest.raises(ValidationError) as exc_info:
            cls.model_validate({"campo_fantasma_11x": "inyeccion"})
        assert any(
            err["type"] == "extra_forbidden" and err["loc"] == ("campo_fantasma_11x",)
            for err in exc_info.value.errors()
        ), f"{nombre} no rechazó campo_fantasma_11x con extra_forbidden"


@pytest.mark.asyncio
async def test_bearer_token_authentication_and_production_422_sanitization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valida soporte Authorization: Bearer (M2M/MCP) y sanitización 422 en producción."""
    engine, factory = await create_sqlite_fk_factory()
    try:
        ctx = await seed_condo_base(factory)
        token = create_access_token(data={"sub": "pres@condo.test", "rol": "PRESIDENTE", "id": ctx.presidente_id})
        app.dependency_overrides[get_db] = _build_sqlite_db_override(factory)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as async_client:
            response = await async_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert response.status_code == 200
            assert response.json()["rol"] == "PRESIDENTE"
            assert response.headers["x-content-type-options"] == "nosniff"
            assert response.headers["x-frame-options"] == "DENY"

            # Modo producción: oculta detalle interno en errores 422
            monkeypatch.setenv("APP_ENV", "production")
            assert _es_produccion() is True
            res_422 = await async_client.post("/api/auth/login", json={"correo": "solo_correo"})
            assert res_422.status_code == 422
            assert res_422.json() == {"detail": "Los datos proporcionados no cumplen con los requisitos de validación."}
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


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


@pytest.mark.asyncio
async def test_csrf_middleware_blocks_cookie_mutation_when_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enforce X-CSRF-Token bloquea Cookie+Bearer dummy sin CSRF y permite M2M Bearer puro o token válido."""
    monkeypatch.setenv("CSRF_ENFORCE", "true")
    engine, factory = await create_sqlite_fk_factory()
    try:
        ctx = await seed_condo_base(factory)
        token = create_access_token(
            {"sub": "tes@condo.test", "rol": "TESORERO", "id": ctx.tesorero_id, "sid": "sid-csrf"}
        )
        valid_csrf = generate_csrf_token("sid-csrf")
        app.dependency_overrides[get_db] = _build_sqlite_db_override(factory)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as async_client:
            async_client.cookies.set("access_token", f"Bearer {token}")
            blocked = await async_client.post("/api/finanzas/tasas", json={})
            assert blocked.status_code == 403
            assert "CSRF" in blocked.json()["detail"]

            # Bypass con cookie activa + Authorization: Bearer dummy DEBE ser bloqueado con 403
            dummy_bypass = await async_client.post(
                "/api/finanzas/tasas",
                headers={"Authorization": "Bearer dummy"},
                json={},
            )
            assert dummy_bypass.status_code == 403
            assert "CSRF" in dummy_bypass.json()["detail"]

            csrf_ok_req = await async_client.post(
                "/api/finanzas/tasas",
                headers={"X-CSRF-Token": valid_csrf},
                json={},
            )
            assert csrf_ok_req.status_code != 403

            # Bearer M2M puro (sin cookies) omite double-submit CSRF
            async_client.cookies.clear()
            bearer_req = await async_client.post(
                "/api/finanzas/tasas",
                headers={"Authorization": f"Bearer {token}"},
                json={},
            )
            assert bearer_req.status_code != 403
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_redis_fail_closed_in_production_and_sid_revocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """En APP_ENV=production KeyDB caído o None debe fallar cerrado con HTTP 503."""
    from src.redis_client import burn_qr_nonce, check_and_set_idempotency_key, revoke_user_session

    reset_local_security_state()
    monkeypatch.setenv("APP_ENV", "production")

    broken_redis = AsyncMock()
    broken_redis.get.side_effect = RuntimeError("KeyDB unreachable")
    broken_redis.set.side_effect = RuntimeError("KeyDB unreachable")
    broken_redis.eval.side_effect = RuntimeError("KeyDB unreachable")
    broken_redis.delete.side_effect = RuntimeError("KeyDB unreachable")

    for client_arg in (None, broken_redis):
        with pytest.raises(HTTPException) as exc_rev:
            await is_session_id_revoked(client_arg, "sid-prod")
        assert exc_rev.value.status_code == 503

        with pytest.raises(HTTPException) as exc_rev_user:
            await revoke_user_session(client_arg, 10)
        assert exc_rev_user.value.status_code == 503

        with pytest.raises(HTTPException) as exc_rev_sid:
            await revoke_session_id(client_arg, "sid-prod")
        assert exc_rev_sid.value.status_code == 503

        with pytest.raises(HTTPException) as exc_idemp:
            await check_and_set_idempotency_key(client_arg, "key-prod")
        assert exc_idemp.value.status_code == 503

        with pytest.raises(HTTPException) as exc_qr:
            await burn_qr_nonce(client_arg, "jti-qr-prod")
        assert exc_qr.value.status_code == 503

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
    ok_redis.eval.return_value = 1
    assert await is_login_locked_out(ok_redis, "10.0.0.1", "u@test.com") is True
    assert await record_login_failure(ok_redis, "10.0.0.2", "u@test.com") == 1
    assert ok_redis.eval.await_count == 2
    await clear_login_failures(ok_redis, "10.0.0.2", "u@test.com")
    await revoke_session_id(ok_redis, "sid-dev-1")
    ok_redis.set.assert_awaited()
    assert await is_session_id_revoked(None, "sid-dev-1") is False
    await revoke_session_id(None, "sid-dev-local")
    assert await is_session_id_revoked(None, "sid-dev-local") is True
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
    assert PBKDF2_ITERATIONS == 600_000
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

    from datetime import UTC, datetime, timedelta

    acc_tok = create_access_token({"sub": "a@b.com"})
    with pytest.raises(jwt.InvalidTokenError):
        decode_refresh_token(acc_tok)

    wrong_typ_tok = jwt.encode(
        {
            "sub": "a@b.com",
            "typ": "access",
            "jti": "jti-wrong-typ",
            "iat": int(datetime.now(UTC).timestamp()),
            "iss": security_mod.JWT_ISSUER,
            "aud": security_mod.JWT_AUDIENCE,
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        },
        security_mod.derive_subkey("jwt-refresh"),
        algorithm=ALGORITHM,
    )
    with pytest.raises(jwt.InvalidTokenError, match=r"^Tipo de token inválido para renovación\.$"):
        decode_refresh_token(wrong_typ_tok)

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


def test_hkdf_subkeys_worm_hash_and_secret_key_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica constantes JWT/HKDF, expansión multibloque (>32 B), subclaves y hash WORM."""
    import os

    from src import security as security_mod

    assert JWT_ISSUER == "condominio-app"
    assert JWT_AUDIENCE == "condominio-app-client"
    assert SECRET_KEY == os.getenv("SECRET_KEY", DEFAULT_INSECURE_SECRET_KEY)
    assert security_mod._HKDF_SALT == b"condominio-app-hkdf-v1"

    monkeypatch.setenv("SECRET_KEY", "env-secret-key-32-bytes-minimum!")
    assert security_mod._get_secret_key() == "env-secret-key-32-bytes-minimum!"
    monkeypatch.setenv("SECRET_KEY", "")
    assert security_mod._get_secret_key() == SECRET_KEY
    monkeypatch.delenv("SECRET_KEY", raising=False)
    assert security_mod._get_secret_key() == SECRET_KEY

    salt = b"condominio-app-hkdf-v1"
    prk = hmac.new(salt, b"ikm-demo", hashlib.sha256).digest()
    assert security_mod._hkdf_extract(salt, b"ikm-demo") == prk

    t1 = hmac.new(prk, b"info-11x\x01", hashlib.sha256).digest()
    t2 = hmac.new(prk, t1 + b"info-11x\x02", hashlib.sha256).digest()
    t3 = hmac.new(prk, t2 + b"info-11x\x03", hashlib.sha256).digest()
    assert security_mod._hkdf_expand(prk, b"info-11x") == t1
    assert security_mod._hkdf_expand(prk, b"info-11x", 17) == t1[:17]
    assert security_mod._hkdf_expand(prk, b"info-11x", 42) == (t1 + t2)[:42]
    assert security_mod._hkdf_expand(prk, b"info-11x", 80) == (t1 + t2 + t3)[:80]

    hmac_calls: list[int] = []
    real_hmac_new = hmac.new

    def _spy_hmac_new(key: bytes, msg: bytes | None = None, digestmod: Any = None) -> Any:
        hmac_calls.append(1)
        return real_hmac_new(key, msg, digestmod)

    with monkeypatch.context() as mp:
        mp.setattr(security_mod.hmac, "new", _spy_hmac_new)
        for req_len, expected_calls in ((0, 0), (32, 1), (42, 2), (64, 2), (80, 3)):
            hmac_calls.clear()
            out = security_mod._hkdf_expand(prk, b"info-11x", req_len)
            assert len(out) == req_len
            assert len(hmac_calls) == expected_calls

    monkeypatch.setenv("SECRET_KEY", "env-master-32-chars-1234567890ab")
    prk_explicit = real_hmac_new(salt, b"explicit-master", hashlib.sha256).digest()
    exp_explicit = real_hmac_new(prk_explicit, b"solvency-hmac\x01", hashlib.sha256).digest().hex()
    assert derive_subkey("solvency-hmac", master_secret="explicit-master") == exp_explicit

    prk_empty = real_hmac_new(salt, b"", hashlib.sha256).digest()
    exp_empty = real_hmac_new(prk_empty, b"vote-hmac\x01", hashlib.sha256).digest().hex()
    assert derive_subkey("vote-hmac", master_secret="") == exp_empty
    assert derive_subkey("vote-hmac", master_secret=None) != exp_empty

    prk_env = real_hmac_new(salt, b"env-master-32-chars-1234567890ab", hashlib.sha256).digest()
    exp_qr = real_hmac_new(prk_env, b"qr-pass-hmac\x01", hashlib.sha256).digest().hex()
    assert derive_subkey("qr-pass-hmac") == exp_qr

    k_solv = get_solvency_signing_key()
    k_vote = get_vote_signing_key()
    k_qr = get_qr_signing_key()
    k_worm = get_worm_signing_key()
    k_worm_custom = get_worm_signing_key(master_secret="worm-master-key")
    assert k_solv == derive_subkey("solvency-hmac")
    assert k_vote == derive_subkey("vote-hmac")
    assert k_qr == exp_qr
    assert k_worm == derive_subkey("worm-audit-hmac")
    assert k_worm_custom == derive_subkey("worm-audit-hmac", master_secret="worm-master-key")
    assert len({k_solv, k_vote, k_qr, k_worm, k_worm_custom}) == 5
    assert all(len(k) == 64 for k in (k_solv, k_vote, k_qr, k_worm, k_worm_custom))

    expected_worm = real_hmac_new(
        k_worm_custom.encode("utf-8"),
        b"0" * 64 + b"|recibo:10|PAGADO",
        hashlib.sha256,
    ).hexdigest()
    h1 = compute_worm_record_hash("0" * 64, "recibo:10|PAGADO", master_secret="worm-master-key")
    h2 = compute_worm_record_hash("0" * 64, "recibo:10|PAGADO", master_secret="worm-master-key")
    assert h1 == expected_worm == h2
    assert len(h1) == 64
    assert compute_worm_record_hash("1" * 64, "recibo:10|PAGADO", master_secret="worm-master-key") != h1
    assert compute_worm_record_hash("0" * 64, "recibo:11|PAGADO", master_secret="worm-master-key") != h1
    assert compute_worm_record_hash("0" * 64, "recibo:10|PAGADO", master_secret=None) != h1
    assert compute_worm_record_hash("a", "bc", master_secret="worm-master-key") != compute_worm_record_hash(
        "ab", "c", master_secret="worm-master-key"
    )


def test_jwt_access_refresh_claims_errors_and_csrf_hmac_bounds() -> None:
    """Verifica claims JWT exactos, errores de decodificación/expiración y límites HMAC CSRF."""
    from datetime import UTC, datetime, timedelta

    import jwt

    raw_access = {"sub": "user@condo.test", "id": 42}
    tok_default = create_access_token(raw_access)
    assert raw_access == {"sub": "user@condo.test", "id": 42}
    decoded_default = decode_access_token(tok_default)
    assert decoded_default["sub"] == "user@condo.test"
    assert decoded_default["id"] == 42
    assert decoded_default["typ"] == "access"
    assert decoded_default["iss"] == "condominio-app"
    assert decoded_default["aud"] == "condominio-app-client"
    assert isinstance(decoded_default["iat"], int)
    assert isinstance(decoded_default["exp"], int)
    assert decoded_default["exp"] - decoded_default["iat"] == ACCESS_TOKEN_EXPIRE_MINUTES * 60

    tok_5m = create_access_token({"sub": "u@t.com"}, expires_delta=timedelta(minutes=5))
    decoded_5m = decode_access_token(tok_5m)
    assert decoded_5m["exp"] - decoded_5m["iat"] == 300

    expired_access = create_access_token({"sub": "exp@condo.test"}, expires_delta=timedelta(seconds=-5))
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(expired_access)

    raw_refresh = {"sub": "user@condo.test", "id": 42}
    rt_default = create_refresh_token(raw_refresh)
    assert raw_refresh == {"sub": "user@condo.test", "id": 42}
    dec_rt = decode_refresh_token(rt_default)
    assert dec_rt["typ"] == "refresh"
    assert dec_rt["iss"] == "condominio-app"
    assert dec_rt["aud"] == "condominio-app-client"
    assert dec_rt["exp"] - dec_rt["iat"] == REFRESH_TOKEN_EXPIRE_DAYS * 86400

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(rt_default)

    now_ts = int(datetime.now(UTC).timestamp())
    base_access = {
        "sub": "u@condo.test",
        "typ": "access",
        "iat": now_ts,
        "iss": "condominio-app",
        "aud": "condominio-app-client",
        "exp": now_ts + 300,
    }
    wrong_typ_access = jwt.encode({**base_access, "typ": "refresh"}, derive_subkey("jwt-access"), algorithm=ALGORITHM)
    with pytest.raises(jwt.InvalidTokenError, match=r"^Tipo de token inválido para acceso\.$"):
        decode_access_token(wrong_typ_access)

    for missing in ("exp", "iat", "iss", "aud"):
        partial = {k: v for k, v in base_access.items() if k != missing}
        with pytest.raises(jwt.InvalidTokenError):
            decode_access_token(jwt.encode(partial, derive_subkey("jwt-access"), algorithm=ALGORITHM))

    for bad_override in ({"iss": "otro-iss"}, {"aud": "otro-aud"}):
        forged = jwt.encode({**base_access, **bad_override}, derive_subkey("jwt-access"), algorithm=ALGORITHM)
        with pytest.raises(jwt.InvalidTokenError):
            decode_access_token(forged)

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(jwt.encode(base_access, SECRET_KEY, algorithm=ALGORITHM))
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(jwt.encode(base_access, derive_subkey("jwt-access"), algorithm="HS512"))

    base_refresh = {**base_access, "typ": "refresh", "jti": "jti-check-1"}
    for missing in ("exp", "iat", "iss", "aud", "jti"):
        partial_r = {k: v for k, v in base_refresh.items() if k != missing}
        with pytest.raises(jwt.InvalidTokenError):
            decode_refresh_token(jwt.encode(partial_r, derive_subkey("jwt-refresh"), algorithm=ALGORITHM))
    for bad_override in ({"iss": "otro-iss"}, {"aud": "otro-aud"}):
        forged_r = jwt.encode({**base_refresh, **bad_override}, derive_subkey("jwt-refresh"), algorithm=ALGORITHM)
        with pytest.raises(jwt.InvalidTokenError):
            decode_refresh_token(forged_r)

    expired_refresh = create_refresh_token({"sub": "exp@condo.test"}, expires_delta=timedelta(seconds=-5))
    dec_exp_acc = decode_token_unverified_exp(expired_access)
    dec_exp_ref = decode_token_unverified_exp(expired_refresh)
    assert dec_exp_acc is not None and dec_exp_acc["typ"] == "access"
    assert dec_exp_ref is not None and dec_exp_ref["typ"] == "refresh"

    forged_swapped = jwt.encode({**base_access, "typ": "access"}, derive_subkey("jwt-refresh"), algorithm=ALGORITHM)
    forged_no_iat = jwt.encode(
        {k: v for k, v in base_access.items() if k != "iat"},
        derive_subkey("jwt-access"),
        algorithm=ALGORITHM,
    )
    assert decode_token_unverified_exp(wrong_typ_access) is None
    assert decode_token_unverified_exp(forged_swapped) is None
    assert decode_token_unverified_exp(forged_no_iat) is None

    expected_csrf = hmac.new(
        derive_subkey("csrf-hmac").encode("utf-8"),
        b"sid-hmac-check",
        hashlib.sha256,
    ).hexdigest()
    assert generate_csrf_token("sid-hmac-check") == expected_csrf
    assert len(expected_csrf) == 64
    assert validate_csrf_token(expected_csrf, "sid-hmac-check") is True
    flipped = expected_csrf[:-1] + ("0" if expected_csrf[-1] != "0" else "1")
    assert validate_csrf_token(flipped, "sid-hmac-check") is False
    assert validate_csrf_token(expected_csrf.upper(), "sid-hmac-check") is False
    assert validate_csrf_token(expected_csrf + "a", "sid-hmac-check") is False


def test_trusted_proxy_ip_and_forbidden_ip_ranges(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica validación de proxies confiables por defecto/env y rangos IP prohibidos Anti-SSRF."""
    from src import security as security_mod

    assert security_mod._DEFAULT_TRUSTED_PROXY_CIDRS == (
        "127.0.0.1/32",
        "::1/128",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
    )
    monkeypatch.delenv("TRUSTED_PROXY_IPS", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)

    assert is_trusted_proxy_ip(None) is False
    assert is_trusted_proxy_ip("") is False
    assert is_trusted_proxy_ip("   ") is False
    assert is_trusted_proxy_ip("127.0.0.1") is True
    assert is_trusted_proxy_ip("  127.0.0.1  ") is True
    assert is_trusted_proxy_ip("::1") is True
    assert is_trusted_proxy_ip("10.20.30.40") is True
    assert is_trusted_proxy_ip("172.16.0.1") is True
    assert is_trusted_proxy_ip("172.31.255.254") is True
    assert is_trusted_proxy_ip("172.32.0.1") is False
    assert is_trusted_proxy_ip("192.168.10.20") is True
    assert is_trusted_proxy_ip("8.8.8.8") is False
    assert is_trusted_proxy_ip("no-es-ip") is False

    assert is_trusted_proxy_ip("testclient") is True
    monkeypatch.setenv("APP_ENV", "  PRODUCTION  ")
    assert is_trusted_proxy_ip("testclient") is False

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("TRUSTED_PROXY_IPS", " , 203.0.113.10 , 198.51.100.0/24 , bad/99 , proxy-interno , ")
    assert is_trusted_proxy_ip("203.0.113.10") is True
    assert is_trusted_proxy_ip("198.51.100.42") is True
    assert is_trusted_proxy_ip("198.51.101.42") is False
    assert is_trusted_proxy_ip("proxy-interno") is True
    assert is_trusted_proxy_ip("127.0.0.1") is False
    assert is_trusted_proxy_ip("testclient") is False
    assert is_trusted_proxy_ip("bad") is False

    for forbidden in ("10.0.0.1", "127.0.0.1", "::1", "169.254.1.1", "224.0.0.1", "240.0.0.1", "0.0.0.0", "::"):
        assert security_mod._is_forbidden_ip(forbidden) is True
    for public in ("93.184.216.34", "2606:4700:4700::1111"):
        assert security_mod._is_forbidden_ip(public) is False


@pytest.mark.asyncio
async def test_async_password_ssrf_local_internal_and_upload_chunk_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cubre hashing asíncrono, sufijos .local/.internal, Anti-SSRF async, chunks de carga y WS origin."""
    hashed_async = await get_password_hash_async("ClaveAsync11X!")
    assert hashed_async.startswith("pbkdf2_sha256$")
    assert await verify_password_async("ClaveAsync11X!", hashed_async) is True
    assert await verify_password_async("ClaveIncorrecta", hashed_async) is False

    for internal_url in (
        "https://printer.local/status",
        "HTTPS://API.LOCAL/v1",
        "https://metadata.google.internal/computeMetadata",
        "https://LOCALHOST/health",
    ):
        with pytest.raises(ValueError, match=r"^Acceso prohibido a recursos internos de infraestructura$"):
            validate_safe_outgoing_url(internal_url)
        with pytest.raises(ValueError, match=r"^Acceso prohibido a recursos internos de infraestructura$"):
            await validate_safe_outgoing_url_async(internal_url)

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda _host, _port: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )
    assert (
        await validate_safe_outgoing_url_async("  HTTPS://CDN.Example.COM/Carpeta/Archivo.PDF  ")
        == "https://cdn.example.com/Carpeta/Archivo.PDF"
    )

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda _host, _port: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.10", 0))],
    )
    with pytest.raises(ValueError, match=r"^Destino prohibido en red privada o reservada \(192\.168\.1\.10\)$"):
        await validate_safe_outgoing_url_async("https://privado-async.example/hook")

    def _fail_async_dns(_host: str, _port: Any) -> list[Any]:
        raise socket.gaierror("fail")

    monkeypatch.setattr(socket, "getaddrinfo", _fail_async_dns)
    with pytest.raises(ValueError, match=r"^No se pudo resolver el host: missing\.example$"):
        await validate_safe_outgoing_url_async("https://missing.example/hook")

    class _SpyUpload:
        def __init__(self, chunks: list[bytes]) -> None:
            self._chunks = list(chunks)
            self.sizes: list[int] = []

        async def read(self, size: int = -1) -> bytes:
            self.sizes.append(size)
            if not self._chunks:
                return b""
            return self._chunks.pop(0)

    empty_spy = _SpyUpload([])
    assert await read_uploaded_file_safely(empty_spy, verify_magic_bytes=False) == b""
    assert empty_spy.sizes == [UPLOAD_CHUNK_SIZE]

    chunks_2mb = [b"a" * UPLOAD_CHUNK_SIZE] * 32
    exact_spy = _SpyUpload(chunks_2mb)
    loaded = await read_uploaded_file_safely(exact_spy, verify_magic_bytes=False)
    assert len(loaded) == MAX_UPLOAD_SIZE_BYTES
    assert all(sz == UPLOAD_CHUNK_SIZE for sz in exact_spy.sizes)

    over_spy = _SpyUpload([*chunks_2mb, b"x"])
    with pytest.raises(HTTPException) as exc_over:
        await read_uploaded_file_safely(over_spy, verify_magic_bytes=False)
    assert exc_over.value.status_code == 413
    assert exc_over.value.detail == "El archivo excede el tamaño máximo permitido de 2 MB."

    assert validate_file_magic_bytes(b"RIFF\x00\x00\x00\x00WEBP" + b"X" * 10) == "image/webp"

    monkeypatch.setenv("APP_ENV", "development")
    assert verify_websocket_origin("https://evil.com") is False
    assert verify_websocket_origin("https://a.com", allowed_origins=set()) is False
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    assert verify_websocket_origin("http://localhost:3000") is False
