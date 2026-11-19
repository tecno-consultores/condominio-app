# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
"""Pruebas unitarias del cliente KeyDB/Redis, revocación Fail-Closed, lockout Lua e idempotencia."""

from __future__ import annotations

import json
import runpy
import time
from collections.abc import Generator
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
import redis.asyncio as aioredis
from fastapi import HTTPException
from redis.exceptions import ConnectionError as RedisConnectionError

from src import redis_client, redis_idempotency
from src.redis_client import (
    LOGIN_ACCOUNT_MAX_ATTEMPTS,
    LOGIN_MAX_ATTEMPTS,
    MAX_LOCAL_SECURITY_ENTRIES,
    IdempotencyResponsePayload,
    IdempotencySlotResult,
    __all__ as redis_exports,
    _local_grace_tokens,
    _local_idempotency_keys,
    _local_idempotency_records,
    acquire_idempotency_slot,
    build_idempotency_key,
    build_qr_nonce_key,
    build_scoped_idempotency_key,
    burn_qr_nonce,
    check_and_set_idempotency_key,
    clear_login_failures,
    clear_user_session_revocation,
    get_redis_client,
    get_refresh_token_from_grace_period,
    is_login_locked_out,
    is_qr_nonce_burned,
    is_session_id_revoked,
    is_user_session_revoked,
    mark_refresh_jti_used,
    record_login_failure,
    release_idempotency_slot,
    reset_local_security_state,
    revoke_session_id,
    revoke_user_session,
    rotate_refresh_token_with_grace_period,
    store_idempotency_response,
)
from src.redis_idempotency import (
    GRACE_PERIOD_SECONDS,
    IDEMPOTENCY_TTL_SECONDS,
    _evaluate_existing_idempotency_record,
    _get_local_idemp_record,
    _store_local_idemp_record,
    has_local_ttl,
    is_production_env,
    purge_expired_map,
    raise_if_prod,
    store_local_ttl,
)

_UNSET: object = object()
_DETAIL_KEYDB_503 = "Servicio de seguridad KeyDB no disponible."


class _FakeAsyncRedis:
    """Protocolo mínimo asíncrono compatible con redis.asyncio.Redis para pruebas en memoria."""

    def __init__(self) -> None:
        self.kv: dict[str, tuple[Any, float | None]] = {}
        self.set_calls: list[tuple[str, str, bool, int | None]] = []
        self.delete_calls: list[tuple[str, ...]] = []
        self.eval_calls: list[tuple[str, int, tuple[Any, ...]]] = []
        self.eval_return_override: Any = _UNSET

    def _purge_if_expired(self, key: str) -> None:
        entry = self.kv.get(key)
        if entry is not None and entry[1] is not None and entry[1] <= time.monotonic():
            self.kv.pop(key, None)

    async def get(self, key: str) -> Any:
        self._purge_if_expired(key)
        entry = self.kv.get(key)
        return entry[0] if entry is not None else None

    async def set(
        self,
        key: str,
        value: str,
        *,
        nx: bool = False,
        ex: int | None = None,
    ) -> bool:
        self.set_calls.append((key, value, nx, ex))
        self._purge_if_expired(key)
        if nx and key in self.kv:
            return False
        exp = time.monotonic() + ex if ex is not None else None
        self.kv[key] = (value, exp)
        return True

    async def delete(self, *keys: str) -> int:
        self.delete_calls.append(keys)
        deleted = 0
        for key in keys:
            if self.kv.pop(key, None) is not None:
                deleted += 1
        return deleted

    async def eval(self, script: str, numkeys: int, *keys_and_args: Any) -> Any:
        self.eval_calls.append((script, numkeys, keys_and_args))
        if self.eval_return_override is not _UNSET:
            return self.eval_return_override
        assert numkeys == 1
        key = str(keys_and_args[0])
        ttl = int(keys_and_args[1])
        self._purge_if_expired(key)
        entry = self.kv.get(key)
        count = int(entry[0]) + 1 if entry is not None else 1
        exp = entry[1] if (entry is not None and entry[1] is not None) else time.monotonic() + ttl
        self.kv[key] = (str(count), exp)
        return count


class _FailingAsyncRedis:
    """Inyector de fallos de red Redis/KeyDB para validar fallback local vs Fail-Closed."""

    async def get(self, _key: str) -> str | None:
        raise RedisConnectionError("KeyDB no alcanzable")

    async def set(self, _key: str, _value: str, *, nx: bool = False, ex: int | None = None) -> bool:
        del nx, ex
        raise RedisConnectionError("KeyDB no alcanzable")

    async def delete(self, *_keys: str) -> int:
        raise RedisConnectionError("KeyDB no alcanzable")

    async def eval(self, _script: str, _numkeys: int, *_keys_and_args: Any) -> int:
        raise RedisConnectionError("KeyDB no alcanzable")


def _instalar_reloj_falso(monkeypatch: pytest.MonkeyPatch, initial: float = 1000.0) -> list[float]:
    """Reemplaza time.monotonic en los módulos objetivo sin alterar el loop asyncio."""
    clock = [initial]
    fake_time = SimpleNamespace(monotonic=lambda: clock[0])
    monkeypatch.setattr(redis_client, "time", fake_time)
    monkeypatch.setattr(redis_idempotency, "time", fake_time)
    return clock


