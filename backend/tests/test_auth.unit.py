"""Pruebas unitarias de autenticación, registro, refresh rotation y lockout con SQLite FK real."""

import hashlib
import json
from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from datetime import timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.database import get_db
from src.main import app
from src.models import ContratoOcupacion, Usuario
from src.redis_client import (
    acquire_idempotency_slot,
    build_scoped_idempotency_key,
    get_redis_client,
    is_session_id_revoked,
    is_user_session_revoked,
    mark_refresh_jti_used,
    reset_local_security_state,
)
from src.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    generate_csrf_token,
    get_password_hash,
)
from tests._sqlite_helpers import SeededCondoContext, create_sqlite_fk_factory, seed_condo_base


@pytest.fixture(autouse=True)
def _limpiar_estado_auth() -> Generator[None]:
    """Aísla el estado local de Redis en memoria y overrides entre pruebas."""
    app.dependency_overrides.clear()
    reset_local_security_state()
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        reset_local_security_state()


@asynccontextmanager
async def _entorno_auth() -> AsyncIterator[tuple[async_sessionmaker[AsyncSession], SeededCondoContext, AsyncClient]]:
    """Prepara SQLite FK real y cliente HTTP asíncrono con limpieza obligatoria en try...finally."""
    engine, factory = await create_sqlite_fk_factory()
    try:
        ctx = await seed_condo_base(factory)

        async def _override_get_db() -> AsyncIterator[AsyncSession]:
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_redis_client] = lambda: None
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
            yield factory, ctx, ac
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_register_user_success() -> None:
    """Valida el registro exitoso persistiendo Usuario FANTASMA y ContratoOcupacion en SQLite FK."""
    async with _entorno_auth() as (factory, ctx, ac):
        payload = {
            "nombre": "Pedro QA",
            "cedula": "V-9999999",
            "correo": "pedro@test.com",
            "telefono": "12345",
            "password": "Mypassword1!",
            "unidad_solicitada_id": ctx.unidad_a_id,
            "tipo_ocupante_solicitado": "PROPIETARIO",
        }
        headers = {"Idempotency-Key": "123e4567-e89b-12d3-a456-426614174000"}
        response = await ac.post("/api/auth/register", json=payload, headers=headers)

        assert response.status_code == 201
        assert response.json()["es_activo"] is False
        assert response.json()["rol"] == "FANTASMA"
        async with factory() as session:
            usr = (await session.execute(select(Usuario).where(Usuario.correo == "pedro@test.com"))).scalars().first()
            assert usr is not None
            contrato = (
                (await session.execute(select(ContratoOcupacion).where(ContratoOcupacion.usuario_id == usr.id)))
                .scalars()
                .first()
            )
            assert contrato is not None and contrato.es_activo is False


