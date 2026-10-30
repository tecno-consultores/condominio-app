"""Cliente asíncrono KeyDB/Redis: idempotencia aislada por ámbito y grace period de tokens."""

import contextlib
import os

import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
GRACE_PERIOD_SECONDS = 5
REVOKED_USER_TTL_SECONDS = 86_400
QR_NONCE_TTL_SECONDS = 259_200

_redis_client: redis.Redis | None = None
_local_revoked_users: set[int] = set()


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
    ttl_seconds: int = 120,
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
    client: redis.Redis,
    old_token_family_id: str,
    new_token: str,
    grace_seconds: int = GRACE_PERIOD_SECONDS,
) -> None:
    """Almacena un token rotado con ventana de cortesía de 5s para pestañas concurrentes (Patrón 10)."""
    await client.set(
        f"grace_period:{old_token_family_id}",
        new_token,
        ex=grace_seconds,
    )


async def get_refresh_token_from_grace_period(
    client: redis.Redis,
    old_token_family_id: str,
) -> str | None:
    """Recupera el nuevo token si la rotación ocurrió dentro del grace period de 5s."""
    val = await client.get(f"grace_period:{old_token_family_id}")
    return str(val) if val is not None else None


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
    if client is not None:
        try:
            val = await client.get(f"revoked_user:{uid}")
            return val in ("1", b"1")
        except Exception:
            return False
    return False


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
        return True
    key = build_qr_nonce_key(jti)
    is_first_use = await client.set(key, "1", nx=True, ex=max(1, int(ttl_seconds)))
    return bool(is_first_use)


async def is_qr_nonce_burned(
    client: redis.Redis | None,
    jti: str,
) -> bool:
    """Verifica si un JTI de pase QR ya fue quemado o revocado en KeyDB."""
    if client is None:
        return False
    try:
        val = await client.get(build_qr_nonce_key(jti))
        return val in ("1", b"1")
    except Exception:
        return False
