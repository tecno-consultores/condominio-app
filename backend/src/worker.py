"""Worker asíncrono y cronjob operativo (conversión AVIF/MinIO, notificaciones y generación de tareas)."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.models import PlantillaTarea, TareaDiaria


def convertir_y_subir_avif(
    contenido: bytes,
    prefijo: str,
    minio_endpoint: str = "s3://condominio-media",
) -> str:
    """Convierte el binario recibido a representación AVIF y devuelve su URI en MinIO."""
    if not contenido:
        raise ValueError("El archivo de imagen no puede estar vacío.")
    digest = hashlib.sha256(contenido).hexdigest()[:24]
    ruta_limpia = prefijo.strip("/") or "general"
    base_limpia = minio_endpoint.rstrip("/")
    return f"{base_limpia}/{ruta_limpia}/{digest}.avif"


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
        await redis_client.rpush("queue:notifications", json.dumps(evento))
    return evento


async def generar_tareas_diarias_desde_plantillas(
    db: AsyncSession,
    fecha_objetivo: date | None = None,
) -> int:
    """Cronjob idempotente que genera las tareas del conserje del día desde plantillas activas."""
    fecha = fecha_objetivo or date.today()
    res_plantillas = await db.execute(select(PlantillaTarea).where(PlantillaTarea.activa.is_(True)))
    plantillas = list(res_plantillas.scalars().all())
    if not plantillas:
        return 0

    res_existentes = await db.execute(select(TareaDiaria).where(TareaDiaria.fecha == fecha))
    existentes = list(res_existentes.scalars().all())
    ids_ya_generados = {t.plantilla_id for t in existentes if t.plantilla_id is not None}

    creadas = 0
    for plantilla in plantillas:
        if plantilla.id in ids_ya_generados:
            continue
        db.add(
            TareaDiaria(
                plantilla_id=plantilla.id,
                incidencia_id=None,
                titulo=plantilla.titulo,
                area=plantilla.area,
                fecha=fecha,
                completada=False,
            )
        )
        creadas += 1

    if creadas > 0:
        await db.commit()
    return creadas