@pytest.mark.asyncio
async def test_register_user_duplicate_idempotency_key() -> None:
    """Falla con 409 Conflict si la Idempotency-Key ya fue adquirida en Redis/memoria."""
    async with _entorno_auth() as (_, ctx, ac):
        payload = {
            "nombre": "Pedro Duplicado",
            "cedula": "V-9999999",
            "correo": "pedro@test.com",
            "telefono": "12345",
            "password": "Mypassword1!",
            "unidad_solicitada_id": ctx.unidad_a_id,
            "tipo_ocupante_solicitado": "PROPIETARIO",
        }
        key = "123e4567-e89b-12d3-a456-426614174000"
        raw_body = json.dumps(payload).encode("utf-8")
        redis_key = build_scoped_idempotency_key(1, 0, "register", key)
        await acquire_idempotency_slot(None, redis_key, hashlib.sha256(raw_body).hexdigest())

        response = await ac.post(
            "/api/auth/register",
            content=raw_body,
            headers={"Idempotency-Key": key, "Content-Type": "application/json"},
        )

        assert response.status_code == 409
        assert "Petición duplicada detectada" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_user_already_registered() -> None:
    """Falla con 409 si el usuario (correo o cédula) ya existe en base de datos."""
    async with _entorno_auth() as (_, ctx, ac):
        payload = {
            "nombre": "Pedro Ya Existe",
            "cedula": "V-9999999",
            "correo": "prop@condo.test",
            "telefono": "12345",
            "password": "Mypassword1!",
            "unidad_solicitada_id": ctx.unidad_a_id,
            "tipo_ocupante_solicitado": "PROPIETARIO",
        }
        headers = {"Idempotency-Key": "unique-idempotency-key-1"}
        response = await ac.post("/api/auth/register", json=payload, headers=headers)

        assert response.status_code == 409
        assert "Usuario ya registrado" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_missing_idempotency_key() -> None:
    """Falla con 422 si no se envía el header de idempotencia."""
    async with _entorno_auth() as (_, ctx, ac):
        payload = {
            "nombre": "Pedro QA",
            "cedula": "V-9999999",
            "correo": "pedro@test.com",
            "telefono": "12345",
            "password": "Mypassword1!",
            "unidad_solicitada_id": ctx.unidad_a_id,
            "tipo_ocupante_solicitado": "PROPIETARIO",
        }
        response = await ac.post("/api/auth/register", json=payload)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_user_db_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simula una falla catastrófica en la BD durante el registro y verifica rollback real."""
    async with _entorno_auth() as (factory, ctx, ac):
        payload = {
            "nombre": "Pedro Error",
            "cedula": "V-1111111",
            "correo": "error@test.com",
            "telefono": "123",
            "password": "Mypassword1!",
            "unidad_solicitada_id": ctx.unidad_a_id,
            "tipo_ocupante_solicitado": "PROPIETARIO",
        }
        headers = {"Idempotency-Key": "123e4567-e89b-12d3-a456-426614174001"}

        async with factory() as real_session:

            async def _fallar_commit() -> None:
                raise SQLAlchemyError("DB Connection Lost")

            monkeypatch.setattr(real_session, "commit", _fallar_commit)
            app.dependency_overrides[get_db] = lambda: real_session
            response = await ac.post("/api/auth/register", json=payload, headers=headers)

        assert response.status_code == 500
        assert "Error en base de datos" in response.json()["detail"]
        async with factory() as check_session:
            stmt_cnt = select(func.count()).select_from(Usuario).where(Usuario.correo == "error@test.com")
            total = (await check_session.execute(stmt_cnt)).scalar_one()
            assert total == 0


@pytest.mark.asyncio
async def test_register_user_integrity_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un error de integridad en BD se traduce en 400 (dato inválido), nunca en 500."""
    async with _entorno_auth() as (factory, ctx, ac):
        payload = {
            "nombre": "Pedro Integridad",
            "cedula": "V-2222222",
            "correo": "integridad@test.com",
            "telefono": "123",
            "password": "Mypassword1!",
            "unidad_solicitada_id": ctx.unidad_a_id,
            "tipo_ocupante_solicitado": "PROPIETARIO",
        }
        headers = {"Idempotency-Key": "integridad-key-1"}

        async with factory() as real_session:

            async def _fallar_integridad() -> None:
                raise IntegrityError("INSERT usuarios", {}, Exception("duplicado"))

            monkeypatch.setattr(real_session, "commit", _fallar_integridad)
            app.dependency_overrides[get_db] = lambda: real_session
            response = await ac.post("/api/auth/register", json=payload, headers=headers)

        assert response.status_code == 400
        assert "Datos inválidos o duplicados" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_set_httponly_cookie() -> None:
    """Valida un login exitoso contra SQLite verificando la creación de la cookie HttpOnly."""
    async with _entorno_auth() as (_, _, ac):
        payload = {"correo": "pres@condo.test", "password": "ClaveReal11X!"}
        response = await ac.post("/api/auth/login", json=payload)

        assert response.status_code == 200
        cookies = response.headers.get_list("set-cookie")
        assert any("access_token" in c and "HttpOnly" in c for c in cookies)


@pytest.mark.asyncio
async def test_login_invalid_credentials() -> None:
    """Valida un login con credenciales erróneas devolviendo 401."""
    async with _entorno_auth() as (_, _, ac):
        payload = {"correo": "noexiste@test.com", "password": "WrongPass123!"}
        response = await ac.post("/api/auth/login", json=payload)

        assert response.status_code == 401
        assert "Credenciales inválidas" in response.json()["detail"]


@pytest.mark.asyncio
async def test_me_without_cookie_fails() -> None:
    """Llamada a /api/auth/me sin cookie debe responder 401."""
    async with _entorno_auth() as (_, _, ac):
        response = await ac.get("/api/auth/me")
        assert response.status_code == 401
        assert "No autenticado" in response.json()["detail"]


