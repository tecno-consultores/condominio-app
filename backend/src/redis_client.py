"""Cliente asíncrono KeyDB/Redis: idempotencia, revocación fail-closed 7d, lockout Lua y nonces QR."""

import os
import time

import redis.asyncio as redis

from src.redis_idempotency import (
    GRACE_PERIOD_SECONDS,
    IDEMPOTENCY_TTL_SECONDS,
    MAX_LOCAL_SECURITY_ENTRIES,
    IdempotencyResponsePayload,
    IdempotencySlotResult,
    _local_grace_tokens,
    _local_idempotency_keys,
    _local_idempotency_records,
    acquire_idempotency_slot,
    build_idempotency_key,
    build_scoped_idempotency_key,
    check_and_set_idempotency_key,
    get_refresh_token_from_grace_period,
    has_local_ttl,
    is_production_env,
    raise_if_prod,
    release_idempotency_slot,
    reset_local_idempotency_state,
    rotate_refresh_token_with_grace_period,
    store_idempotency_response,
    store_local_ttl,
)

__all__ = [
    "GRACE_PERIOD_SECONDS",
    "IDEMPOTENCY_TTL_SECONDS",
    "MAX_LOCAL_SECURITY_ENTRIES",
    "IdempotencyResponsePayload",
    "IdempotencySlotResult",
    "_local_grace_tokens",
    "_local_idempotency_keys",
    "_local_idempotency_records",
    "acquire_idempotency_slot",
    "build_idempotency_key",
    "build_qr_nonce_key",
    "build_scoped_idempotency_key",
    "burn_qr_nonce",
    "check_and_set_idempotency_key",
    "clear_login_failures",
    "clear_user_session_revocation",
    "get_redis_client",
    "get_refresh_token_from_grace_period",
    "is_login_locked_out",
    "is_qr_nonce_burned",
    "is_session_id_revoked",
    "is_user_session_revoked",
    "mark_refresh_jti_used",
    "record_login_failure",
    "release_idempotency_slot",
    "reset_local_security_state",
    "revoke_session_id",
    "revoke_user_session",
    "rotate_refresh_token_with_grace_period",
    "store_idempotency_response",
]

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
LOGIN_MAX_ATTEMPTS = 5
LOGIN_ACCOUNT_MAX_ATTEMPTS = 10
LOGIN_LOCKOUT_SECONDS = 900
REFRESH_TOKEN_EXPIRE_DAYS = max(7, int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")))
REFRESH_USED_TTL_SECONDS = REFRESH_TOKEN_EXPIRE_DAYS * 86_400
REVOKED_USER_TTL_SECONDS = REFRESH_USED_TTL_SECONDS
QR_NONCE_TTL_SECONDS = 259_200

_LUA_INCR_EXPIRE = (
    "local c = redis.call('INCR', KEYS[1]); "
    "if c == 1 or redis.call('TTL', KEYS[1]) < 0 then "
    "redis.call('EXPIRE', KEYS[1], tonumber(ARGV[1])) "
    "end; "
    "return c"
)

_redis_client: redis.Redis | None = None
_local_revoked_users: dict[int, float] = {}
_local_revoked_sids: dict[str, float] = {}
_local_burned_qrs: dict[str, float] = {}
_local_login_failures: dict[str, tuple[int, float]] = {}
_local_used_refresh_jtis: dict[str, float] = {}


def reset_local_security_state() -> None:
    """Reinicia el estado local en memoria utilizado en pruebas fuera de producción."""
    _local_revoked_users.clear()
    _local_revoked_sids.clear()
    _local_burned_qrs.clear()
    _local_login_failures.clear()
    _local_used_refresh_jtis.clear()
    reset_local_idempotency_state()


def get_redis_client() -> redis.Redis:
    """Retorna el cliente singleton asíncrono de Redis/KeyDB."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


async def _read_redis_flag(client: redis.Redis | None, redis_key: str) -> bool:
    """Consulta una bandera ('1') en KeyDB aplicando política Fail-Closed en producción."""
    if client is None:
        raise_if_prod()
        return False
    try:
        val = await client.get(redis_key)
        return val in ("1", b"1")
    except Exception as exc:
        raise_if_prod(exc)
        return False


async def revoke_user_session(
    client: redis.Redis | None,
    user_id: int,
    ttl_seconds: int = REVOKED_USER_TTL_SECONDS,
) -> None:
    """Registra la revocación instantánea de sesión de un usuario en KeyDB (>= 7d, Fail-Closed en prod)."""
    uid = int(user_id)
    if client is not None:
        try:
            await client.set(f"revoked_user:{uid}", "1", ex=max(1, int(ttl_seconds)))
            return
        except Exception as exc:
            raise_if_prod(exc)
    else:
        raise_if_prod()
    store_local_ttl(_local_revoked_users, uid, ttl_seconds)


async def clear_user_session_revocation(
    client: redis.Redis | None,
    user_id: int,
) -> None:
    """Limpia la marca de revocación administrativa de sesión cuando el usuario es reactivado."""
    uid = int(user_id)
    _local_revoked_users.pop(uid, None)
    if client is None:
        raise_if_prod()
        return
    try:
        await client.delete(f"revoked_user:{uid}")
    except Exception as exc:
        raise_if_prod(exc)


async def is_user_session_revoked(
    client: redis.Redis | None,
    user_id: int,
) -> bool:
    """Verifica si la sesión de un usuario fue revocada en tiempo real en KeyDB."""
    uid = int(user_id)
    if has_local_ttl(_local_revoked_users, uid):
        return True
    return await _read_redis_flag(client, f"revoked_user:{uid}")


async def revoke_session_id(
    client: redis.Redis | None,
    sid: str,
    ttl_seconds: int = REVOKED_USER_TTL_SECONDS,
) -> None:
    """Registra la revocación de un identificador de sesión específico (sid) tras logout o replay."""
    clean_sid = sid.strip()
    if not clean_sid:
        return
    if client is not None:
        try:
            await client.set(f"revoked_sid:{clean_sid}", "1", ex=max(1, int(ttl_seconds)))
            return
        except Exception as exc:
            raise_if_prod(exc)
    else:
        raise_if_prod()
    store_local_ttl(_local_revoked_sids, clean_sid, ttl_seconds)


async def is_session_id_revoked(client: redis.Redis | None, sid: str) -> bool:
    """Verifica si un sid de sesión fue revocado (Fail-Closed en producción)."""
    clean_sid = sid.strip()
    if not clean_sid:
        return False
    if has_local_ttl(_local_revoked_sids, clean_sid):
        return True
    return await _read_redis_flag(client, f"revoked_sid:{clean_sid}")


def _login_failure_key(ip: str, correo: str) -> str:
    clean_ip = (ip or "unknown").strip() or "unknown"
    clean_correo = correo.strip().lower()
    return f"login_fail:{clean_ip}:{clean_correo}"


def _login_account_failure_key(correo: str) -> str:
    return f"login_fail:acct:{correo.strip().lower()}"


def _purge_expired_local_failures(now: float) -> None:
    expired = [key for key, (_, exp) in _local_login_failures.items() if exp <= now]
    for key in expired:
        _local_login_failures.pop(key, None)


def _read_local_failure_count(key: str, now: float) -> int:
    if is_production_env():
        return 0
    entry = _local_login_failures.get(key)
    return entry[0] if entry is not None and entry[1] > now else 0


async def _read_redis_counter(client: redis.Redis | None, key: str) -> int:
    if client is None:
        raise_if_prod()
        return 0
    try:
        raw = await client.get(key)
        if isinstance(raw, (str, bytes, int)) and not isinstance(raw, bool):
            return int(raw)
        return 0
    except Exception as exc:
        raise_if_prod(exc)
        return 0


async def is_login_locked_out(client: redis.Redis | None, ip: str, correo: str) -> bool:
    """Retorna True si (ip, correo) o la cuenta global alcanzaron su umbral de fallos."""
    ip_key = _login_failure_key(ip, correo)
    acct_key = _login_account_failure_key(correo)
    now = time.monotonic()
    _purge_expired_local_failures(now)
    if _read_local_failure_count(ip_key, now) >= LOGIN_MAX_ATTEMPTS:
        return True
    if _read_local_failure_count(acct_key, now) >= LOGIN_ACCOUNT_MAX_ATTEMPTS:
        return True
    ip_count = await _read_redis_counter(client, ip_key)
    acct_count = await _read_redis_counter(client, acct_key)
    return ip_count >= LOGIN_MAX_ATTEMPTS or acct_count >= LOGIN_ACCOUNT_MAX_ATTEMPTS


async def _eval_atomic_incr(client: redis.Redis, key: str) -> int | None:
    attempts = await client.eval(_LUA_INCR_EXPIRE, 1, key, LOGIN_LOCKOUT_SECONDS)
    if isinstance(attempts, (int, str)) and not isinstance(attempts, bool):
        return int(attempts)
    return None


def _increment_local_failure(key: str, now: float) -> int:
    prev_count, prev_exp = _local_login_failures.get(key, (0, now + LOGIN_LOCKOUT_SECONDS))
    new_count = prev_count + 1
    _local_login_failures[key] = (new_count, prev_exp if prev_count > 0 else now + LOGIN_LOCKOUT_SECONDS)
    return new_count


async def record_login_failure(client: redis.Redis | None, ip: str, correo: str) -> int:
    """Incrementa atómicamente vía Lua el contador por (ip, correo) y la cuota global por correo."""
    ip_key = _login_failure_key(ip, correo)
    acct_key = _login_account_failure_key(correo)
    now = time.monotonic()
    _purge_expired_local_failures(now)
    if client is not None:
        try:
            ip_attempts = await _eval_atomic_incr(client, ip_key)
            await _eval_atomic_incr(client, acct_key)
            if ip_attempts is not None:
                return ip_attempts
        except Exception as exc:
            raise_if_prod(exc)
    else:
        raise_if_prod()
    _increment_local_failure(acct_key, now)
    return _increment_local_failure(ip_key, now)


async def clear_login_failures(client: redis.Redis | None, ip: str, correo: str) -> None:
    """Reinicia los contadores de fallos de login tras una autenticación válida."""
    ip_key = _login_failure_key(ip, correo)
    acct_key = _login_account_failure_key(correo)
    _local_login_failures.pop(ip_key, None)
    _local_login_failures.pop(acct_key, None)
    if client is None:
        raise_if_prod()
        return
    try:
        await client.delete(ip_key, acct_key)
    except Exception as exc:
        raise_if_prod(exc)


async def mark_refresh_jti_used(
    client: redis.Redis | None,
    jti: str,
    ttl_seconds: int = REFRESH_USED_TTL_SECONDS,
) -> bool:
    """Consume atómicamente el JTI de un refresh token (True en primer uso, False en reutilización)."""
    clean_jti = jti.strip()
    if not clean_jti:
        return False
    redis_key = f"used_refresh:{clean_jti}"
    if client is not None:
        try:
            is_first = await client.set(redis_key, "1", nx=True, ex=max(1, int(ttl_seconds)))
            return bool(is_first)
        except Exception as exc:
            raise_if_prod(exc)
    else:
        raise_if_prod()
    if has_local_ttl(_local_used_refresh_jtis, clean_jti):
        return False
    store_local_ttl(_local_used_refresh_jtis, clean_jti, ttl_seconds)
    return True


def build_qr_nonce_key(jti: str) -> str:
    """Construye la clave Anti-Replay en KeyDB para el JTI de un pase QR de único uso."""
    return f"qr_used:{jti.strip()}"


async def burn_qr_nonce(
    client: redis.Redis | None,
    jti: str,
    ttl_seconds: int = QR_NONCE_TTL_SECONDS,
) -> bool:
    """Registra atómicamente el consumo de un pase QR (SET NX EX) con política Fail-Closed."""
    key = build_qr_nonce_key(jti)
    if client is not None:
        try:
            is_first_use = await client.set(key, "1", nx=True, ex=max(1, int(ttl_seconds)))
            return bool(is_first_use)
        except Exception as exc:
            raise_if_prod(exc)
    else:
        raise_if_prod()
    if has_local_ttl(_local_burned_qrs, key):
        return False
    store_local_ttl(_local_burned_qrs, key, ttl_seconds)
    return True


async def is_qr_nonce_burned(
    client: redis.Redis | None,
    jti: str,
) -> bool:
    """Verifica si un JTI de pase QR ya fue quemado o revocado en KeyDB."""
    key = build_qr_nonce_key(jti)
    if has_local_ttl(_local_burned_qrs, key):
        return True
    return await _read_redis_flag(client, key)