@pytest.fixture(autouse=True)
def _aislar_estado_redis() -> Generator[None]:
    """Limpia estado local y singleton global antes y después de cada test."""
    reset_local_security_state()
    redis_client._redis_client = None
    try:
        yield
    finally:
        reset_local_security_state()
        redis_client._redis_client = None


async def test_exports_y_singleton_get_redis_client() -> None:
    """Valida __all__, inicialización perezosa singleton y reinicio limpio del cliente."""
    assert len(redis_exports) == 30
    for symbol in redis_exports:
        assert hasattr(redis_client, symbol)

    c1 = get_redis_client()
    c2 = get_redis_client()
    assert c1 is c2
    await c1.aclose()

    redis_client._redis_client = None
    c3 = get_redis_client()
    assert c3 is not c1
    await c3.aclose()


async def test_constantes_entorno_y_from_url_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica constantes, script Lua exacto, kwargs de from_url y limpieza de mapas locales."""
    assert LOGIN_MAX_ATTEMPTS == 5
    assert LOGIN_ACCOUNT_MAX_ATTEMPTS == 10
    assert redis_client.LOGIN_LOCKOUT_SECONDS == 900
    assert redis_client.QR_NONCE_TTL_SECONDS == 259_200
    assert GRACE_PERIOD_SECONDS == 5
    assert IDEMPOTENCY_TTL_SECONDS == 86_400
    assert MAX_LOCAL_SECURITY_ENTRIES == 1024
    assert redis_client._LUA_INCR_EXPIRE == (
        "local c = redis.call('INCR', KEYS[1]); "
        "if c == 1 or redis.call('TTL', KEYS[1]) < 0 then "
        "redis.call('EXPIRE', KEYS[1], tonumber(ARGV[1])) "
        "end; "
        "return c"
    )

    mod_path = redis_client.__file__
    assert mod_path is not None
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("REFRESH_TOKEN_EXPIRE_DAYS", raising=False)
    ns_default = runpy.run_path(str(Path(mod_path)))
    assert ns_default["REDIS_URL"] == "redis://localhost:6379/0"
    assert ns_default["REFRESH_TOKEN_EXPIRE_DAYS"] == 7
    assert ns_default["REFRESH_USED_TTL_SECONDS"] == 604_800
    assert ns_default["REVOKED_USER_TTL_SECONDS"] == 604_800

    monkeypatch.setenv("REDIS_URL", "redis://custom-keydb:6380/2")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "3")
    ns_clamped = runpy.run_path(str(Path(mod_path)))
    assert ns_clamped["REDIS_URL"] == "redis://custom-keydb:6380/2"
    assert ns_clamped["REFRESH_TOKEN_EXPIRE_DAYS"] == 7

    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "10")
    ns_custom = runpy.run_path(str(Path(mod_path)))
    assert ns_custom["REFRESH_TOKEN_EXPIRE_DAYS"] == 10
    assert ns_custom["REFRESH_USED_TTL_SECONDS"] == 864_000
    assert ns_custom["REVOKED_USER_TTL_SECONDS"] == 864_000

    from_url_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    sentinel = _FakeAsyncRedis()

    def _fake_from_url(*args: Any, **kwargs: Any) -> Any:
        from_url_calls.append((args, kwargs))
        return sentinel

    monkeypatch.setattr(redis_client.redis, "from_url", _fake_from_url)
    redis_client._redis_client = None
    assert get_redis_client() is cast(Any, sentinel)
    assert get_redis_client() is cast(Any, sentinel)
    assert from_url_calls == [((redis_client.REDIS_URL,), {"decode_responses": True})]

    redis_client._local_revoked_users[1] = 999.0
    redis_client._local_revoked_sids["s"] = 999.0
    redis_client._local_burned_qrs["q"] = 999.0
    redis_client._local_login_failures["l"] = (1, 999.0)
    redis_client._local_used_refresh_jtis["j"] = 999.0
    _local_idempotency_keys["k"] = 999.0
    _local_idempotency_records["r"] = ("{}", 999.0)
    _local_grace_tokens["g"] = ("t", 999.0)
    reset_local_security_state()
    assert redis_client._local_revoked_users == {}
    assert redis_client._local_revoked_sids == {}
    assert redis_client._local_burned_qrs == {}
    assert redis_client._local_login_failures == {}
    assert redis_client._local_used_refresh_jtis == {}
    assert _local_idempotency_keys == {}
    assert _local_idempotency_records == {}
    assert _local_grace_tokens == {}


async def test_revocacion_usuario_y_sid_con_redis_y_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cubre revocación de usuario y sid en Redis real simulado y fallback local no-prod."""
    monkeypatch.setenv("APP_ENV", "development")
    fake = _FakeAsyncRedis()
    client = cast(aioredis.Redis, fake)

    assert await is_user_session_revoked(client, 10) is False
    await revoke_user_session(client, 10, ttl_seconds=60)
    assert await is_user_session_revoked(client, 10) is True
    await clear_user_session_revocation(client, 10)
    assert await is_user_session_revoked(client, 10) is False

    # Soporte de bytes desde Redis en _read_redis_flag
    fake.kv["revoked_user:11"] = (b"1", None)
    assert await is_user_session_revoked(client, 11) is True

    # SID vacío es no-op
    await revoke_session_id(client, "   ")
    assert await is_session_id_revoked(client, "   ") is False

    await revoke_session_id(client, "sid-abc", ttl_seconds=60)
    assert await is_session_id_revoked(client, "sid-abc") is True

    # Fallback local ante cliente None o error de conexión en desarrollo
    failing = cast(aioredis.Redis, _FailingAsyncRedis())
    await revoke_user_session(None, 22, ttl_seconds=60)
    assert await is_user_session_revoked(failing, 22) is True
    await clear_user_session_revocation(failing, 22)
    assert await is_user_session_revoked(None, 22) is False

    await revoke_session_id(failing, "sid-local", ttl_seconds=60)
    assert await is_session_id_revoked(None, "sid-local") is True


