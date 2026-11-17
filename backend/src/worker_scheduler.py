"""Colas KeyDB confiables (BLMOVE/DLQ) y scheduler de tareas LPH por frecuencia (Hito 21)."""

from __future__ import annotations

import base64
import json
import logging
from collections.abc import Awaitable, Callable, Sequence
from datetime import date
from typing import Any

from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import DEFAULT_CONDOMINIO_ID, bind_rls_tenant
from src.models import PlantillaTarea, TareaDiaria

logger = logging.getLogger(__name__)

_NOTIFICATIONS_QUEUE = "queue:notifications"
_NOTIFICATIONS_PROCESSING = "queue:notifications:processing"
_NOTIFICATIONS_DLQ = "queue:notifications:dlq"
_MEDIA_QUEUE = "queue:media:avif"
_MEDIA_PROCESSING = "queue:media:avif:processing"
_MEDIA_DLQ = "queue:media:avif:dlq"
MAX_DLQ_ITEMS = 1000


async def encolar_notificacion_correo(
    destinatarios: list[str],
    asunto: str,
    cuerpo: str,
    redis_client: Any | None = None,
) -> dict[str, Any]:
    """Encola una tarea asíncrona de notificación por correo en KeyDB/Redis."""
    if not destinatarios:
        raise ValueError("Debe especificar al menos un destinatario.")
    evento: dict[str, Any] = {
        "tipo": "EMAIL_NOTIFICATION",
        "destinatarios": destinatarios,
        "asunto": asunto,
        "cuerpo": cuerpo,
    }
    if redis_client is not None and hasattr(redis_client, "rpush"):
        try:
            await redis_client.rpush(_NOTIFICATIONS_QUEUE, json.dumps(evento))
        except (RedisError, OSError) as exc:
            logger.warning("No se pudo encolar notificación en KeyDB: %s", exc)
    return evento


async def encolar_tarea_media(
    redis_client: Any,
    contenido: bytes,
    prefijo: str,
    mime_origen: str,
    objeto_key: str,
) -> dict[str, Any]:
    """Encola una evidencia binaria en la cola de procesamiento AVIF/MinIO del worker."""
    evento: dict[str, Any] = {
        "tipo": "MEDIA_UPLOAD",
        "prefijo": prefijo,
        "mime_origen": mime_origen,
        "objeto_key": objeto_key,
        "content_base64": base64.b64encode(contenido).decode("ascii"),
        "intentos": 0,
    }
    await redis_client.rpush(_MEDIA_QUEUE, json.dumps(evento))
    return evento


def debe_generar_por_frecuencia(frecuencia: str, fecha: date, fechas_previas: set[date]) -> bool:
    """Evalúa si corresponde generar una TareaDiaria para una plantilla según su frecuencia."""
    freq = (frecuencia or "DIARIA").strip().upper()
    if freq == "UNICA":
        return len(fechas_previas) == 0
    if freq == "SEMANAL":
        semana_obj = fecha.isocalendar()[:2]
        return all(f.isocalendar()[:2] != semana_obj for f in fechas_previas)
    if freq == "MENSUAL":
        mes_obj = (fecha.year, fecha.month)
        return all((f.year, f.month) != mes_obj for f in fechas_previas)
    return fecha not in fechas_previas


def _mapear_fechas_previas(tareas: Sequence[TareaDiaria], fecha_fallback: date) -> dict[int, set[date]]:
    fechas_por_plantilla: dict[int, set[date]] = {}
    for tarea in tareas:
        if tarea.plantilla_id is not None:
            fechas_por_plantilla.setdefault(int(tarea.plantilla_id), set()).add(tarea.fecha or fecha_fallback)
    return fechas_por_plantilla


