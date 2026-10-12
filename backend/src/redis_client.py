import os
from typing import Optional

import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Instancia global o fábrica para conexión asíncrona a Redis
_redis_client: Optional[redis.Redis] = None

def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client

async def check_and_set_idempotency_key(client: redis.Redis, key: str, ttl_seconds: int = 120) -> bool:
    """
    Verifica y almacena una clave de idempotencia atómicamente.
    Retorna True si la clave es NUEVA (se adquirió el candado).
    Retorna False si la clave ya existía (petición duplicada).
    """
    redis_key = f"idempotency:{key}"
    is_new = await client.set(redis_key, "1", nx=True, ex=ttl_seconds)
    return bool(is_new)
