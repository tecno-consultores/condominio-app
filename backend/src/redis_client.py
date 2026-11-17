"""Cliente asíncrono KeyDB/Redis: idempotencia, revocación fail-closed 7d, lockout Lua y nonces QR."""

import os
import time
from typing import Any

import redis.asyncio as redis
from fastapi import HTTPException, status

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
GRACE_PERIOD_SECONDS = 5
IDEMPOTENCY_TTL_SECONDS = 86_400
LOGIN_MAX_ATTEMPTS = 5
LOGIN_ACCOUNT_MAX_ATTEMPTS = 10
LOGIN_LOCKOUT_SECONDS = 900
REFRESH_TOKEN_EXPIRE_DAYS = max(7, int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")))
REFRESH_USED_TTL_SECONDS = REFRESH_TOKEN_EXPIRE_DAYS * 86_400
REVOKED_USER_TTL_SECONDS = REFRESH_USED_TTL_SECONDS
QR_NONCE_TTL_SECONDS = 259_200
MAX_LOCAL_SECURITY_ENTRIES = 1024

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
_local_idempotency_keys: dict[str, float] = {}
_local_burned_qrs: dict[str, float] = {}
_local_login_failures: dict[str, tuple[int, float]] = {}
_local_used_refresh_jtis: dict[str, float] = {}
_local_grace_tokens: dict[str, tuple[str, float]] = {}


def _is_production_env() -> bool:
    return os.getenv("APP_ENV", "development").strip().lower() == "production"


def _raise_if_prod(exc: Exception | None = None) -> None:
    """Falla cerrado (HTTP 503) en producción cuando KeyDB no está disponible."""
    if not _is_production_env():
        return
    if exc is not None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de seguridad KeyDB no disponible.",
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Servicio de seguridad KeyDB no disponible.",
    )


def _purge_expired_map(store: dict[Any, float], now: float) -> None:
    expired = [key for key, exp in store.items() if exp <= now]
    for key in expired:
        store.pop(key, None)


def _store_local_ttl(store: dict[Any, float], key: Any, ttl_seconds: int) -> None:
    if _is_production_env():
        return
    now = time.monotonic()
    _purge_expired_map(store, now)
    if key not in store and len(store) >= MAX_LOCAL_SECURITY_ENTRIES:
        oldest_key = min(store, key=lambda k: store[k])
        store.pop(oldest_key, None)
    store[key] = now + max(1, int(ttl_seconds))


def _has_local_ttl(store: dict[Any, float], key: Any) -> bool:
    if _is_production_env():
        return False
    now = time.monotonic()
    exp = store.get(key)
    if exp is None:
        return False
    if exp <= now:
        store.pop(key, None)
        return False
    return True


def reset_local_security_state() -> None:
    """Reinicia el estado local en memoria utilizado en pruebas fuera de producción."""
    _local_revoked_users.clear()
    _local_revoked_sids.clear()
    _local_idempotency_keys.clear()
    _local_burned_qrs.clear()
    _local_login_failures.clear()
    _local_used_refresh_jtis.clear()
    _local_grace_tokens.clear()


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def build_idempotency_key(scope: str, key: str) -> str:
    """Construye una clave de idempotencia aislada por ámbito/usuario (Patrón 11)."""
    clean_scope = scope.strip() or "global"
    return f"idemp:{clean_scope}:{key.strip()}"


async def check_and_set_idempotency_key(
    client: redis.Redis | None,
    key: str,
    ttl_seconds: int = IDEMPOTENCY_TTL_SECONDS,
    scope: str = "global",
) -> bool:
    """Verifica y almacena una clave de idempotencia atómicamente en KeyDB (Fail-Closed en prod)."""
    redis_key = build_idempotency_key(scope, key)
    if client is not None:
        try:
            is_new = await client.set(redis_key, "1", nx=True, ex=max(1, int(ttl_seconds)))
            return bool(is_new)
        except Exception as exc:
            _raise_if_prod(exc)
    else:
        _raise_if_prod()
    if _has_local_ttl(_local_idempotency_keys, redis_key):
        return False
    _store_local_ttl(_local_idempotency_keys, redis_key, ttl_seconds)
    return True


async def rotate_refresh_token_with_grace_period(
    client: redis.Redis | None,
    old_token_family_id: str,
    new_token: str,
    grace_seconds: int = GRACE_PERIOD_SECONDS,
) -> None:
    """Almacena un token rotado con ventana de cortesía de 5s para pestañas concurrentes (Patrón 10)."""
    if client is not None:
        try:
            await client.set(
                f"grace_period:{old_token_family_id}",
                new_token,
                ex=grace_seconds,
            )
            return
        except Exception as exc:
            _raise_if_prod(exc)
    else:
        _raise_if_prod()
    if not _is_production_env():
        _local_grace_tokens[old_token_family_id] = (new_token, time.monotonic() + max(1, grace_seconds))