def _agregar_tareas_desde_plantillas(
    db: AsyncSession,
    plantillas: Sequence[PlantillaTarea],
    fechas_por_plantilla: dict[int, set[date]],
    fecha: date,
) -> int:
    creadas = 0
    for plantilla in plantillas:
        previas = fechas_por_plantilla.get(int(plantilla.id), set())
        if not debe_generar_por_frecuencia(str(getattr(plantilla, "frecuencia", None) or "DIARIA"), fecha, previas):
            continue
        db.add(
            TareaDiaria(
                condominio_id=getattr(plantilla, "condominio_id", 1) or 1,
                plantilla_id=plantilla.id,
                incidencia_id=None,
                titulo=plantilla.titulo,
                area=plantilla.area,
                fecha=fecha,
                completada=False,
            )
        )
        creadas += 1
    return creadas


async def generar_tareas_diarias_desde_plantillas(
    db: AsyncSession,
    fecha_objetivo: date | None = None,
    condominio_id: int = DEFAULT_CONDOMINIO_ID,
) -> int:
    """Cronjob idempotente que genera las tareas del conserje respetando la frecuencia de cada plantilla."""
    await bind_rls_tenant(db, condominio_id)
    fecha = fecha_objetivo or date.today()
    res_plantillas = await db.execute(
        select(PlantillaTarea).where(
            PlantillaTarea.condominio_id == condominio_id,
            PlantillaTarea.activa.is_(True),
        )
    )
    plantillas = list(res_plantillas.scalars().all())
    if not plantillas:
        return 0

    res_existentes = await db.execute(
        select(TareaDiaria).where(
            TareaDiaria.condominio_id == condominio_id,
            TareaDiaria.plantilla_id.is_not(None),
            TareaDiaria.fecha <= fecha,
        )
    )
    fechas_por_plantilla = _mapear_fechas_previas(list(res_existentes.scalars().all()), fecha)
    creadas = _agregar_tareas_desde_plantillas(db, plantillas, fechas_por_plantilla, fecha)

    if creadas > 0:
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            return 0
    return creadas


async def enviar_a_dlq_acotado(redis_client: Any, dlq_queue: str, raw_payload: str) -> None:
    """Empuja un mensaje irrecuperable a DLQ acotándola al máximo de MAX_DLQ_ITEMS."""
    if hasattr(redis_client, "rpush"):
        await redis_client.rpush(dlq_queue, raw_payload)
    if hasattr(redis_client, "ltrim"):
        await redis_client.ltrim(dlq_queue, -MAX_DLQ_ITEMS, -1)


async def reencolar_o_dlq(
    redis_client: Any,
    evento: dict[str, Any],
    error: str,
    max_retries: int,
    *,
    queue: str = _NOTIFICATIONS_QUEUE,
    dlq_queue: str = _NOTIFICATIONS_DLQ,
) -> None:
    """Reencola con conteo de intentos o mueve a DLQ al alcanzar max_retries."""
    intentos = int(evento.get("intentos", 0)) + 1
    actualizado = dict(evento)
    actualizado["intentos"] = intentos
    actualizado["ultimo_error"] = error
    encoded = json.dumps(actualizado)
    if intentos < max_retries:
        if hasattr(redis_client, "rpush"):
            await redis_client.rpush(queue, encoded)
        return
    await enviar_a_dlq_acotado(redis_client, dlq_queue, encoded)


def decodificar_json_objeto(raw_payload: str) -> dict[str, Any] | None:
    """Decodifica un payload JSON exigiendo que represente un objeto dict."""
    try:
        evento = json.loads(raw_payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(evento, dict):
        return None
    return evento


async def consumir_cola_tick(
    redis_client: Any,
    queues: tuple[str, str],
    timeout_seconds: int,
    processor: Callable[[str], Awaitable[bool]],
) -> None:
    """Extrae un ítem con BLMOVE hacia :processing, lo procesa y limpia con LREM al finalizar."""
    src_queue, processing_queue = queues
    raw_item = await redis_client.blmove(src_queue, processing_queue, timeout_seconds, "LEFT", "RIGHT")
    if raw_item is None:
        return
    payload_str = raw_item.decode("utf-8") if isinstance(raw_item, bytes) else str(raw_item)
    try:
        await processor(payload_str)
    finally:
        if hasattr(redis_client, "lrem"):
            await redis_client.lrem(processing_queue, 1, raw_item)
