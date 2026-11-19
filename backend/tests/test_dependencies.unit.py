"""Pruebas unitarias de dependencias FastAPI (auth Cookie/Bearer, RLS, RBAC e idempotencia)."""

import hashlib
import json
from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace
from typing import Any, cast

import jwt
import pytest
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src import dependencies
from src.database import DEFAULT_CONDOMINIO_ID, get_db
from src.dependencies import (
    ROLES_ACTIVOS_VALIDOS,
    ActiveIdempotencySlot,
    IdempotencyReplayException,
    IdempotentAPIRoute,
    _cargar_usuario_activo_desde_payload,
    _claim_idempotency_slot,
    _compute_request_payload_hash,
    _ContextoIdempotencia,
    _decode_response_json,
    _decodificar_payload_token,
    _extraer_claim_condominio,
    _extraer_user_condo,
    _finalize_request_slot,
    _PoliticaIdempotencia,
    _release_request_slot,
    _resolver_guardia_idempotencia,
    _resolver_override_usuario,
    _sesion_activa_valida,
    _validar_sesion_no_revocada,
    _validar_usuario_en_tenant,
    exigir_idempotencia,
    exigir_idempotencia_anonima,
    extract_bearer_or_cookie_token,
    get_current_user,
    get_optional_active_user,
    verificar_roles,
    verificar_usuario_activo,
)
from src.main import app
from src.models import TasaCambio, Usuario
from src.redis_client import (
    IdempotencyResponsePayload,
    _local_idempotency_records,
    get_redis_client,
    reset_local_security_state,
    revoke_session_id,
    revoke_user_session,
    store_idempotency_response,
)
from src.redis_idempotency import IdempotencySlotResult
from src.security import ALGORITHM, JWT_AUDIENCE, JWT_ISSUER, create_access_token, derive_subkey
from tests._sqlite_helpers import SeededCondoContext, create_sqlite_fk_factory, seed_condo_base

PROTEGIDO = "/api/finanzas/tasa"


@pytest.fixture(autouse=True)
def _limpiar_estado_deps() -> Generator[None]:
    """Aísla el estado local de seguridad y overrides entre pruebas."""
    app.dependency_overrides.clear()
    reset_local_security_state()
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        reset_local_security_state()


@asynccontextmanager
async def _entorno_sqlite() -> AsyncIterator[tuple[async_sessionmaker[AsyncSession], SeededCondoContext, AsyncClient]]:
    """Prepara SQLite FK real, cliente HTTP asíncrono y limpieza determinista en try...finally."""
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
async def test_endpoint_protegido_sin_cookie() -> None:
    async with _entorno_sqlite() as (_, _, ac):
        response = await ac.get(PROTEGIDO)
        assert response.status_code == 401
        assert "No autenticado" in response.json()["detail"]


@pytest.mark.asyncio
async def test_token_expirado() -> None:
    token = create_access_token(data={"sub": "x@test.com"}, expires_delta=timedelta(seconds=-10))
    async with _entorno_sqlite() as (_, _, ac):
        ac.cookies.set("access_token", f"Bearer {token}")
        response = await ac.get(PROTEGIDO)
        assert response.status_code == 401
        assert "expirado" in response.json()["detail"]


@pytest.mark.asyncio
async def test_token_invalido() -> None:
    async with _entorno_sqlite() as (_, _, ac):
        ac.cookies.set("access_token", "Bearer token_corrupto")
        response = await ac.get(PROTEGIDO)
        assert response.status_code == 401
        assert "inválido" in response.json()["detail"]


@pytest.mark.asyncio
async def test_token_sin_identificacion() -> None:
    token = create_access_token(data={"rol": "TESORERO"})
    async with _entorno_sqlite() as (_, _, ac):
        ac.cookies.set("access_token", f"Bearer {token}")
        response = await ac.get(PROTEGIDO)
        assert response.status_code == 401
        assert "sin identificación" in response.json()["detail"]


@pytest.mark.asyncio
async def test_usuario_no_encontrado() -> None:
    token = create_access_token(data={"sub": "nadie@test.com"})
    async with _entorno_sqlite() as (_, _, ac):
        ac.cookies.set("access_token", f"Bearer {token}")
        response = await ac.get(PROTEGIDO)
        assert response.status_code == 401
        assert "Usuario no encontrado" in response.json()["detail"]


@pytest.mark.asyncio
async def test_usuario_valido_continua_al_endpoint() -> None:
    async with _entorno_sqlite() as (factory, ctx, ac):
        async with factory() as session:
            await session.execute(delete(TasaCambio))
            await session.commit()

        token = create_access_token(
            data={"sub": "tes@condo.test", "id": ctx.tesorero_id, "rol": "TESORERO", "condominio_id": 1}
        )
        ac.cookies.set("access_token", f"Bearer {token}")
        response = await ac.get(PROTEGIDO)
        assert response.status_code == 404


class _FakeRedis:
    """Stub asíncrono mínimo compatible con las operaciones Redis usadas en dependencias."""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None) -> bool:
        del ex
        if nx and key in self.data:
            return False
        self.data[key] = value
        return True

    async def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if key in self.data:
                del self.data[key]
                removed += 1
        return removed


def _construir_request(
    *,
    method: str = "GET",
    path: str = "/test",
    query_string: bytes = b"",
    headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
    body: bytes = b"",
    path_params: dict[str, Any] | None = None,
    test_app: FastAPI | None = None,
) -> Request:
    """Construye un Starlette Request ASGI en memoria para pruebas unitarias deterministas."""
    raw_headers: list[tuple[bytes, bytes]] = []
    if headers:
        for k, v in headers.items():
            raw_headers.append((k.lower().encode("latin-1"), v.encode("latin-1")))
    if cookies:
        cookie_val = "; ".join(f"{k}={v}" for k, v in cookies.items())
        raw_headers.append((b"cookie", cookie_val.encode("latin-1")))

    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("latin-1"),
        "query_string": query_string,
        "headers": raw_headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "path_params": path_params or {},
    }
    if test_app is not None:
        scope["app"] = test_app

    sent = False

    async def _receive() -> dict[str, Any]:
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive=_receive)