async def test_revocacion_claves_ttls_y_fallos_en_desarrollo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida claves exactas, TTL por defecto/mínimo 1s, coerción int y no-op de SID vacío en prod."""
    monkeypatch.setenv("APP_ENV", "development")
    fake = _FakeAsyncRedis()
    client = cast(aioredis.Redis, fake)
    failing = cast(aioredis.Redis, _FailingAsyncRedis())

    await revoke_user_session(client, cast(Any, "44"))
    assert fake.set_calls[-1] == ("revoked_user:44", "1", False, redis_client.REVOKED_USER_TTL_SECONDS)
    assert 44 not in redis_client._local_revoked_users
    await clear_user_session_revocation(client, 44)
    assert fake.delete_calls[-1] == ("revoked_user:44",)

    await revoke_user_session(client, 45, ttl_seconds=0)
    assert fake.set_calls[-1] == ("revoked_user:45", "1", False, 1)

    fake.kv["revoked_user:46"] = ("0", None)
    fake.kv["revoked_user:47"] = (b"0", None)
    assert await is_user_session_revoked(client, 46) is False
    assert await is_user_session_revoked(client, 47) is False

    await revoke_user_session(failing, cast(Any, "23"), ttl_seconds=30)
    assert 23 in redis_client._local_revoked_users
    assert await is_user_session_revoked(None, cast(Any, "23")) is True
    await clear_user_session_revocation(None, cast(Any, "23"))
    assert 23 not in redis_client._local_revoked_users
    assert await is_user_session_revoked(failing, 999) is False

    clock = _instalar_reloj_falso(monkeypatch, 500.0)
    await revoke_user_session(None, 24, ttl_seconds=5)
    clock[0] = 505.0
    assert await is_user_session_revoked(None, 24) is False
    assert 24 not in redis_client._local_revoked_users

    await revoke_session_id(client, "  sid-trim  ")
    assert fake.set_calls[-1] == ("revoked_sid:sid-trim", "1", False, redis_client.REVOKED_USER_TTL_SECONDS)
    assert "sid-trim" not in redis_client._local_revoked_sids
    assert await is_session_id_revoked(client, " sid-trim ") is True

    await revoke_session_id(client, "sid-min", ttl_seconds=-3)
    assert fake.set_calls[-1] == ("revoked_sid:sid-min", "1", False, 1)

    await revoke_session_id(None, "sid-none", ttl_seconds=20)
    assert "sid-none" in redis_client._local_revoked_sids
    assert await is_session_id_revoked(failing, " sid-none ") is True
    assert await is_session_id_revoked(failing, "sid-inexistente") is False

    # SID vacío retorna temprano sin tocar Redis ni lanzar 503 en producción
    monkeypatch.setenv("APP_ENV", "production")
    calls_before = len(fake.set_calls)
    await revoke_session_id(None, "   ")
    await revoke_session_id(client, "")
    assert len(fake.set_calls) == calls_before
    assert await is_session_id_revoked(None, "   ") is False


async def test_login_lockout_lua_y_fallback_local(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica contador Lua atómico, bloqueo por IP (>=5), bloqueo por cuenta (>=10) y limpieza."""
    monkeypatch.setenv("APP_ENV", "development")
    fake = _FakeAsyncRedis()
    client = cast(aioredis.Redis, fake)

    for idx in range(LOGIN_MAX_ATTEMPTS - 1):
        intentos = await record_login_failure(client, "10.0.0.1", "Vecino@Condo.TEST ")
        assert intentos == idx + 1
        assert await is_login_locked_out(client, "10.0.0.1", "vecino@condo.test") is False

    assert await record_login_failure(client, "10.0.0.1", "vecino@condo.test") == LOGIN_MAX_ATTEMPTS
    assert await is_login_locked_out(client, "10.0.0.1", "vecino@condo.test") is True

    await clear_login_failures(client, "10.0.0.1", "vecino@condo.test")
    assert await is_login_locked_out(client, "10.0.0.1", "vecino@condo.test") is False

    # Bloqueo global por cuenta distribuyendo intentos en múltiples IPs (con fallback local)
    failing = cast(aioredis.Redis, _FailingAsyncRedis())
    for idx in range(LOGIN_ACCOUNT_MAX_ATTEMPTS):
        await record_login_failure(failing if idx % 2 == 0 else None, f"10.0.1.{idx}", "objetivo@condo.test")
    assert await is_login_locked_out(None, "192.168.99.99", "objetivo@condo.test") is True
    await clear_login_failures(failing, "10.0.1.0", "objetivo@condo.test")
    assert await is_login_locked_out(None, "192.168.99.99", "objetivo@condo.test") is False


