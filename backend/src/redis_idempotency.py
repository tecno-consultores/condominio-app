"""Idempotencia con replay, fallback acotado y período de gracia KeyDB (Hito 21)."""

import json
import os
import time
from dataclasses import dataclass
from typing import Any

import redis.asyncio as redis
from fastapi import HTTPException, status

GRACE_PERIOD_SECONDS = 5
IDEMPOTENCY_TTL_SECONDS = 86_400
MAX_LOCAL_SECURITY_ENTRIES = 1024

_local_idempotency_keys: dict[str, float] = {}
_local_idempotency_records: dict[str, tuple[str, float]] = {}
_local_grace_tokens: dict[str, tuple[str, float]] = {}


def is_production_env() -> bool:
    """Retorna True cuando APP_ENV corresponde a producción."""
    return os.getenv("APP_ENV", "development").strip().lower() == "production"


def raise_if_prod(exc: Exception | None = None) -> None:
    """Falla cerrado (HTTP 503) en producción cuando KeyDB no está disponible."""
    if not is_production_env():
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


def purge_expired_map(store: dict[Any, float], now: float) -> None:
    """Depura entradas expiradas de un mapa TTL local en memoria."""
    expired = [key for key, exp in store.items() if exp <= now]
    for key in expired:
        store.pop(key, None)


def store_local_ttl(store: dict[Any, float], key: Any, ttl_seconds: int) -> None:
    """Almacena una entrada acotada por LRU simple en memoria fuera de producción."""
    if is_production_env():
        return
    now = time.monotonic()
    purge_expired_map(store, now)
    if key not in store and len(store) >= MAX_LOCAL_SECURITY_ENTRIES:
        oldest_key = min(store, key=lambda k: store[k])
        store.pop(oldest_key, None)
    store[key] = now + max(1, int(ttl_seconds))


def has_local_ttl(store: dict[Any, float], key: Any) -> bool:
    """Verifica vigencia de una clave en mapa TTL local fuera de producción."""
    if is_production_env():
        return False
    now = time.monotonic()
    exp = store.get(key)
    if exp is None:
        return False
    if exp <= now:
        store.pop(key, None)
        return False
    return True


def reset_local_idempotency_state() -> None:
    """Limpia cachés locales de idempotencia y refresh grace-period en pruebas."""
    _local_idempotency_keys.clear()
    _local_idempotency_records.clear()
    _local_grace_tokens.clear()


def build_idempotency_key(scope: str, key: str) -> str:
    """Construye una clave de idempotencia aislada por ámbito/usuario (Patrón 11)."""
    clean_scope = scope.strip() or "global"
    return f"idemp:{clean_scope}:{key.strip()}"


def build_scoped_idempotency_key(condominio_id: int, usuario_id: int, scope: str, key: str) -> str:
    """Construye clave canónica idemp:{condominio_id}:{usuario_id}:{scope}:{key}."""
    clean_scope = scope.strip() or "global"
    return f"idemp:{int(condominio_id)}:{int(usuario_id)}:{clean_scope}:{key.strip()}"


@dataclass(frozen=True)
class IdempotencySlotResult:
    """Resultado de adquirir o consultar un slot de idempotencia."""

    acquired: bool
    replay_status: int | None = None
    replay_body: Any = None
    conflict_detail: str | None = None


@dataclass(frozen=True)
class IdempotencyResponsePayload:
    """Cuerpo serializable persistido tras completar una operación 2xx."""

    payload_hash: str
    status_code: int
    body: Any


def _purge_expired_local_records(now: float) -> None:
    expired = [k for k, (_, exp) in _local_idempotency_records.items() if exp <= now]
    for k in expired:
        _local_idempotency_records.pop(k, None)


def _store_local_idemp_record(redis_key: str, encoded: str, ttl_seconds: int) -> None:
    if is_production_env():
        return
    now = time.monotonic()
    _purge_expired_local_records(now)
    if redis_key not in _local_idempotency_records and len(_local_idempotency_records) >= MAX_LOCAL_SECURITY_ENTRIES:
        oldest = min(_local_idempotency_records, key=lambda k: _local_idempotency_records[k][1])
        _local_idempotency_records.pop(oldest, None)
    _local_idempotency_records[redis_key] = (encoded, now + max(1, int(ttl_seconds)))


def _get_local_idemp_record(redis_key: str) -> str | None:
    if is_production_env():
        return None
    entry = _local_idempotency_records.get(redis_key)
    if entry is None:
        return None
    encoded, exp = entry
    if exp <= time.monotonic():
        _local_idempotency_records.pop(redis_key, None)
        return None
    return encoded