def _nuevo_usuario(
    *,
    usuario_id: int | None = 1,
    condominio_id: int = 1,
    correo: str = "user@condo.test",
    cedula: str = "V-20000001",
    rol: str = "PROPIETARIO",
    es_activo: bool = True,
) -> Usuario:
    """Instancia un modelo Usuario ligero sin invocar PBKDF2."""
    return Usuario(
        id=usuario_id,
        condominio_id=condominio_id,
        nombre="Usuario Prueba",
        cedula=cedula,
        correo=correo,
        telefono="+584140000000",
        password_hash="pbkdf2_sha256$salt$digest",
        es_activo=es_activo,
        rol=rol,
    )


@asynccontextmanager
async def _entorno_sqlite_sin_seed() -> AsyncIterator[tuple[async_sessionmaker[AsyncSession], _FakeRedis]]:
    """Crea una base SQLite FK real ligera sin sembrar usuarios con PBKDF2."""
    engine, factory = await create_sqlite_fk_factory()
    try:
        yield factory, _FakeRedis()
    finally:
        await engine.dispose()


def test_roles_activos_validos_catalogo() -> None:
    assert ROLES_ACTIVOS_VALIDOS == frozenset(
        {
            "PROPIETARIO",
            "INQUILINO",
            "CONSERJE",
            "PRESIDENTE",
            "VICEPRESIDENTE",
            "SECRETARIO",
            "TESORERO",
            "VOCERO",
        }
    )


def test_extract_bearer_or_cookie_token_variantes() -> None:
    req_cookie_bearer = _construir_request(cookies={"access_token": "Bearer   tok_cookie"})
    assert extract_bearer_or_cookie_token(req_cookie_bearer) == "tok_cookie"

    req_cookie_raw = _construir_request(cookies={"access_token": "tok_raw"})
    assert extract_bearer_or_cookie_token(req_cookie_raw) == "tok_raw"

    req_ambos = _construir_request(
        cookies={"access_token": "Bearer tok_cookie"},
        headers={"Authorization": "Bearer tok_header"},
    )
    assert extract_bearer_or_cookie_token(req_ambos) == "tok_cookie"

    req_header = _construir_request(
        cookies={"access_token": ""},
        headers={"Authorization": "Bearer   tok_header  "},
    )
    assert extract_bearer_or_cookie_token(req_header) == "tok_header"

    req_lower = _construir_request(headers={"Authorization": "bearer tok_lower"})
    assert extract_bearer_or_cookie_token(req_lower) is None

    req_basic = _construir_request(headers={"Authorization": "Basic abc"})
    assert extract_bearer_or_cookie_token(req_basic) is None

    assert extract_bearer_or_cookie_token(_construir_request()) is None


def test_decodificar_payload_token_errores_y_exito() -> None:
    with pytest.raises(HTTPException) as exc_sin_token:
        _decodificar_payload_token(_construir_request())
    assert exc_sin_token.value.status_code == 401
    assert exc_sin_token.value.detail == "No autenticado"

    with pytest.raises(HTTPException) as exc_espacios:
        _decodificar_payload_token(_construir_request(headers={"Authorization": "Bearer    "}))
    assert exc_espacios.value.status_code == 401
    assert exc_espacios.value.detail == "No autenticado"

    expirado = create_access_token(data={"sub": "a@test.com"}, expires_delta=timedelta(seconds=-5))
    with pytest.raises(HTTPException) as exc_exp:
        _decodificar_payload_token(_construir_request(headers={"Authorization": f"Bearer {expirado}"}))
    assert exc_exp.value.status_code == 401
    assert exc_exp.value.detail == "Token expirado"

    with pytest.raises(HTTPException) as exc_inv:
        _decodificar_payload_token(_construir_request(cookies={"access_token": "Bearer corrupto"}))
    assert exc_inv.value.status_code == 401
    assert exc_inv.value.detail == "Token inválido"

    refresh_forjado = jwt.encode(
        {"sub": "a@test.com", "typ": "refresh", "iss": JWT_ISSUER, "aud": JWT_AUDIENCE, "iat": 1, "exp": 9999999999},
        derive_subkey("jwt-access"),
        algorithm=ALGORITHM,
    )
    with pytest.raises(HTTPException) as exc_typ:
        _decodificar_payload_token(_construir_request(headers={"Authorization": f"Bearer {refresh_forjado}"}))
    assert exc_typ.value.status_code == 401
    assert exc_typ.value.detail == "Token inválido"

    sin_sub = create_access_token(data={"rol": "PROPIETARIO"})
    with pytest.raises(HTTPException) as exc_sin_sub:
        _decodificar_payload_token(_construir_request(headers={"Authorization": f"Bearer {sin_sub}"}))
    assert exc_sin_sub.value.status_code == 401
    assert exc_sin_sub.value.detail == "Token sin identificación de usuario"

    sub_vacio = create_access_token(data={"sub": ""})
    with pytest.raises(HTTPException) as exc_sub_vacio:
        _decodificar_payload_token(_construir_request(headers={"Authorization": f"Bearer {sub_vacio}"}))
    assert exc_sub_vacio.value.status_code == 401
    assert exc_sub_vacio.value.detail == "Token sin identificación de usuario"

    valido = create_access_token(data={"sub": "ok@test.com", "condominio_id": 4})
    payload = _decodificar_payload_token(_construir_request(headers={"Authorization": f"Bearer {valido}"}))
    assert payload["sub"] == "ok@test.com"
    assert payload["condominio_id"] == 4