async def test_login_lockout_lua_args_normalizacion_y_expiracion(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cubre args exactos de Lua, IP vacía, eval bool/str, TTL local fijo y umbrales en Redis."""
    monkeypatch.setenv("APP_ENV", "development")
    fake = _FakeAsyncRedis()
    client = cast(aioredis.Redis, fake)

    assert await record_login_failure(client, "   ", " User@Condo.TEST ") == 1
    assert await record_login_failure(client, "", "User@Condo.TEST") == 2
    ip_key = "login_fail:unknown:user@condo.test"
    acct_key = "login_fail:acct:user@condo.test"
    assert fake.eval_calls[:2] == [
        (redis_client._LUA_INCR_EXPIRE, 1, (ip_key, 900)),
        (redis_client._LUA_INCR_EXPIRE, 1, (acct_key, 900)),
    ]
    assert redis_client._local_login_failures == {}

    await clear_login_failures(client, "", "USER@CONDO.TEST")
    assert fake.delete_calls[-1] == (ip_key, acct_key)

    # Umbral local de cuenta: 9 intentos -> False, 10mo intento -> True
    for idx in range(LOGIN_ACCOUNT_MAX_ATTEMPTS - 1):
        await record_login_failure(None, f"10.9.0.{idx}", "local-acct@condo.test")
    assert await is_login_locked_out(None, "10.9.0.99", "local-acct@condo.test") is False
    await record_login_failure(None, "10.9.0.99", "local-acct@condo.test")
    assert await is_login_locked_out(None, "10.9.0.99", "local-acct@condo.test") is True

    # eval retornando str es válido; retornando bool o None cae a contador local
    fake.eval_return_override = "4"
    assert await record_login_failure(client, "10.0.0.2", "str@condo.test") == 4
    fake.eval_return_override = True
    assert await record_login_failure(client, "10.0.0.2", "bool@condo.test") == 1
    fake.eval_return_override = None
    assert await record_login_failure(client, "10.0.0.2", "none@condo.test") == 1
    fake.eval_return_override = _UNSET

    # Bloqueo por cuenta desde Redis con 9 vs 10 intentos y _read_redis_counter
    fake.kv["login_fail:acct:acct@condo.test"] = (b"9", None)
    assert await is_login_locked_out(client, "10.0.0.8", "acct@condo.test") is False
    fake.kv["login_fail:acct:acct@condo.test"] = (10, None)
    assert await is_login_locked_out(client, "10.0.0.8", "acct@condo.test") is True
    fake.kv["login_fail:10.0.0.9:bool@condo.test"] = (True, None)
    assert await redis_client._read_redis_counter(client, "login_fail:10.0.0.9:bool@condo.test") == 0
    assert await redis_client._read_redis_counter(cast(aioredis.Redis, _FailingAsyncRedis()), "k") == 0

    # Reloj determinista: exp inicial se preserva en incrementos sucesivos y expira exactamente a los 900s
    clock = _instalar_reloj_falso(monkeypatch, 2000.0)
    assert await record_login_failure(None, "10.0.0.3", "clock@condo.test") == 1
    local_ip_key = "login_fail:10.0.0.3:clock@condo.test"
    assert redis_client._local_login_failures[local_ip_key] == (1, 2900.0)
    clock[0] = 2100.0
    assert await record_login_failure(None, "10.0.0.3", "clock@condo.test") == 2
    assert redis_client._local_login_failures[local_ip_key] == (2, 2900.0)
    for _ in range(3):
        await record_login_failure(None, "10.0.0.3", "clock@condo.test")
    assert await is_login_locked_out(None, "10.0.0.3", "clock@condo.test") is True

    # En producción se ignora cualquier contador local residual
    monkeypatch.setenv("APP_ENV", "production")
    assert redis_client._read_local_failure_count(local_ip_key, 2100.0) == 0
    assert await is_login_locked_out(client, "10.0.0.3", "clock@condo.test") is False
    monkeypatch.setenv("APP_ENV", "development")

    clock[0] = 2900.0
    assert await is_login_locked_out(None, "10.0.0.3", "clock@condo.test") is False
    assert local_ip_key not in redis_client._local_login_failures
    assert await record_login_failure(None, "10.0.0.3", "clock@condo.test") == 1


async def test_refresh_jti_grace_period_y_qr_nonce(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida consumo único de JTI, ventana de gracia de refresh y nonces QR anti-replay."""
    monkeypatch.setenv("APP_ENV", "development")
    fake = _FakeAsyncRedis()
    client = cast(aioredis.Redis, fake)

    assert await mark_refresh_jti_used(client, "  ") is False
    assert await mark_refresh_jti_used(client, "jti-1") is True
    assert await mark_refresh_jti_used(client, "jti-1") is False

    assert await mark_refresh_jti_used(None, "jti-local") is True
    assert await mark_refresh_jti_used(cast(aioredis.Redis, _FailingAsyncRedis()), "jti-local") is False

    assert build_qr_nonce_key(" qr-77 ") == "qr_used:qr-77"
    assert await is_qr_nonce_burned(client, "qr-77") is False
    assert await burn_qr_nonce(client, "qr-77") is True
    assert await burn_qr_nonce(client, "qr-77") is False
    assert await is_qr_nonce_burned(client, "qr-77") is True

    assert await burn_qr_nonce(None, "qr-local") is True
    assert await burn_qr_nonce(cast(aioredis.Redis, _FailingAsyncRedis()), "qr-local") is False
    assert await is_qr_nonce_burned(None, "qr-local") is True

    await rotate_refresh_token_with_grace_period(client, "fam-1", "tok-nuevo", grace_seconds=10)
    assert await get_refresh_token_from_grace_period(client, "fam-1") == "tok-nuevo"

    # Limpieza de caché local para forzar lectura directa desde Redis
    _local_grace_tokens.clear()
    assert await get_refresh_token_from_grace_period(client, "fam-1") == "tok-nuevo"
    assert await get_refresh_token_from_grace_period(None, "fam-inexistente") is None

    # Expiración de grace token local
    _local_grace_tokens["fam-exp"] = ("tok-viejo", time.monotonic() - 1.0)
    assert await get_refresh_token_from_grace_period(None, "fam-exp") is None


async def test_refresh_jti_qr_y_grace_period_bordes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica TTLs por defecto/mínimo 1s, fallback ante error y ventana de gracia de 5s."""
    monkeypatch.setenv("APP_ENV", "development")
    fake = _FakeAsyncRedis()
    client = cast(aioredis.Redis, fake)
    failing = cast(aioredis.Redis, _FailingAsyncRedis())

    assert await mark_refresh_jti_used(client, " jti-def ") is True
    assert fake.set_calls[-1] == ("used_refresh:jti-def", "1", True, redis_client.REFRESH_USED_TTL_SECONDS)
    assert "jti-def" not in redis_client._local_used_refresh_jtis
    assert await mark_refresh_jti_used(client, " jti-def ") is False
    assert "jti-def" not in redis_client._local_used_refresh_jtis

    assert await mark_refresh_jti_used(client, "jti-min", ttl_seconds=0) is True
    assert fake.set_calls[-1] == ("used_refresh:jti-min", "1", True, 1)
    assert await mark_refresh_jti_used(failing, "jti-fail", ttl_seconds=10) is True
    assert await mark_refresh_jti_used(None, "jti-fail") is False

    assert build_qr_nonce_key("") == "qr_used:"
    assert await burn_qr_nonce(client, " qr-def ") is True
    assert fake.set_calls[-1] == ("qr_used:qr-def", "1", True, redis_client.QR_NONCE_TTL_SECONDS)
    assert "qr_used:qr-def" not in redis_client._local_burned_qrs
    assert await burn_qr_nonce(client, "qr-min", ttl_seconds=-5) is True
    assert fake.set_calls[-1] == ("qr_used:qr-min", "1", True, 1)

    assert await burn_qr_nonce(failing, "qr-fail-new", ttl_seconds=10) is True
    assert await is_qr_nonce_burned(failing, "qr-fail-new") is True
    assert await is_qr_nonce_burned(failing, "qr-desconocido") is False
    fake.kv["qr_used:qr-cero"] = ("0", None)
    assert await is_qr_nonce_burned(client, "qr-cero") is False

    await rotate_refresh_token_with_grace_period(client, "fam-def", "tok-def")
    assert fake.set_calls[-1] == ("grace_period:fam-def", "tok-def", False, 5)
    assert "fam-def" not in _local_grace_tokens
    fake.kv["grace_period:fam-def"] = ("tok-def", time.monotonic() - 1.0)
    assert await get_refresh_token_from_grace_period(client, "fam-def") is None

    clock = _instalar_reloj_falso(monkeypatch, 3000.0)
    await rotate_refresh_token_with_grace_period(failing, "fam-fb", "tok-fb")
    assert _local_grace_tokens["fam-fb"] == ("tok-fb", 3005.0)
    clock[0] = 3004.9
    assert await get_refresh_token_from_grace_period(failing, "fam-fb") == "tok-fb"
    clock[0] = 3005.0
    assert await get_refresh_token_from_grace_period(None, "fam-fb") is None
    assert "fam-fb" not in _local_grace_tokens

    await rotate_refresh_token_with_grace_period(None, "fam-min", "tok-min", grace_seconds=0)
    assert _local_grace_tokens["fam-min"] == ("tok-min", 3006.0)

    # En producción se ignora caché local de grace token y JTI vacío sigue siendo no-op
    monkeypatch.setenv("APP_ENV", "production")
    assert await mark_refresh_jti_used(None, "   ") is False
    assert await get_refresh_token_from_grace_period(client, "fam-min") is None


async def test_idempotencia_slots_replay_conflicto_y_corrupcion(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cubre acquire/store/release de slots de idempotencia, check_and_set y parsing defensivo."""
    monkeypatch.setenv("APP_ENV", "development")
    assert build_idempotency_key(" ", "abc ") == "idemp:global:abc"
    assert build_scoped_idempotency_key(2, 9, "pagos", "k-1 ") == "idemp:2:9:pagos:k-1"

    fake = _FakeAsyncRedis()
    client = cast(aioredis.Redis, fake)

    assert await check_and_set_idempotency_key(client, "k-simple", scope="pagos") is True
    assert await check_and_set_idempotency_key(client, "k-simple", scope="pagos") is False
    assert await check_and_set_idempotency_key(None, "k-local", scope="pagos") is True
    assert "idemp:pagos:k-local" in _local_idempotency_keys
    assert await check_and_set_idempotency_key(None, "k-local", scope="pagos") is False

    s_key = build_scoped_idempotency_key(1, 5, "incidencia", "key-0001")
    first = await acquire_idempotency_slot(client, s_key, "hash-a")
    assert first.acquired is True

    in_progress = await acquire_idempotency_slot(client, s_key, "hash-a")
    assert in_progress.acquired is False
    assert in_progress.conflict_detail == "Petición duplicada detectada (operación en curso)."

    mismatch = await acquire_idempotency_slot(client, s_key, "hash-b")
    assert mismatch.acquired is False
    assert mismatch.conflict_detail == "Idempotency-Key reutilizada con un cuerpo de solicitud distinto."

    await store_idempotency_response(
        client,
        s_key,
        IdempotencyResponsePayload(payload_hash="hash-a", status_code=201, body={"id": 99}),
    )
    replay = await acquire_idempotency_slot(client, s_key, "hash-a")
    assert replay.acquired is False
    assert replay.replay_status == 201
    assert replay.replay_body == {"id": 99}

    await release_idempotency_slot(client, s_key)
    reacquired = await acquire_idempotency_slot(client, s_key, "hash-a")
    assert reacquired.acquired is True

    # Fallback local en memoria + release con cliente que falla no propaga excepción
    local_key = build_scoped_idempotency_key(1, 5, "local", "key-0002")
    assert (await acquire_idempotency_slot(None, local_key, "h1")).acquired is True
    await store_idempotency_response(None, local_key, IdempotencyResponsePayload("h1", 200, {"ok": True}))
    assert (await acquire_idempotency_slot(None, local_key, "h1")).replay_status == 200
    await release_idempotency_slot(cast(aioredis.Redis, _FailingAsyncRedis()), local_key)
    assert (await acquire_idempotency_slot(None, local_key, "h1")).acquired is True

    # Registros corruptos / no dict en _evaluate_existing_idempotency_record
    assert _evaluate_existing_idempotency_record(123, "h").conflict_detail is not None
    assert _evaluate_existing_idempotency_record(b"{bad-json", "h").conflict_detail is not None
    assert _evaluate_existing_idempotency_record(json.dumps(["lista"]), "h").conflict_detail is not None


async def test_idempotencia_json_ttls_fallbacks_y_produccion(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida JSON compacto, TTL 86400/mínimo 1s, bytes UTF-8, fallbacks de error y release best-effort."""
    monkeypatch.setenv("APP_ENV", "development")
    assert build_scoped_idempotency_key(cast(Any, "2"), cast(Any, "9"), "   ", " k-1 ") == "idemp:2:9:global:k-1"
    default_slot = IdempotencySlotResult(acquired=True)
    assert default_slot.replay_status is None
    assert default_slot.replay_body is None
    assert default_slot.conflict_detail is None

    fake = _FakeAsyncRedis()
    client = cast(aioredis.Redis, fake)
    failing = cast(aioredis.Redis, _FailingAsyncRedis())

    s_key = build_scoped_idempotency_key(7, 8, "cuotas", "k-json")
    assert (await acquire_idempotency_slot(client, s_key, "h-json")).acquired is True
    assert fake.set_calls[-1] == (
        s_key,
        '{"state":"IN_PROGRESS","payload_hash":"h-json"}',
        True,
        86_400,
    )
    assert s_key not in _local_idempotency_records

    await store_idempotency_response(
        client,
        s_key,
        IdempotencyResponsePayload(payload_hash="h-json", status_code=201, body={"id": 5}),
    )
    assert fake.set_calls[-1] == (
        s_key,
        '{"state":"COMPLETED","payload_hash":"h-json","status_code":201,"body":{"id":5}}',
        False,
        86_400,
    )
    assert s_key not in _local_idempotency_records

    # TTL mínimo 1s en acquire, store y check_and_set
    assert (await acquire_idempotency_slot(client, "idemp:min", "h0", ttl_seconds=0)).acquired is True
    assert fake.set_calls[-1][3] == 1
    await store_idempotency_response(client, "idemp:min", IdempotencyResponsePayload("h0", 200, {}), ttl_seconds=-1)
    assert fake.set_calls[-1][3] == 1

    assert await check_and_set_idempotency_key(client, "k-def") is True
    assert fake.set_calls[-1] == ("idemp:global:k-def", "1", True, 86_400)
    assert "idemp:global:k-def" not in _local_idempotency_keys
    assert await check_and_set_idempotency_key(client, "k-min", ttl_seconds=0) is True
    assert fake.set_calls[-1] == ("idemp:global:k-min", "1", True, 1)

    # Fallback ante error de red en acquire, store y check_and_set
    assert (await acquire_idempotency_slot(failing, "idemp:fb", "h-fb", ttl_seconds=30)).acquired is True
    assert "idemp:fb" in _local_idempotency_records
    dup_fb = await acquire_idempotency_slot(None, "idemp:fb", "h-fb")
    assert dup_fb == IdempotencySlotResult(
        acquired=False,
        conflict_detail="Petición duplicada detectada (operación en curso).",
    )
    await store_idempotency_response(failing, "idemp:fb", IdempotencyResponsePayload("h-fb", 202, {"ok": 1}))
    assert (await acquire_idempotency_slot(None, "idemp:fb", "h-fb")).replay_status == 202

    assert await check_and_set_idempotency_key(failing, "k-fb", scope="pagos") is True
    assert await check_and_set_idempotency_key(failing, "k-fb", scope="pagos") is False

    # Parsing defensivo y bytes UTF-8 válidos
    utf8_bytes = '{"state":"COMPLETED","payload_hash":"hb","status_code":202,"body":{"msg":"acción"}}'.encode("utf-8")
    assert _evaluate_existing_idempotency_record(utf8_bytes, "hb") == IdempotencySlotResult(
        acquired=False,
        replay_status=202,
        replay_body={"msg": "acción"},
    )
    bad_status_json = json.dumps({"state": "COMPLETED", "payload_hash": "h", "status_code": "201", "body": {}})
    assert _evaluate_existing_idempotency_record(bad_status_json, "h") == IdempotencySlotResult(
        acquired=False,
        conflict_detail="Petición duplicada detectada (operación en curso).",
    )
    for corrupt in (None, 123, b"{bad-json", "{bad", json.dumps(["lista"])):
        res = _evaluate_existing_idempotency_record(corrupt, "h")
        assert res.acquired is False
        assert res.conflict_detail == "Petición duplicada detectada (Idempotency-Key ya procesada)."

    # release_idempotency_slot limpia caché local y Redis, y no lanza 503 en producción si Redis falla
    _local_idempotency_records[s_key] = ("{}", 9999999.0)
    await release_idempotency_slot(None, s_key)
    assert s_key not in _local_idempotency_records
    _local_idempotency_records[s_key] = ("{}", 9999999.0)
    await release_idempotency_slot(client, s_key)
    assert s_key not in _local_idempotency_records
    assert fake.delete_calls[-1] == (s_key,)

    monkeypatch.setenv("APP_ENV", "production")
    await release_idempotency_slot(failing, s_key)


def test_ttl_local_expiracion_y_lru_eviction(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica expiración TTL y cota LRU MAX_LOCAL_SECURITY_ENTRIES en mapas locales."""
    monkeypatch.setenv("APP_ENV", "development")
    store: dict[str, float] = {}
    store["expirada"] = time.monotonic() - 5.0
    assert has_local_ttl(store, "expirada") is False
    assert "expirada" not in store

    for idx in range(MAX_LOCAL_SECURITY_ENTRIES + 5):
        store_local_ttl(store, f"k-{idx}", 60)
    assert len(store) == MAX_LOCAL_SECURITY_ENTRIES
    assert "k-0" not in store

    for idx in range(MAX_LOCAL_SECURITY_ENTRIES + 3):
        redis_idempotency._store_local_idemp_record(f"rec-{idx}", "{}", 60)
    assert len(_local_idempotency_records) == MAX_LOCAL_SECURITY_ENTRIES


def test_local_ttl_y_records_bordes_y_produccion(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida reloj exacto (exp==now), evicción por menor TTL, actualización sin evicción y modo prod."""
    monkeypatch.delenv("APP_ENV", raising=False)
    assert is_production_env() is False
    raise_if_prod(ValueError("ignorado"))

    monkeypatch.setenv("APP_ENV", "  PRODUCTION  ")
    assert is_production_env() is True
    with pytest.raises(HTTPException) as exc_none:
        raise_if_prod()
    assert exc_none.value.status_code == 503
    assert exc_none.value.detail == _DETAIL_KEYDB_503
    assert exc_none.value.__cause__ is None

    causa = ValueError("boom")
    with pytest.raises(HTTPException) as exc_cause:
        raise_if_prod(causa)
    assert exc_cause.value.status_code == 503
    assert exc_cause.value.detail == _DETAIL_KEYDB_503
    assert exc_cause.value.__cause__ is causa

    monkeypatch.setenv("APP_ENV", "development")
    clock = _instalar_reloj_falso(monkeypatch, 100.0)

    store: dict[str, float] = {"eq": 100.0, "gt": 100.1}
    purge_expired_map(store, 100.0)
    assert store == {"gt": 100.1}

    store_local_ttl(store, "min-ttl", 0)
    assert store["min-ttl"] == 101.0
    clock[0] = 101.0
    assert has_local_ttl(store, "min-ttl") is False
    assert "min-ttl" not in store

    # Evicción elige la entrada de menor expiración y actualizar una clave existente no evicta otra
    lru_store: dict[str, float] = {}
    for idx in range(MAX_LOCAL_SECURITY_ENTRIES):
        ttl = 5 if idx == 500 else 100 + idx
        store_local_ttl(lru_store, f"lru-{idx}", ttl)
    assert len(lru_store) == MAX_LOCAL_SECURITY_ENTRIES
    store_local_ttl(lru_store, "lru-0", 999)
    assert len(lru_store) == MAX_LOCAL_SECURITY_ENTRIES
    assert "lru-500" in lru_store
    store_local_ttl(lru_store, "lru-extra", 200)
    assert len(lru_store) == MAX_LOCAL_SECURITY_ENTRIES
    assert "lru-500" not in lru_store
    assert "lru-0" in lru_store
    assert "lru-extra" in lru_store

    clock[0] = 203.0
    store_local_ttl(lru_store, "lru-after-exp", 50)
    assert len(lru_store) == MAX_LOCAL_SECURITY_ENTRIES - 1
    assert "lru-1" not in lru_store
    assert "lru-2" not in lru_store
    assert "lru-3" in lru_store

    # Mismo control de expiración y evicción para _local_idempotency_records
    clock[0] = 200.0
    _store_local_idemp_record("r-min", "{}", 0)
    assert _local_idempotency_records["r-min"] == ("{}", 201.0)
    clock[0] = 201.0
    assert _get_local_idemp_record("r-min") is None
    assert "r-min" not in _local_idempotency_records

    for idx in range(MAX_LOCAL_SECURITY_ENTRIES):
        ttl = 5 if idx == 400 else 100 + idx
        _store_local_idemp_record(f"rec-{idx}", f"{idx}", ttl)
    _store_local_idemp_record("rec-0", "upd", 999)
    assert len(_local_idempotency_records) == MAX_LOCAL_SECURITY_ENTRIES
    assert "rec-400" in _local_idempotency_records
    _store_local_idemp_record("rec-extra", "new", 200)
    assert len(_local_idempotency_records) == MAX_LOCAL_SECURITY_ENTRIES
    assert "rec-400" not in _local_idempotency_records
    assert "rec-extra" in _local_idempotency_records

    clock[0] = 303.0
    _store_local_idemp_record("rec-after-exp", "v", 50)
    assert len(_local_idempotency_records) == MAX_LOCAL_SECURITY_ENTRIES - 1
    assert "rec-1" not in _local_idempotency_records
    assert "rec-2" not in _local_idempotency_records
    assert "rec-3" in _local_idempotency_records

    # En producción store/has local son no-op y no borran entradas preexistentes
    monkeypatch.setenv("APP_ENV", "production")
    prod_store: dict[str, float] = {"keep": 9999.0}
    store_local_ttl(prod_store, "nuevo", 60)
    assert prod_store == {"keep": 9999.0}
    assert has_local_ttl(prod_store, "keep") is False
    assert "keep" in prod_store

    _local_idempotency_records["keep-rec"] = ("v", 9999.0)
    _store_local_idemp_record("nuevo-rec", "v2", 60)
    assert "nuevo-rec" not in _local_idempotency_records
    assert _get_local_idemp_record("keep-rec") is None
    assert "keep-rec" in _local_idempotency_records


async def test_politica_fail_closed_503_en_produccion(monkeypatch: pytest.MonkeyPatch) -> None:
    """En APP_ENV=production toda ausencia o error de KeyDB falla cerrado con HTTP 503."""
    monkeypatch.setenv("APP_ENV", "production")
    failing = cast(aioredis.Redis, _FailingAsyncRedis())

    calls = [
        revoke_user_session(None, 1),
        revoke_user_session(failing, 1),
        is_user_session_revoked(None, 1),
        is_user_session_revoked(failing, 1),
        clear_user_session_revocation(None, 1),
        clear_user_session_revocation(failing, 1),
        revoke_session_id(None, "sid-1"),
        revoke_session_id(failing, "sid-1"),
        is_session_id_revoked(None, "sid-1"),
        is_session_id_revoked(failing, "sid-1"),
        record_login_failure(None, "1.1.1.1", "a@b.test"),
        record_login_failure(failing, "1.1.1.1", "a@b.test"),
        is_login_locked_out(None, "1.1.1.1", "a@b.test"),
        is_login_locked_out(failing, "1.1.1.1", "a@b.test"),
        clear_login_failures(None, "1.1.1.1", "a@b.test"),
        clear_login_failures(failing, "1.1.1.1", "a@b.test"),
        mark_refresh_jti_used(None, "jti-prod"),
        mark_refresh_jti_used(failing, "jti-prod"),
        burn_qr_nonce(None, "qr-prod"),
        burn_qr_nonce(failing, "qr-prod"),
        is_qr_nonce_burned(None, "qr-prod"),
        is_qr_nonce_burned(failing, "qr-prod"),
        acquire_idempotency_slot(None, "k-prod", "h"),
        acquire_idempotency_slot(failing, "k-prod", "h"),
        store_idempotency_response(None, "k-prod", IdempotencyResponsePayload("h", 200, {})),
        store_idempotency_response(failing, "k-prod", IdempotencyResponsePayload("h", 200, {})),
        check_and_set_idempotency_key(None, "k-prod"),
        check_and_set_idempotency_key(failing, "k-prod"),
        rotate_refresh_token_with_grace_period(None, "fam", "tok"),
        rotate_refresh_token_with_grace_period(failing, "fam", "tok"),
        get_refresh_token_from_grace_period(None, "fam"),
        get_refresh_token_from_grace_period(failing, "fam"),
    ]
    for coro in calls:
        with pytest.raises(HTTPException) as exc:
            await coro
        assert exc.value.status_code == 503
        assert exc.value.detail == _DETAIL_KEYDB_503