@pytest.mark.asyncio
async def test_me_with_valid_token_success() -> None:
    """Llamada a /api/auth/me con token válido y usuario FANTASMA real en SQLite."""
    async with _entorno_auth() as (factory, _, ac):
        async with factory() as session:
            pedro = Usuario(
                condominio_id=1,
                nombre="Pedro QA",
                cedula="V-9998887",
                correo="pedro@test.com",
                telefono="0414",
                password_hash=get_password_hash("ClavePedro1!"),
                es_activo=False,
                rol="FANTASMA",
            )
            session.add(pedro)
            await session.commit()
            pedro_id = pedro.id

        token = create_access_token(data={"sub": "pedro@test.com", "rol": "FANTASMA", "id": pedro_id})
        ac.cookies.set("access_token", f"Bearer {token}")
        response = await ac.get("/api/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == pedro_id
        assert data["correo"] == "pedro@test.com"
        assert data["rol"] == "FANTASMA"
        assert data["es_activo"] is False


@pytest.mark.asyncio
async def test_me_with_expired_token() -> None:
    """Llamada a /api/auth/me con token expirado debe responder 401."""
    async with _entorno_auth() as (_, _, ac):
        expired_token = create_access_token(data={"sub": "expired@test.com"}, expires_delta=timedelta(seconds=-10))
        ac.cookies.set("access_token", f"Bearer {expired_token}")
        response = await ac.get("/api/auth/me")

        assert response.status_code == 401
        assert "Token expirado" in response.json()["detail"]


@pytest.mark.asyncio
async def test_me_with_invalid_token() -> None:
    """Llamada a /api/auth/me con token adulterado/inválido debe responder 401."""
    async with _entorno_auth() as (_, _, ac):
        ac.cookies.set("access_token", "Bearer token_completamente_invalido")
        response = await ac.get("/api/auth/me")

        assert response.status_code == 401
        assert "Token inválido" in response.json()["detail"]


@pytest.mark.asyncio
async def test_logout_revokes_session_and_clears_cookies() -> None:
    """POST /api/auth/logout revoca sid/jti en KeyDB sin afectar otros dispositivos."""
    async with _entorno_auth() as (_, _, ac):
        access = create_access_token({"sub": "logout@test.com", "rol": "PROPIETARIO", "id": 77, "sid": "sid-logout-1"})
        refresh = create_refresh_token({"sub": "logout@test.com", "id": 77, "sid": "sid-logout-1"})
        jti = str(decode_refresh_token(refresh)["jti"])
        ac.cookies.set("access_token", f"Bearer {access}")
        ac.cookies.set("refresh_token", refresh)

        res = await ac.post("/api/auth/logout")
        assert res.status_code == 200
        assert res.json()["message"] == "Sesión cerrada exitosamente"
        assert res.headers.get("clear-site-data") == '"cookies", "storage", "cache"'
        assert await is_session_id_revoked(None, "sid-logout-1") is True
        assert await is_user_session_revoked(None, 77) is False
        assert await mark_refresh_jti_used(None, jti) is False


@pytest.mark.asyncio
async def test_refresh_token_rotation_grace_period_and_replay() -> None:
    """POST /api/auth/refresh rota refresh_token, soporta grace period 5s y revoca en replay tardío."""
    async with _entorno_auth() as (_, ctx, ac):
        res_missing = await ac.post("/api/auth/refresh")
        assert res_missing.status_code == 401

        expired_refresh = create_refresh_token(
            {"sub": "prop@condo.test", "id": ctx.propietario_id, "sid": "sid-ref-1"},
            expires_delta=timedelta(seconds=-5),
        )
        res_exp = await ac.post("/api/auth/refresh", headers={"Authorization": f"Bearer {expired_refresh}"})
        assert res_exp.status_code == 401
        assert "expirado" in res_exp.json()["detail"]

        res_bad = await ac.post("/api/auth/refresh", headers={"Authorization": "Bearer invalido"})
        assert res_bad.status_code == 401

        incomplete_refresh = create_refresh_token({"id": ctx.propietario_id, "sid": "sid-no-sub"})
        res_nosub = await ac.post("/api/auth/refresh", headers={"Authorization": f"Bearer {incomplete_refresh}"})
        assert res_nosub.status_code == 401

        no_jti_access = create_access_token({"sub": "prop@condo.test", "id": ctx.propietario_id, "sid": "sid-ref-1"})
        res_missing_jti = await ac.post("/api/auth/refresh", headers={"Authorization": f"Bearer {no_jti_access}"})
        assert res_missing_jti.status_code == 401

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

        app.dependency_overrides[get_redis_client] = lambda: _FakeRedis()

        valid_refresh = create_refresh_token({"sub": "prop@condo.test", "id": ctx.propietario_id, "sid": "sid-ref-1"})
        ac.cookies.set("refresh_token", valid_refresh)

        res_ok = await ac.post("/api/auth/refresh")
        assert res_ok.status_code == 200
        assert res_ok.headers.get("x-csrf-token")

        # Segunda pestaña concurrente aún con el token previo dentro del grace period de 5s
        ac.cookies.clear()
        ac.cookies.set("refresh_token", valid_refresh)
        res_grace = await ac.post("/api/auth/refresh")
        assert res_grace.status_code == 200
        assert res_grace.json()["csrf_token"] == res_ok.json()["csrf_token"]

        # Expirado el grace period -> replay tardío revoca usuario/sid y devuelve 401 con Clear-Site-Data
        for key in [k for k in kv if k.startswith("grace_period:")]:
            del kv[key]
        ac.cookies.clear()
        ac.cookies.set("refresh_token", valid_refresh)
        res_replay = await ac.post("/api/auth/refresh")
        assert res_replay.status_code == 401
        assert "reutilizado" in res_replay.json()["detail"]
        assert res_replay.headers.get("clear-site-data") == '"cookies", "storage", "cache"'
        assert kv.get(f"revoked_user:{ctx.propietario_id}") == "1"
        assert kv.get("revoked_sid:sid-ref-1") == "1"


@pytest.mark.asyncio
async def test_me_real_orm_usuario_and_revoked_sid() -> None:
    """GET /api/auth/me resuelve cedula, telefono, unidad_activa_id y rechaza SID revocado o sin sub."""
    async with _entorno_auth() as (_, ctx, ac):
        token_no_sub = create_access_token(data={"rol": "PROPIETARIO"})
        ac.cookies.set("access_token", f"Bearer {token_no_sub}")
        res_no_sub = await ac.get("/api/auth/me")
        assert res_no_sub.status_code == 401

        sid_unico = f"sid-rev-{uuid4().hex[:8]}"
        token_revoked = create_access_token(data={"sub": "prop@condo.test", "id": ctx.propietario_id, "sid": sid_unico})
        ac.cookies.clear()
        ac.cookies.set("access_token", f"Bearer {token_revoked}")
        ok_resp = await ac.get("/api/auth/me")
        assert ok_resp.status_code == 200
        body = ok_resp.json()
        assert body["cedula"] == "V-10000006"
        assert body["telefono"] == "+584140000100"
        assert body["unidad_activa_id"] == ctx.unidad_a_id
        assert ok_resp.headers.get("x-csrf-token") == generate_csrf_token(sid_unico)

        # Revocamos mediante logout y validamos rechazo 401 por SID revocado
        await ac.post("/api/auth/logout")
        ac.cookies.set("access_token", f"Bearer {token_revoked}")
        revoked_resp = await ac.get("/api/auth/me")
        assert revoked_resp.status_code == 401


@pytest.mark.asyncio
async def test_login_lockout_429_and_short_idempotency_key() -> None:
    """Lockout 429 tras 5 fallos (ip, correo) y rechazo 422 de Idempotency-Key < 8 caracteres."""
    async with _entorno_auth() as (_, ctx, ac):
        uid = uuid4()
        hdrs = {"X-Forwarded-For": f"203.{uid.bytes[0]}.{uid.bytes[1]}.{uid.bytes[2] % 250 + 1}"}
        correo_brute = f"brute-{uid.hex[:8]}@test.com"
        for _ in range(5):
            r = await ac.post(
                "/api/auth/login",
                json={"correo": correo_brute, "password": "WrongPass123!"},
                headers=hdrs,
            )
            assert r.status_code == 401

        blocked = await ac.post(
            "/api/auth/login",
            json={"correo": correo_brute, "password": "WrongPass123!"},
            headers=hdrs,
        )
        assert blocked.status_code == 429
        assert "Demasiados intentos" in blocked.json()["detail"]

        res_short = await ac.post(
            "/api/auth/register",
            json={
                "nombre": "Corto",
                "cedula": "V-9991112",
                "correo": "corto@test.com",
                "telefono": "0414",
                "password": "Mypassword1!",
                "unidad_solicitada_id": ctx.unidad_a_id,
                "tipo_ocupante_solicitado": "PROPIETARIO",
            },
            headers={"Idempotency-Key": "short"},
        )
        assert res_short.status_code == 422