def test_extraer_claim_condominio_validacion_y_respaldo(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _extraer_claim_condominio({"condominio_id": 7}) == 7
    assert _extraer_claim_condominio({"condominio_id": True}) == DEFAULT_CONDOMINIO_ID
    assert _extraer_claim_condominio({"condominio_id": False}) == DEFAULT_CONDOMINIO_ID
    assert _extraer_claim_condominio({"condominio_id": 0}) == DEFAULT_CONDOMINIO_ID
    assert _extraer_claim_condominio({"condominio_id": -3}) == DEFAULT_CONDOMINIO_ID
    assert _extraer_claim_condominio({"condominio_id": "5"}) == DEFAULT_CONDOMINIO_ID
    assert _extraer_claim_condominio({"condominio_id": None}) == DEFAULT_CONDOMINIO_ID
    assert _extraer_claim_condominio({}) == DEFAULT_CONDOMINIO_ID

    monkeypatch.setattr(dependencies, "DEFAULT_CONDOMINIO_ID", 99)
    assert _extraer_claim_condominio({"condominio_id": 1}) == 1
    assert _extraer_claim_condominio({"condominio_id": 0}) == 99


@pytest.mark.asyncio
async def test_validar_sesion_no_revocada_redis_y_local() -> None:
    fake_redis = _FakeRedis()
    redis_arg = cast(aioredis.Redis, fake_redis)

    await _validar_sesion_no_revocada(redis_arg, cast(Usuario, SimpleNamespace(id=None)), "")
    await _validar_sesion_no_revocada(redis_arg, _nuevo_usuario(usuario_id=10), "sid-ok")

    fake_redis.data["revoked_user:10"] = "1"
    with pytest.raises(HTTPException) as exc_usr:
        await _validar_sesion_no_revocada(redis_arg, _nuevo_usuario(usuario_id=10), "sid-ok")
    assert exc_usr.value.status_code == 401
    assert exc_usr.value.detail == "Sesión revocada por la administración"

    fake_redis.data.clear()
    fake_redis.data["revoked_sid:sid-rev"] = "1"
    with pytest.raises(HTTPException) as exc_sid:
        await _validar_sesion_no_revocada(redis_arg, _nuevo_usuario(usuario_id=10), "sid-rev")
    assert exc_sid.value.status_code == 401
    assert exc_sid.value.detail == "Sesión revocada"

    await revoke_user_session(None, 22)
    with pytest.raises(HTTPException) as exc_loc_usr:
        await _validar_sesion_no_revocada(cast(aioredis.Redis, None), _nuevo_usuario(usuario_id=22), "")
    assert exc_loc_usr.value.status_code == 401
    assert exc_loc_usr.value.detail == "Sesión revocada por la administración"

    await revoke_session_id(None, "sid-local")
    with pytest.raises(HTTPException) as exc_loc_sid:
        await _validar_sesion_no_revocada(cast(aioredis.Redis, None), _nuevo_usuario(usuario_id=23), "sid-local")
    assert exc_loc_sid.value.status_code == 401
    assert exc_loc_sid.value.detail == "Sesión revocada"


@pytest.mark.asyncio
async def test_get_current_user_rls_tenant_y_revocacion_sqlite() -> None:
    async with _entorno_sqlite_sin_seed() as (factory, fake_redis):
        redis_arg = cast(aioredis.Redis, fake_redis)
        async with factory() as session:
            session.add_all(
                [
                    _nuevo_usuario(
                        usuario_id=None,
                        condominio_id=4,
                        correo="activo4@condo.test",
                        cedula="V-30000001",
                        rol="PROPIETARIO",
                        es_activo=True,
                    ),
                    _nuevo_usuario(
                        usuario_id=None,
                        condominio_id=0,
                        correo="cero@condo.test",
                        cedula="V-30000002",
                        rol="INQUILINO",
                        es_activo=True,
                    ),
                ]
            )
            await session.commit()

        async with factory() as session:
            tok_ausente = create_access_token(data={"sub": "noexiste@condo.test", "condominio_id": 3})
            with pytest.raises(HTTPException) as exc_missing:
                await get_current_user(
                    _construir_request(headers={"Authorization": f"Bearer {tok_ausente}"}),
                    db=session,
                    redis_conn=redis_arg,
                )
            assert exc_missing.value.status_code == 401
            assert exc_missing.value.detail == "Usuario no encontrado"
            assert session.sync_session.info["tenant_id"] == "3"

        async with factory() as session:
            tok_mismatch = create_access_token(data={"sub": "activo4@condo.test", "condominio_id": 2})
            with pytest.raises(HTTPException) as exc_mismatch:
                await get_current_user(
                    _construir_request(cookies={"access_token": f"Bearer {tok_mismatch}"}),
                    db=session,
                    redis_conn=redis_arg,
                )
            assert exc_mismatch.value.status_code == 401
            assert exc_mismatch.value.detail == "Token inválido para el condominio activo"

        async with factory() as session:
            tok_cero = create_access_token(data={"sub": "cero@condo.test", "condominio_id": 5})
            usr_cero = await get_current_user(
                _construir_request(headers={"Authorization": f"Bearer {tok_cero}"}),
                db=session,
                redis_conn=redis_arg,
            )
            assert usr_cero.correo == "cero@condo.test"
            assert session.sync_session.info["tenant_id"] == "5"

        async with factory() as session:
            tok_ok = create_access_token(data={"sub": "activo4@condo.test", "condominio_id": 4, "sid": "sid-4"})
            usr_ok = await get_current_user(
                _construir_request(cookies={"access_token": f"Bearer {tok_ok}"}),
                db=session,
                redis_conn=redis_arg,
            )
            assert usr_ok.correo == "activo4@condo.test"
            assert session.sync_session.info["tenant_id"] == "4"

            fake_redis.data["revoked_sid:sid-4"] = "1"
            with pytest.raises(HTTPException) as exc_rev_sid:
                await get_current_user(
                    _construir_request(headers={"Authorization": f"Bearer {tok_ok}"}),
                    db=session,
                    redis_conn=redis_arg,
                )
            assert exc_rev_sid.value.status_code == 401
            assert exc_rev_sid.value.detail == "Sesión revocada"

            fake_redis.data.clear()
            fake_redis.data[f"revoked_user:{usr_ok.id}"] = "1"
            with pytest.raises(HTTPException) as exc_rev_usr:
                await get_current_user(
                    _construir_request(headers={"Authorization": f"Bearer {tok_ok}"}),
                    db=session,
                    redis_conn=redis_arg,
                )
            assert exc_rev_usr.value.status_code == 401
            assert exc_rev_usr.value.detail == "Sesión revocada por la administración"


@pytest.mark.parametrize("rol_valido", sorted(ROLES_ACTIVOS_VALIDOS))
def test_verificar_usuario_activo_acepta_todos_roles_validos(rol_valido: str) -> None:
    verificar_usuario_activo(_nuevo_usuario(rol=rol_valido, es_activo=True))


@pytest.mark.parametrize(
    "candidato",
    [
        _nuevo_usuario(rol="PROPIETARIO", es_activo=False),
        _nuevo_usuario(rol="FANTASMA", es_activo=True),
        _nuevo_usuario(rol="INVITADO", es_activo=True),
        _nuevo_usuario(rol="", es_activo=True),
        _nuevo_usuario(rol="propietario", es_activo=True),
        SimpleNamespace(es_activo=1, rol="PROPIETARIO"),
        SimpleNamespace(rol="PROPIETARIO"),
        SimpleNamespace(es_activo=True, rol=None),
    ],
)
def test_verificar_usuario_activo_rechaza_inactivos_y_roles_invalidos(candidato: Any) -> None:
    with pytest.raises(HTTPException) as exc:
        verificar_usuario_activo(cast(Usuario, candidato))
    assert exc.value.status_code == 403
    assert exc.value.detail == "Cuenta pendiente de aprobación por la Junta de Condominio."


def test_verificar_roles_rbac() -> None:
    verificar_roles(_nuevo_usuario(rol="CONSERJE", es_activo=True), ("CONSERJE", "PRESIDENTE"))

    with pytest.raises(HTTPException) as exc_denegado:
        verificar_roles(_nuevo_usuario(rol="PROPIETARIO", es_activo=True), ("TESORERO", "PRESIDENTE"))
    assert exc_denegado.value.status_code == 403
    assert exc_denegado.value.detail == "No tiene permisos para ejecutar esta acción."

    with pytest.raises(HTTPException) as exc_inactivo:
        verificar_roles(_nuevo_usuario(rol="TESORERO", es_activo=False), ("TESORERO",))
    assert exc_inactivo.value.status_code == 403
    assert exc_inactivo.value.detail == "Cuenta pendiente de aprobación por la Junta de Condominio."


@pytest.mark.asyncio
async def test_helpers_usuario_opcional_y_override() -> None:
    assert _extraer_user_condo(_nuevo_usuario(condominio_id=8), 2) == 8
    assert _extraer_user_condo(_nuevo_usuario(condominio_id=0), 3) == 3
    assert _extraer_user_condo(cast(Usuario, SimpleNamespace(condominio_id=None)), 4) == 4
    assert _extraer_user_condo(cast(Usuario, SimpleNamespace()), 6) == 6

    activo = _nuevo_usuario(usuario_id=7, condominio_id=3, es_activo=True)
    assert _validar_usuario_en_tenant(None, 3) is None
    assert _validar_usuario_en_tenant(_nuevo_usuario(es_activo=False, condominio_id=3), 3) is None
    assert _validar_usuario_en_tenant(cast(Usuario, SimpleNamespace(es_activo=1, condominio_id=3)), 3) is None
    assert _validar_usuario_en_tenant(_nuevo_usuario(es_activo=True, condominio_id=2), 3) is None
    assert _validar_usuario_en_tenant(activo, 3) == (activo, 3)

    fake_redis = _FakeRedis()
    redis_arg = cast(aioredis.Redis, fake_redis)
    assert await _sesion_activa_valida(redis_arg, activo, None) is True
    assert await _sesion_activa_valida(redis_arg, activo, "sid-1") is True
    fake_redis.data["revoked_sid:sid-1"] = "1"
    assert await _sesion_activa_valida(redis_arg, activo, "sid-1") is False

    async with _entorno_sqlite_sin_seed() as (factory, _):
        local_app = FastAPI()
        async with factory() as session:
            req_sin_override = _construir_request(test_app=local_app)
            assert await _resolver_override_usuario(req_sin_override, session) is None

            try:
                local_app.dependency_overrides[get_current_user] = lambda: _nuevo_usuario(
                    condominio_id=6, es_activo=True
                )
                res_sync = await _resolver_override_usuario(req_sin_override, session)
                assert res_sync is not None
                assert session.sync_session.info["tenant_id"] == "6"

                async def _override_async() -> Usuario:
                    return _nuevo_usuario(condominio_id=0, es_activo=True)

                local_app.dependency_overrides[get_current_user] = _override_async
                res_async = await _resolver_override_usuario(req_sin_override, session)
                assert res_async is not None
                assert session.sync_session.info["tenant_id"] == str(DEFAULT_CONDOMINIO_ID)

                local_app.dependency_overrides[get_current_user] = lambda: _nuevo_usuario(es_activo=False)
                assert await _resolver_override_usuario(req_sin_override, session) is None

                local_app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(es_activo=1, condominio_id=2)
                assert await _resolver_override_usuario(req_sin_override, session) is None

                local_app.dependency_overrides[get_current_user] = lambda: None
                assert await _resolver_override_usuario(req_sin_override, session) is None
            finally:
                local_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_optional_active_user_sqlite_y_endpoint() -> None:
    async with _entorno_sqlite_sin_seed() as (factory, fake_redis):
        redis_arg = cast(aioredis.Redis, fake_redis)
        async with factory() as session:
            session.add_all(
                [
                    _nuevo_usuario(
                        usuario_id=None,
                        condominio_id=5,
                        correo="opt_ok@condo.test",
                        cedula="V-40000001",
                        rol="PROPIETARIO",
                        es_activo=True,
                    ),
                    _nuevo_usuario(
                        usuario_id=None,
                        condominio_id=5,
                        correo="opt_fantasma@condo.test",
                        cedula="V-40000002",
                        rol="FANTASMA",
                        es_activo=False,
                    ),
                ]
            )
            await session.commit()

        async with factory() as session:
            assert await _cargar_usuario_activo_desde_payload(session, redis_arg, {}) is None
            assert (
                await _cargar_usuario_activo_desde_payload(
                    session, redis_arg, {"sub": "fantasma_no@condo.test", "condominio_id": 7}
                )
                is None
            )
            assert session.sync_session.info["tenant_id"] == "7"
            assert (
                await _cargar_usuario_activo_desde_payload(
                    session, redis_arg, {"sub": "opt_fantasma@condo.test", "condominio_id": 5}
                )
                is None
            )
            assert (
                await _cargar_usuario_activo_desde_payload(
                    session, redis_arg, {"sub": "opt_ok@condo.test", "condominio_id": 2}
                )
                is None
            )
            fake_redis.data["revoked_sid:sid-opt"] = "1"
            assert (
                await _cargar_usuario_activo_desde_payload(
                    session, redis_arg, {"sub": "opt_ok@condo.test", "condominio_id": 5, "sid": "sid-opt"}
                )
                is None
            )
            fake_redis.data.clear()
            loaded = await _cargar_usuario_activo_desde_payload(
                session, redis_arg, {"sub": "opt_ok@condo.test", "condominio_id": 5}
            )
            assert loaded is not None
            assert loaded.correo == "opt_ok@condo.test"
            assert session.sync_session.info["tenant_id"] == "5"

        local_app = FastAPI()

        @local_app.get("/opcional")
        async def _ep_opcional(usuario: Usuario | None = Depends(get_optional_active_user)) -> dict[str, Any]:
            return {"correo": usuario.correo if usuario else None}

        async def _override_db() -> AsyncIterator[AsyncSession]:
            async with factory() as session:
                yield session

        try:
            local_app.dependency_overrides[get_db] = _override_db
            local_app.dependency_overrides[get_redis_client] = lambda: fake_redis

            async with AsyncClient(transport=ASGITransport(app=local_app), base_url="http://testserver") as ac:
                assert (await ac.get("/opcional")).json() == {"correo": None}
                assert (await ac.get("/opcional", headers={"Authorization": "Bearer roto"})).json() == {"correo": None}

                exp_tok = create_access_token(data={"sub": "opt_ok@condo.test"}, expires_delta=timedelta(seconds=-5))
                assert (await ac.get("/opcional", headers={"Authorization": f"Bearer {exp_tok}"})).json() == {
                    "correo": None
                }

                tok_ok = create_access_token(data={"sub": "opt_ok@condo.test", "condominio_id": 5})
                assert (await ac.get("/opcional", headers={"Authorization": f"Bearer {tok_ok}"})).json() == {
                    "correo": "opt_ok@condo.test"
                }

                tok_fantasma = create_access_token(data={"sub": "opt_fantasma@condo.test", "condominio_id": 5})
                assert (await ac.get("/opcional", headers={"Authorization": f"Bearer {tok_fantasma}"})).json() == {
                    "correo": None
                }

                local_app.dependency_overrides[get_current_user] = lambda: _nuevo_usuario(
                    correo="override@condo.test", es_activo=True
                )
                assert (await ac.get("/opcional")).json() == {"correo": "override@condo.test"}

                local_app.dependency_overrides[get_current_user] = lambda: _nuevo_usuario(
                    correo="inactivo@condo.test", es_activo=False
                )
                assert (await ac.get("/opcional")).json() == {"correo": None}
        finally:
            local_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_idempotency_slot_helpers_y_limites() -> None:
    exc = IdempotencyReplayException(201, {"id": 9})
    assert str(exc) == "Idempotency replay"
    assert exc.status_code == 201
    assert exc.body == {"id": 9}

    assert _decode_response_json(Response(content=b'{"id":42}', media_type="application/json")) == {"id": 42}
    assert _decode_response_json(Response(content=b"")) is None
    assert _decode_response_json(Response(content=b"\xff\xfe")) is None
    assert _decode_response_json(Response(content=b"no-json")) is None

    fake_redis = _FakeRedis()
    redis_arg = cast(aioredis.Redis, fake_redis)

    req_vacio = _construir_request()
    await _release_request_slot(req_vacio)
    await _finalize_request_slot(req_vacio, Response(status_code=200))

    req_slot = _construir_request()
    fake_redis.data["k_rel"] = '{"state":"IN_PROGRESS"}'
    req_slot.state.idempotency_slot = ActiveIdempotencySlot(redis_conn=redis_arg, redis_key="k_rel", payload_hash="h1")
    await _release_request_slot(req_slot)
    assert req_slot.state.idempotency_slot is None
    assert "k_rel" not in fake_redis.data

    for codigo in (199, 300, 400, 500):
        key = f"k_{codigo}"
        fake_redis.data[key] = '{"state":"IN_PROGRESS"}'
        req = _construir_request()
        req.state.idempotency_slot = ActiveIdempotencySlot(redis_conn=redis_arg, redis_key=key, payload_hash="h")
        await _finalize_request_slot(req, Response(status_code=codigo, content=b'{"e":1}'))
        assert req.state.idempotency_slot is None
        assert key not in fake_redis.data

    for codigo in (200, 299):
        key = f"k_ok_{codigo}"
        req = _construir_request()
        req.state.idempotency_slot = ActiveIdempotencySlot(redis_conn=redis_arg, redis_key=key, payload_hash="h_ok")
        await _finalize_request_slot(
            req,
            Response(status_code=codigo, content=b'{"saved":true}', media_type="application/json"),
        )
        assert req.state.idempotency_slot is None
        guardado = json.loads(fake_redis.data[key])
        assert guardado == {
            "state": "COMPLETED",
            "payload_hash": "h_ok",
            "status_code": codigo,
            "body": {"saved": True},
        }


@pytest.mark.asyncio
async def test_compute_hash_y_claim_idempotency_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    req_body = _construir_request(method="POST", path="/api/pagos", body=b'{"monto":10}')
    assert await _compute_request_payload_hash(req_body, hash_body=True) == hashlib.sha256(b'{"monto":10}').hexdigest()

    req_meta = _construir_request(
        method="POST",
        path="/api/items",
        query_string=b"a=1",
        headers={"Content-Length": "12"},
        body=b'{"ignorar":1}',
    )
    esperado_meta = hashlib.sha256(b"POST:/api/items:a=1:12").hexdigest()
    assert await _compute_request_payload_hash(req_meta, hash_body=False) == esperado_meta

    req_meta_vacio = _construir_request(method="GET", path="/api/items")
    assert (
        await _compute_request_payload_hash(req_meta_vacio, hash_body=False)
        == hashlib.sha256(b"GET:/api/items::").hexdigest()
    )

    fake_redis = _FakeRedis()
    redis_arg = cast(aioredis.Redis, fake_redis)

    req_first = _construir_request(method="POST", path="/api/pagos", body=b'{"monto":10}')
    await _claim_idempotency_slot(req_first, redis_arg, "idemp:1:1:pagos:k1")
    slot = req_first.state.idempotency_slot
    assert isinstance(slot, ActiveIdempotencySlot)
    assert slot.redis_conn is redis_arg
    assert slot.redis_key == "idemp:1:1:pagos:k1"
    assert slot.payload_hash == hashlib.sha256(b'{"monto":10}').hexdigest()

    with pytest.raises(HTTPException) as exc_in_prog:
        await _claim_idempotency_slot(
            _construir_request(method="POST", path="/api/pagos", body=b'{"monto":10}'),
            redis_arg,
            "idemp:1:1:pagos:k1",
        )
    assert exc_in_prog.value.status_code == 409
    assert exc_in_prog.value.detail == "Petición duplicada detectada (operación en curso)."

    with pytest.raises(HTTPException) as exc_diff:
        await _claim_idempotency_slot(
            _construir_request(method="POST", path="/api/pagos", body=b'{"monto":99}'),
            redis_arg,
            "idemp:1:1:pagos:k1",
        )
    assert exc_diff.value.status_code == 409
    assert exc_diff.value.detail == "Idempotency-Key reutilizada con un cuerpo de solicitud distinto."

    await store_idempotency_response(
        redis_arg,
        "idemp:1:1:pagos:k1",
        IdempotencyResponsePayload(payload_hash=slot.payload_hash, status_code=202, body={"ok": 202}),
    )
    with pytest.raises(IdempotencyReplayException) as exc_replay:
        await _claim_idempotency_slot(
            _construir_request(method="POST", path="/api/pagos", body=b'{"monto":10}'),
            redis_arg,
            "idemp:1:1:pagos:k1",
        )
    assert exc_replay.value.status_code == 202
    assert exc_replay.value.body == {"ok": 202}

    async def _acquire_sin_detalle(*_args: Any, **_kwargs: Any) -> IdempotencySlotResult:
        return IdempotencySlotResult(acquired=False, replay_status=None, conflict_detail=None)

    monkeypatch.setattr(dependencies, "acquire_idempotency_slot", _acquire_sin_detalle)
    with pytest.raises(HTTPException) as exc_fallback:
        await _claim_idempotency_slot(req_meta_vacio, redis_arg, "k_fallback", hash_body=False)
    assert exc_fallback.value.status_code == 409
    assert exc_fallback.value.detail == "Petición duplicada detectada (Idempotency-Key ya procesada)."


@pytest.mark.asyncio
async def test_resolver_guardia_idempotencia_roles_scope_y_usuario_id() -> None:
    fake_redis = _FakeRedis()
    redis_arg = cast(aioredis.Redis, fake_redis)

    politica_roles = _PoliticaIdempotencia(
        scope_template="recibos:{recibo_id}:pagar",
        roles=("TESORERO",),
        require_active=True,
        hash_body=True,
    )
    req_prop = _construir_request(method="POST", path="/recibos/77/pagar", path_params={"recibo_id": 77}, body=b"{}")
    with pytest.raises(HTTPException) as exc_rol:
        await _resolver_guardia_idempotencia(
            politica_roles,
            _ContextoIdempotencia(
                request=req_prop,
                usuario=_nuevo_usuario(usuario_id=42, condominio_id=5, rol="PROPIETARIO", es_activo=True),
                idempotency_key="clave-1234",
                redis_conn=redis_arg,
            ),
        )
    assert exc_rol.value.status_code == 403
    assert exc_rol.value.detail == "No tiene permisos para ejecutar esta acción."
    assert fake_redis.data == {}
    assert getattr(req_prop.state, "idempotency_slot", None) is None

    req_ok = _construir_request(method="POST", path="/recibos/77/pagar", path_params={"recibo_id": 77}, body=b"{}")
    await _resolver_guardia_idempotencia(
        politica_roles,
        _ContextoIdempotencia(
            request=req_ok,
            usuario=_nuevo_usuario(usuario_id=42, condominio_id=5, rol="TESORERO", es_activo=True),
            idempotency_key="clave-1234",
            redis_conn=redis_arg,
        ),
    )
    assert "idemp:5:42:recibos:77:pagar:clave-1234" in fake_redis.data

    politica_inactivo = _PoliticaIdempotencia(scope_template="alta", roles=None, require_active=True, hash_body=True)
    with pytest.raises(HTTPException) as exc_inactivo:
        await _resolver_guardia_idempotencia(
            politica_inactivo,
            _ContextoIdempotencia(
                request=_construir_request(method="POST", body=b"{}"),
                usuario=_nuevo_usuario(usuario_id=None, condominio_id=0, rol="FANTASMA", es_activo=False),
                idempotency_key="clave-5678",
                redis_conn=redis_arg,
            ),
        )
    assert exc_inactivo.value.status_code == 403
    assert "idemp:1:0:alta:clave-5678" not in fake_redis.data

    politica_no_activo = _PoliticaIdempotencia(scope_template="alta", roles=None, require_active=False, hash_body=True)
    await _resolver_guardia_idempotencia(
        politica_no_activo,
        _ContextoIdempotencia(
            request=_construir_request(method="POST", body=b"{}"),
            usuario=_nuevo_usuario(usuario_id=None, condominio_id=0, rol="FANTASMA", es_activo=False),
            idempotency_key="clave-5678",
            redis_conn=redis_arg,
        ),
    )
    assert "idemp:1:0:alta:clave-5678" in fake_redis.data


@pytest.mark.asyncio
async def test_idempotent_api_route_y_dependencias_http() -> None:
    fake_redis = _FakeRedis()
    local_app = FastAPI()
    router = APIRouter(route_class=IdempotentAPIRoute)
    contadores = {"hash_body": 0, "solo_meta": 0, "anon": 0, "falla": 0}
    usuario_actual = _nuevo_usuario(usuario_id=9, condominio_id=3, rol="TESORERO", es_activo=True)

    @router.post(
        "/items/{item_id}/body",
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(exigir_idempotencia("items:{item_id}", roles=("TESORERO",), hash_body=True))],
    )
    async def _ep_body(item_id: int) -> dict[str, int]:
        contadores["hash_body"] += 1
        return {"item_id": item_id, "calls": contadores["hash_body"]}

    @router.post(
        "/items/meta",
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(exigir_idempotencia("meta", require_active=False, hash_body=False))],
    )
    async def _ep_meta() -> dict[str, int]:
        contadores["solo_meta"] += 1
        return {"calls": contadores["solo_meta"]}

    @router.post(
        "/anonimo",
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(exigir_idempotencia_anonima("registro"))],
    )
    async def _ep_anon() -> dict[str, int]:
        contadores["anon"] += 1
        return {"calls": contadores["anon"]}

    @router.post(
        "/falla/{modo}",
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(exigir_idempotencia_anonima("falla"))],
    )
    async def _ep_falla(modo: str) -> Response:
        contadores["falla"] += 1
        if modo == "400":
            return JSONResponse(status_code=400, content={"error": "bad"})
        if modo == "http":
            raise HTTPException(status_code=422, detail="invalido")
        if modo == "boom":
            raise RuntimeError("boom_idemp")
        return JSONResponse(status_code=201, content={"calls": contadores["falla"]})

    local_app.include_router(router)
    try:
        local_app.dependency_overrides[get_current_user] = lambda: usuario_actual
        local_app.dependency_overrides[get_redis_client] = lambda: fake_redis

        async with AsyncClient(transport=ASGITransport(app=local_app), base_url="http://testserver") as ac:
            assert (await ac.post("/items/10/body", json={"a": 1})).status_code == 422
            assert (
                await ac.post("/items/10/body", json={"a": 1}, headers={"Idempotency-Key": "1234567"})
            ).status_code == 422
            assert (
                await ac.post("/items/10/body", json={"a": 1}, headers={"Idempotency-Key": "k" * 129})
            ).status_code == 422

            clave_min = "12345678"
            clave_max = "k" * 128
            r1 = await ac.post("/items/10/body", json={"a": 1}, headers={"Idempotency-Key": clave_min})
            assert r1.status_code == 201
            assert r1.json() == {"item_id": 10, "calls": 1}
            assert "X-Idempotency-Replayed" not in r1.headers
            assert f"idemp:3:9:items:10:{clave_min}" in fake_redis.data

            r_rep = await ac.post("/items/10/body", json={"a": 1}, headers={"Idempotency-Key": clave_min})
            assert r_rep.status_code == 201
            assert r_rep.json() == {"item_id": 10, "calls": 1}
            assert r_rep.headers["X-Idempotency-Replayed"] == "true"
            assert contadores["hash_body"] == 1

            r_409 = await ac.post("/items/10/body", json={"a": 2}, headers={"Idempotency-Key": clave_min})
            assert r_409.status_code == 409
            assert r_409.json()["detail"] == "Idempotency-Key reutilizada con un cuerpo de solicitud distinto."

            r_max = await ac.post("/items/10/body", json={"a": 1}, headers={"Idempotency-Key": clave_max})
            assert r_max.status_code == 201

            usuario_actual = _nuevo_usuario(usuario_id=9, condominio_id=3, rol="PROPIETARIO", es_activo=True)
            r_403 = await ac.post("/items/10/body", json={"a": 1}, headers={"Idempotency-Key": "prop-no-slot"})
            assert r_403.status_code == 403
            assert r_403.json()["detail"] == "No tiene permisos para ejecutar esta acción."
            assert "idemp:3:9:items:10:prop-no-slot" not in fake_redis.data
            assert _local_idempotency_records == {}

            usuario_actual = _nuevo_usuario(usuario_id=9, condominio_id=3, rol="TESORERO", es_activo=False)
            r_inact = await ac.post("/items/10/body", json={"a": 1}, headers={"Idempotency-Key": "inact-no-slot"})
            assert r_inact.status_code == 403
            assert r_inact.json()["detail"] == "Cuenta pendiente de aprobación por la Junta de Condominio."
            assert "idemp:3:9:items:10:inact-no-slot" not in fake_redis.data

            usuario_actual = _nuevo_usuario(usuario_id=9, condominio_id=3, rol="FANTASMA", es_activo=False)
            m1 = await ac.post("/items/meta", json={"a": 1}, headers={"Idempotency-Key": "meta-key-1"})
            m2 = await ac.post("/items/meta", json={"b": 2}, headers={"Idempotency-Key": "meta-key-1"})
            assert m1.status_code == 201
            assert m2.status_code == 201
            assert m2.headers["X-Idempotency-Replayed"] == "true"
            assert contadores["solo_meta"] == 1
            m_diff_len = await ac.post("/items/meta", json={"bbb": 222}, headers={"Idempotency-Key": "meta-key-1"})
            assert m_diff_len.status_code == 409

            assert (await ac.post("/anonimo", json={"x": 1})).status_code == 422
            assert (await ac.post("/anonimo", json={"x": 1}, headers={"Idempotency-Key": "1234567"})).status_code == 422
            assert (await ac.post("/anonimo", json={"x": 1}, headers={"Idempotency-Key": "a" * 129})).status_code == 422
            a_min = await ac.post("/anonimo", json={"x": 1}, headers={"Idempotency-Key": "12345678"})
            a_max = await ac.post("/anonimo", json={"x": 1}, headers={"Idempotency-Key": "b" * 128})
            assert a_min.status_code == 201
            assert a_max.status_code == 201
            a1 = await ac.post("/anonimo", json={"x": 1}, headers={"Idempotency-Key": "anon-1234"})
            a2 = await ac.post("/anonimo", json={"x": 1}, headers={"Idempotency-Key": "anon-1234"})
            assert a1.status_code == 201
            assert a2.status_code == 201
            assert a2.headers["X-Idempotency-Replayed"] == "true"
            assert contadores["anon"] == 3
            assert f"idemp:{DEFAULT_CONDOMINIO_ID}:0:registro:anon-1234" in fake_redis.data
            a_409 = await ac.post("/anonimo", json={"x": 2}, headers={"Idempotency-Key": "anon-1234"})
            assert a_409.status_code == 409
            assert a_409.json()["detail"] == "Idempotency-Key reutilizada con un cuerpo de solicitud distinto."

            clave_lib = "libera-key-1"
            redis_lib = f"idemp:{DEFAULT_CONDOMINIO_ID}:0:falla:{clave_lib}"
            assert (await ac.post("/falla/400", headers={"Idempotency-Key": clave_lib})).status_code == 400
            assert redis_lib not in fake_redis.data
            assert (await ac.post("/falla/http", headers={"Idempotency-Key": clave_lib})).status_code == 422
            assert redis_lib not in fake_redis.data
            with pytest.raises(RuntimeError, match="boom_idemp"):
                await ac.post("/falla/boom", headers={"Idempotency-Key": clave_lib})
            assert redis_lib not in fake_redis.data
            ok_despues = await ac.post("/falla/ok", headers={"Idempotency-Key": clave_lib})
            assert ok_despues.status_code == 201
            assert ok_despues.json() == {"calls": 4}
    finally:
        local_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_exigir_idempotencia_con_get_current_user_sqlite() -> None:
    async with _entorno_sqlite_sin_seed() as (factory, fake_redis):
        async with factory() as session:
            session.add(
                _nuevo_usuario(
                    usuario_id=None,
                    condominio_id=2,
                    correo="tes2@condo.test",
                    cedula="V-50000001",
                    rol="TESORERO",
                    es_activo=True,
                )
            )
            await session.commit()

        local_app = FastAPI()
        router = APIRouter(route_class=IdempotentAPIRoute)
        llamadas = 0

        @router.post(
            "/operacion",
            status_code=status.HTTP_201_CREATED,
            dependencies=[Depends(exigir_idempotencia("op_real", roles=("TESORERO",)))],
        )
        async def _ep_real() -> dict[str, int]:
            nonlocal llamadas
            llamadas += 1
            return {"ok": llamadas}

        local_app.include_router(router)

        async def _override_db() -> AsyncIterator[AsyncSession]:
            async with factory() as session:
                yield session

        try:
            local_app.dependency_overrides[get_db] = _override_db
            local_app.dependency_overrides[get_redis_client] = lambda: fake_redis

            tok = create_access_token(data={"sub": "tes2@condo.test", "condominio_id": 2})
            headers = {"Authorization": f"Bearer {tok}", "Idempotency-Key": "real-idemp-01"}
            async with AsyncClient(transport=ASGITransport(app=local_app), base_url="http://testserver") as ac:
                r1 = await ac.post("/operacion", json={"n": 1}, headers=headers)
                r2 = await ac.post("/operacion", json={"n": 1}, headers=headers)
                assert r1.status_code == 201
                assert r2.status_code == 201
                assert r2.headers["X-Idempotency-Replayed"] == "true"
                assert r2.json() == {"ok": 1}
                assert llamadas == 1
        finally:
            local_app.dependency_overrides.clear()