async def get_refresh_token_from_grace_period(
    client: redis.Redis | None,
    old_token_family_id: str,
) -> str | None:
    """Recupera el nuevo token si la rotación ocurrió dentro del grace period de 5s."""
    if not _is_production_env():
        now = time.monotonic()
        entry = _local_grace_tokens.get(old_token_family_id)
        if entry is not None:
            if entry[1] > now:
                return entry[0]
            _local_grace_tokens.pop(old_token_family_id, None)
    if client is None:
        _raise_if_prod()
        return None
    try:
        val = await client.get(f"grace_period:{old_token_family_id}")
        return str(val) if val is not None else None
    except Exception as exc:
        _raise_if_prod(exc)
        return None


async def _read_redis_flag(client: redis.Redis | None, redis_key: str) -> bool:
    """Consulta una bandera ('1') en KeyDB aplicando política Fail-Closed en producción."""
    if client is None:
        _raise_if_prod()
        return False
    try:
        val = await client.get(redis_key)
        return val in ("1", b"1")
    except Exception as exc:
        _raise_if_prod(exc)
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
            _raise_if_prod(exc)
    else:
        _raise_if_prod()
    _store_local_ttl(_local_revoked_users, uid, ttl_seconds)


async def clear_user_session_revocation(
    client: redis.Redis | None,
    user_id: int,
) -> None:
    """Limpia la marca de revocación administrativa de sesión cuando el usuario es reactivado."""
    uid = int(user_id)
    _local_revoked_users.pop(uid, None)
    if client is None:
        _raise_if_prod()
        return
    try:
        await client.delete(f"revoked_user:{uid}")
    except Exception as exc:
        _raise_if_prod(exc)


async def is_user_session_revoked(
    client: redis.Redis | None,
    user_id: int,
) -> bool:
    """Verifica si la sesión de un usuario fue revocada en tiempo real en KeyDB."""
    uid = int(user_id)
    if _has_local_ttl(_local_revoked_users, uid):
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
            _raise_if_prod(exc)
    else:
        _raise_if_prod()
    _store_local_ttl(_local_revoked_sids, clean_sid, ttl_seconds)


async def is_session_id_revoked(client: redis.Redis | None, sid: str) -> bool:
    """Verifica si un sid de sesión fue revocado (Fail-Closed en producción)."""
    clean_sid = sid.strip()
    if not clean_sid:
        return False
    if _has_local_ttl(_local_revoked_sids, clean_sid):
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
    if _is_production_env():
        return 0
    entry = _local_login_failures.get(key)
    return entry[0] if entry is not None and entry[1] > now else 0


async def _read_redis_counter(client: redis.Redis | None, key: str) -> int:
    if client is None:
        _raise_if_prod()
        return 0
    try:
        raw = await client.get(key)
        if isinstance(raw, (str, bytes, int)) and not isinstance(raw, bool):
            return int(raw)
        return 0
    except Exception as exc:
        _raise_if_prod(exc)
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
            _raise_if_prod(exc)
    else:
        _raise_if_prod()
    _increment_local_failure(acct_key, now)
    return _increment_local_failure(ip_key, now)


async def clear_login_failures(client: redis.Redis | None, ip: str, correo: str) -> None:
    """Reinicia los contadores de fallos de login tras una autenticación válida."""
    ip_key = _login_failure_key(ip, correo)
    acct_key = _login_account_failure_key(correo)
    _local_login_failures.pop(ip_key, None)
    _local_login_failures.pop(acct_key, None)
    if client is None:
        _raise_if_prod()
        return
    try:
        await client.delete(ip_key, acct_key)
    except Exception as exc:
        _raise_if_prod(exc)


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
            _raise_if_prod(exc)
    else:
        _raise_if_prod()
    if _has_local_ttl(_local_used_refresh_jtis, clean_jti):
        return False
    _store_local_ttl(_local_used_refresh_jtis, clean_jti, ttl_seconds)
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
            _raise_if_prod(exc)
    else:
        _raise_if_prod()
    if _has_local_ttl(_local_burned_qrs, key):
        return False
    _store_local_ttl(_local_burned_qrs, key, ttl_seconds)
    return True


async def is_qr_nonce_burned(
    client: redis.Redis | None,
    jti: str,
) -> bool:
    """Verifica si un JTI de pase QR ya fue quemado o revocado en KeyDB."""
    key = build_qr_nonce_key(jti)
    if _has_local_ttl(_local_burned_qrs, key):
        return True
    return await _read_redis_flag(client, key)
