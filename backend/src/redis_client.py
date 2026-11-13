"""Cliente asíncrono KeyDB/Redis: idempotencia aislada por ámbito y grace period de tokens."""

import contextlib
import os
import time

import redis.asyncio as redis
from fastapi import HTTPException, status

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
GRACE_PERIOD_SECONDS = 5
IDEMPOTENCY_TTL_SECONDS = 86_400
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 900
REVOKED_USER_TTL_SECONDS = 86_400
QR_NONCE_TTL_SECONDS = 259_200
REFRESH_USED_TTL_SECONDS = 7 * 86_400

_redis_client: redis.Redis | None = None
_local_revoked_users: set[int] = set()
_local_revoked_sids: set[str] = set()
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


def reset_local_security_state() -> None:
    """Reinicia el estado local en memoria utilizado en pruebas fuera de producción."""
    _local_revoked_users.clear()
    _local_revoked_sids.clear()
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
    client: redis.Redis,
    key: str,
    ttl_seconds: int = IDEMPOTENCY_TTL_SECONDS,
    scope: str = "global",
) -> bool:
    """Verifica y almacena una clave de idempotencia atómicamente en KeyDB/Redis.

    Retorna True si la clave es NUEVA (se adquirió el candado).
    Retorna False si la clave ya existía (petición duplicada).
    """
    redis_key = build_idempotency_key(scope, key)
    is_new = await client.set(redis_key, "1", nx=True, ex=ttl_seconds)
    return bool(is_new)


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
    _local_grace_tokens[old_token_family_id] = (new_token, time.monotonic() + max(1, grace_seconds))


async def get_refresh_token_from_grace_period(
    client: redis.Redis | None,
    old_token_family_id: str,
) -> str | None:
    """Recupera el nuevo token si la rotación ocurrió dentro del grace period de 5s."""
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
    """Registra la revocación instantánea de sesión de un usuario en KeyDB Multi-Hilo (Patrón 16)."""
    _local_revoked_users.add(int(user_id))
    if client is not None:
        with contextlib.suppress(Exception):
            await client.set(f"revoked_user:{int(user_id)}", "1", ex=ttl_seconds)


async def clear_user_session_revocation(
    client: redis.Redis | None,
    user_id: int,
) -> None:
    """Limpia la marca de revocación de sesión cuando el usuario es reactivado."""
    _local_revoked_users.discard(int(user_id))
    if client is not None:
        with contextlib.suppress(Exception):
            await client.delete(f"revoked_user:{int(user_id)}")


async def is_user_session_revoked(
    client: redis.Redis | None,
    user_id: int,
) -> bool:
    """Verifica si la sesión de un usuario fue revocada en tiempo real en KeyDB."""
    uid = int(user_id)
    if uid in _local_revoked_users:
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
    _local_revoked_sids.add(clean_sid)
    if client is not None:
        with contextlib.suppress(Exception):
            await client.set(f"revoked_sid:{clean_sid}", "1", ex=ttl_seconds)


async def is_session_id_revoked(client: redis.Redis | None, sid: str) -> bool:
    """Verifica si un sid de sesión fue revocado (Fail-Closed en producción)."""
    clean_sid = sid.strip()
    if not clean_sid:
        return False
    if clean_sid in _local_revoked_sids:
        return True
    return await _read_redis_flag(client, f"revoked_sid:{clean_sid}")


def _login_failure_key(ip: str, correo: str) -> str:
    clean_ip = (ip or "unknown").strip() or "unknown"
    clean_correo = correo.strip().lower()
    return f"login_fail:{clean_ip}:{clean_correo}"


def _purge_expired_local_failures(now: float) -> None:
    expired = [key for key, (_, exp) in _local_login_failures.items() if exp <= now]
    for key in expired:
        _local_login_failures.pop(key, None)


async def is_login_locked_out(client: redis.Redis | None, ip: str, correo: str) -> bool:
    """Retorna True si (ip, correo) alcanzó LOGIN_MAX_ATTEMPTS fallos en la ventana de 15 minutos."""
    key = _login_failure_key(ip, correo)
    now = time.monotonic()
    _purge_expired_local_failures(now)
    local_entry = _local_login_failures.get(key)
    if local_entry is not None and local_entry[0] >= LOGIN_MAX_ATTEMPTS:
        return True
    if client is None:
        _raise_if_prod()
        return False
    try:
        raw = await client.get(key)
        if isinstance(raw, (str, bytes, int)) and not isinstance(raw, bool):
            return int(raw) >= LOGIN_MAX_ATTEMPTS
        return False
    except Exception as exc:
        _raise_if_prod(exc)
        return False


async def record_login_failure(client: redis.Redis | None, ip: str, correo: str) -> int:
    """Incrementa el contador de intentos fallidos de inicio de sesión para (ip, correo)."""
    key = _login_failure_key(ip, correo)
    now = time.monotonic()
    _purge_expired_local_failures(now)
    if client is not None:
        try:
            attempts = await client.incr(key)
            if isinstance(attempts, int) and not isinstance(attempts, bool):
                if attempts == 1:
                    await client.expire(key, LOGIN_LOCKOUT_SECONDS)
                return attempts
        except Exception as exc:
            _raise_if_prod(exc)
    else:
        _raise_if_prod()
    prev_count, prev_exp = _local_login_failures.get(key, (0, now + LOGIN_LOCKOUT_SECONDS))
    new_count = prev_count + 1
    _local_login_failures[key] = (new_count, prev_exp if prev_count > 0 else now + LOGIN_LOCKOUT_SECONDS)
    return new_count


async def clear_login_failures(client: redis.Redis | None, ip: str, correo: str) -> None:
    """Reinicia el contador de fallos de login tras una autenticación válida."""
    key = _login_failure_key(ip, correo)
    _local_login_failures.pop(key, None)
    if client is not None:
        with contextlib.suppress(Exception):
            await client.delete(key)


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
    now = time.monotonic()
    expired = [k for k, exp in _local_used_refresh_jtis.items() if exp <= now]
    for k in expired:
        _local_used_refresh_jtis.pop(k, None)
    if client is not None:
        try:
            is_first = await client.set(redis_key, "1", nx=True, ex=max(1, int(ttl_seconds)))
            return bool(is_first)
        except Exception as exc:
            _raise_if_prod(exc)
    else:
        _raise_if_prod()
    if clean_jti in _local_used_refresh_jtis:
        return False
    _local_used_refresh_jtis[clean_jti] = now + max(1, int(ttl_seconds))
    return True


def build_qr_nonce_key(jti: str) -> str:
    """Construye la clave Anti-Replay en KeyDB para el JTI de un pase QR de único uso."""
    return f"qr_used:{jti.strip()}"


async def burn_qr_nonce(
    client: redis.Redis | None,
    jti: str,
    ttl_seconds: int = QR_NONCE_TTL_SECONDS,
) -> bool:
    """Registra atómicamente el consumo de un pase QR (SET NX EX) en KeyDB Multi-Hilo.

    Retorna True si el JTI no había sido quemado antes (primer uso válido).
    Retorna False si el JTI ya existía en KeyDB (intento de Replay Attack).
    """
    if client is None:
        _raise_if_prod()
        return True
    key = build_qr_nonce_key(jti)
    is_first_use = await client.set(key, "1", nx=True, ex=max(1, int(ttl_seconds)))
    return bool(is_first_use)


async def is_qr_nonce_burned(
    client: redis.Redis | None,
    jti: str,
) -> bool:
    """Verifica si un JTI de pase QR ya fue quemado o revocado en KeyDB."""
    return await _read_redis_flag(client, build_qr_nonce_key(jti))