def _classify_idempotency_dict(record: dict[str, Any], payload_hash: str) -> IdempotencySlotResult:
    if record.get("payload_hash") != payload_hash:
        return IdempotencySlotResult(
            acquired=False,
            conflict_detail="Idempotency-Key reutilizada con un cuerpo de solicitud distinto.",
        )
    if record.get("state") == "COMPLETED":
        status_val = record.get("status_code")
        if isinstance(status_val, int):
            return IdempotencySlotResult(
                acquired=False,
                replay_status=status_val,
                replay_body=record.get("body"),
            )
    return IdempotencySlotResult(
        acquired=False,
        conflict_detail="Petición duplicada detectada (operación en curso).",
    )


def _evaluate_existing_idempotency_record(raw: Any, payload_hash: str) -> IdempotencySlotResult:
    if not isinstance(raw, (str, bytes)):
        return IdempotencySlotResult(
            acquired=False,
            conflict_detail="Petición duplicada detectada (Idempotency-Key ya procesada).",
        )
    raw_str = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    try:
        record = json.loads(raw_str)
    except ValueError:
        return IdempotencySlotResult(
            acquired=False,
            conflict_detail="Petición duplicada detectada (Idempotency-Key ya procesada).",
        )
    if not isinstance(record, dict):
        return IdempotencySlotResult(
            acquired=False,
            conflict_detail="Petición duplicada detectada (Idempotency-Key ya procesada).",
        )
    return _classify_idempotency_dict(record, payload_hash)


async def acquire_idempotency_slot(
    client: redis.Redis | None,
    redis_key: str,
    payload_hash: str,
    ttl_seconds: int = IDEMPOTENCY_TTL_SECONDS,
) -> IdempotencySlotResult:
    """Adquiere un slot de idempotencia o retorna replay/conflicto si ya existe."""
    in_progress = json.dumps({"state": "IN_PROGRESS", "payload_hash": payload_hash}, separators=(",", ":"))
    ttl = max(1, int(ttl_seconds))
    if client is not None:
        try:
            is_new = await client.set(redis_key, in_progress, nx=True, ex=ttl)
            if is_new:
                return IdempotencySlotResult(acquired=True)
            raw = await client.get(redis_key)
            return _evaluate_existing_idempotency_record(raw, payload_hash)
        except Exception as exc:
            raise_if_prod(exc)
    else:
        raise_if_prod()
    existing = _get_local_idemp_record(redis_key)
    if existing is not None:
        return _evaluate_existing_idempotency_record(existing, payload_hash)
    _store_local_idemp_record(redis_key, in_progress, ttl)
    return IdempotencySlotResult(acquired=True)


async def store_idempotency_response(
    client: redis.Redis | None,
    redis_key: str,
    response_data: IdempotencyResponsePayload,
    ttl_seconds: int = IDEMPOTENCY_TTL_SECONDS,
) -> None:
    """Persiste la respuesta exitosa (2xx) en el slot de idempotencia para replay determinista."""
    encoded = json.dumps(
        {
            "state": "COMPLETED",
            "payload_hash": response_data.payload_hash,
            "status_code": int(response_data.status_code),
            "body": response_data.body,
        },
        separators=(",", ":"),
    )
    ttl = max(1, int(ttl_seconds))
    if client is not None:
        try:
            await client.set(redis_key, encoded, ex=ttl)
            return
        except Exception as exc:
            raise_if_prod(exc)
    else:
        raise_if_prod()
    _store_local_idemp_record(redis_key, encoded, ttl)


async def release_idempotency_slot(client: redis.Redis | None, redis_key: str) -> None:
    """Libera la clave de idempotencia cuando una mutación falla (4xx/5xx)."""
    _local_idempotency_records.pop(redis_key, None)
    if client is None:
        return
    try:
        await client.delete(redis_key)
    except Exception:
        return


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
            raise_if_prod(exc)
    else:
        raise_if_prod()
    if has_local_ttl(_local_idempotency_keys, redis_key):
        return False
    store_local_ttl(_local_idempotency_keys, redis_key, ttl_seconds)
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
            raise_if_prod(exc)
    else:
        raise_if_prod()
    if not is_production_env():
        _local_grace_tokens[old_token_family_id] = (new_token, time.monotonic() + max(1, grace_seconds))


def _get_local_grace_token(old_token_family_id: str) -> str | None:
    if is_production_env():
        return None
    entry = _local_grace_tokens.get(old_token_family_id)
    if entry is None:
        return None
    if entry[1] > time.monotonic():
        return entry[0]
    _local_grace_tokens.pop(old_token_family_id, None)
    return None


async def get_refresh_token_from_grace_period(
    client: redis.Redis | None,
    old_token_family_id: str,
) -> str | None:
    """Recupera el nuevo token si la rotación ocurrió dentro del grace period de 5s."""
    local_token = _get_local_grace_token(old_token_family_id)
    if local_token is not None:
        return local_token
    if client is None:
        raise_if_prod()
        return None
    try:
        val = await client.get(f"grace_period:{old_token_family_id}")
        return str(val) if val is not None else None
    except Exception as exc:
        raise_if_prod(exc)
        return None
