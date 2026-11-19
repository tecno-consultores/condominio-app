"""Worker asíncrono y supervisor productivo Nivel 11X (AVIF/MinIO, KeyDB/SMTP, scheduler LPH y QA-HEALTH-01)."""

from __future__ import annotations

import argparse
import asyncio
import binascii
import contextlib
import logging
import os
import signal
import smtplib
import ssl
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import httpx
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from src.database import AsyncSessionLocal
from src.redis_client import get_redis_client
from src.security import validate_production_security_settings
from src.worker_media import (
    MAX_IMAGE_PIXELS,
    _build_sigv4_headers,
    codificar_imagen_avif,
    construir_clave_evidencia,
    convertir_y_subir_avif,
    ejecutar_subida_media_bytes,
    env_flag,
    normalize_minio_endpoint,
    resolver_bucket_minio,
    subir_objeto_minio_s3,
)
from src.worker_scheduler import (
    _MEDIA_DLQ,
    _MEDIA_PROCESSING,
    _MEDIA_QUEUE,
    _NOTIFICATIONS_DLQ,
    _NOTIFICATIONS_PROCESSING,
    _NOTIFICATIONS_QUEUE,
    MAX_DLQ_ITEMS,
    consumir_cola_tick,
    decodificar_json_objeto,
    encolar_notificacion_correo,
    encolar_tarea_media,
    enviar_a_dlq_acotado,
    generar_tareas_diarias_desde_plantillas,
    reencolar_o_dlq,
)

__all__ = [
    "DEFAULT_HEARTBEAT_PATH",
    "MAX_DLQ_ITEMS",
    "MAX_IMAGE_PIXELS",
    "OPTIONAL_WORKERS",
    "WorkerSettings",
    "_MEDIA_DLQ",
    "_MEDIA_PROCESSING",
    "_MEDIA_QUEUE",
    "_NOTIFICATIONS_DLQ",
    "_NOTIFICATIONS_PROCESSING",
    "_NOTIFICATIONS_QUEUE",
    "_build_sigv4_headers",
    "_normalize_minio_endpoint",
    "codificar_imagen_avif",
    "construir_clave_evidencia",
    "convertir_y_subir_avif",
    "encolar_notificacion_correo",
    "encolar_tarea_media",
    "enviar_correo_smtp",
    "generar_tareas_diarias_desde_plantillas",
    "is_supervisor_healthy",
    "main",
    "normalize_minio_endpoint",
    "procesar_mensaje_media",
    "procesar_mensaje_notificacion",
    "resolver_bucket_minio",
    "run_worker_orchestrator",
    "subir_objeto_minio_s3",
    "verify_worker_heartbeat",
    "write_worker_heartbeat",
]

logger = logging.getLogger(__name__)
_normalize_minio_endpoint = normalize_minio_endpoint

DEFAULT_HEARTBEAT_PATH = Path(tempfile.gettempdir()) / "worker_heartbeat"
OPTIONAL_WORKERS: frozenset[str] = frozenset({"media_avif_consumer"})


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    return float(raw) if raw else default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw else default


@dataclass(frozen=True)
class WorkerSettings:
    """Configuración inmutable del proceso worker resuelta desde variables de entorno."""

    heartbeat_path: Path = DEFAULT_HEARTBEAT_PATH
    poll_seconds: float = 1.0
    blpop_timeout_seconds: int = 1
    scheduler_interval_seconds: float = 300.0
    max_heartbeat_age_seconds: float = 90.0
    media_enabled: bool = False
    smtp_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "no-responder@condominio.local"
    smtp_use_tls: bool = True
    max_retries: int = 3
    minio_endpoint: str = ""
    minio_use_ssl: bool = False

    @classmethod
    def from_env(cls) -> WorkerSettings:
        hb_raw = os.getenv("WORKER_HEARTBEAT_PATH", "").strip()
        hb_path = Path(hb_raw) if hb_raw else DEFAULT_HEARTBEAT_PATH
        minio_use_ssl = env_flag("MINIO_USE_SSL", False)
        return cls(
            heartbeat_path=hb_path,
            poll_seconds=_env_float("WORKER_POLL_SECONDS", 1.0),
            blpop_timeout_seconds=max(1, _env_int("WORKER_BLPOP_TIMEOUT_SECONDS", 1)),
            scheduler_interval_seconds=_env_float("WORKER_SCHEDULER_INTERVAL_SECONDS", 300.0),
            max_heartbeat_age_seconds=_env_float("WORKER_HEARTBEAT_MAX_AGE_SECONDS", 90.0),
            media_enabled=env_flag("WORKER_MEDIA_ENABLED", False),
            smtp_enabled=env_flag("SMTP_ENABLED", False),
            smtp_host=os.getenv("SMTP_HOST", "").strip(),
            smtp_port=_env_int("SMTP_PORT", 587),
            smtp_user=os.getenv("SMTP_USER", "").strip(),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            smtp_from=os.getenv("SMTP_FROM", "no-responder@condominio.local").strip(),
            smtp_use_tls=env_flag("SMTP_USE_TLS", True),
            max_retries=max(1, _env_int("WORKER_MAX_RETRIES", 3)),
            minio_endpoint=normalize_minio_endpoint(os.getenv("MINIO_ENDPOINT", ""), minio_use_ssl),
            minio_use_ssl=minio_use_ssl,
        )


def _sanitize_header(valor: str) -> str:
    return valor.replace("\r", " ").replace("\n", " ").strip()


def _extraer_destinatarios(evento: dict[str, Any]) -> list[str]:
    destinatarios = [str(d).strip() for d in evento.get("destinatarios", []) if str(d).strip()]
    if not destinatarios:
        raise ValueError("Evento de notificación sin destinatarios válidos.")
    return destinatarios


def _construir_mensaje_correo(evento: dict[str, Any], destinatarios: list[str], smtp_from: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = _sanitize_header(smtp_from)
    msg["To"] = _sanitize_header(", ".join(destinatarios))
    msg["Subject"] = _sanitize_header(str(evento.get("asunto", "")))
    msg.set_content(str(evento.get("cuerpo", "")))
    return msg


def _despachar_smtp(msg: EmailMessage, settings: WorkerSettings) -> None:
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls(context=ssl.create_default_context())
        if settings.smtp_user and settings.smtp_password:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)


def enviar_correo_smtp(evento: dict[str, Any], settings: WorkerSettings) -> None:
    """Envía una notificación por SMTP STARTTLS cuando SMTP está habilitado."""
    destinatarios = _extraer_destinatarios(evento)
    if not settings.smtp_enabled or not settings.smtp_host:
        logger.info(
            "Notificación omitida (SMTP deshabilitado): asunto=%s", _sanitize_header(str(evento.get("asunto", "")))
        )
        return
    msg = _construir_mensaje_correo(evento, destinatarios, settings.smtp_from)
    _despachar_smtp(msg, settings)


async def procesar_mensaje_notificacion(
    raw_payload: str,
    redis_client: Any,
    settings: WorkerSettings,
) -> bool:
    """Procesa un payload JSON de correo y aplica reintento acotado o envío a DLQ."""
    evento = decodificar_json_objeto(raw_payload)
    if evento is None:
        logger.warning("Payload malformado o no-objeto enviado a DLQ de notificaciones.")
        await enviar_a_dlq_acotado(redis_client, _NOTIFICATIONS_DLQ, raw_payload)
        return False

    try:
        await asyncio.to_thread(enviar_correo_smtp, evento, settings)
        return True
    except (OSError, smtplib.SMTPException, ValueError) as exc:
        logger.warning("Fallo procesando notificación por correo: %s", exc)
        await reencolar_o_dlq(redis_client, evento, str(exc), settings.max_retries)
        return False


async def procesar_mensaje_media(
    raw_payload: str,
    redis_client: Any,
    settings: WorkerSettings,
) -> bool:
    """Procesa una evidencia de imagen/PDF desde KeyDB convirtiéndola a AVIF y cargándola a MinIO."""
    evento = decodificar_json_objeto(raw_payload)
    if evento is None:
        logger.warning("Payload malformado o no-objeto enviado a DLQ de medios.")
        await enviar_a_dlq_acotado(redis_client, _MEDIA_DLQ, raw_payload)
        return False

    try:
        await asyncio.to_thread(ejecutar_subida_media_bytes, evento, settings.minio_endpoint, settings.minio_use_ssl)
        return True
    except (ValueError, OSError, httpx.HTTPError, binascii.Error) as exc:
        logger.warning("Fallo procesando evidencia multimedia: %s", exc)
        await reencolar_o_dlq(
            redis_client,
            evento,
            str(exc),
            settings.max_retries,
            queue=_MEDIA_QUEUE,
            dlq_queue=_MEDIA_DLQ,
        )
        return False


def _is_task_healthy(name: str, task: asyncio.Task[None]) -> bool:
    if task.cancelled():
        return False
    if not task.done():
        return True
    return task.exception() is None and name in OPTIONAL_WORKERS


def is_supervisor_healthy(tasks: dict[str, asyncio.Task[None]]) -> bool:
    """Evalúa salud del supervisor QA-HEALTH-01 diferenciando workers opcionales deshabilitados."""
    return all(_is_task_healthy(name, task) for name, task in tasks.items())


def write_worker_heartbeat(heartbeat_path: Path) -> None:
    """Persiste el marcador físico de latido verificado por el HEALTHCHECK del contenedor."""
    heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
    heartbeat_path.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")


def verify_worker_heartbeat(heartbeat_path: Path, max_age_seconds: float = 90.0) -> bool:
    """Comprueba existencia y frescura del archivo de heartbeat del worker."""
    if not heartbeat_path.is_file():
        return False
    edad = time.time() - heartbeat_path.stat().st_mtime
    return 0.0 <= edad <= max_age_seconds


async def _esperar_o_detener(stop_event: asyncio.Event, timeout_seconds: float) -> None:
    with contextlib.suppress(TimeoutError):
        await asyncio.wait_for(stop_event.wait(), timeout=timeout_seconds)


async def _loop_scheduler_diario(
    settings: WorkerSettings,
    stop_event: asyncio.Event,
    session_factory: Callable[[], Any],
) -> None:
    while not stop_event.is_set():
        try:
            async with session_factory() as session:
                await generar_tareas_diarias_desde_plantillas(session)
        except SQLAlchemyError as exc:
            logger.warning("Error transitorio generando tareas diarias: %s", exc)
        await _esperar_o_detener(stop_event, settings.scheduler_interval_seconds)


async def _consumir_cola_notificaciones_tick(redis_client: Any, settings: WorkerSettings) -> None:
    await consumir_cola_tick(
        redis_client,
        (_NOTIFICATIONS_QUEUE, _NOTIFICATIONS_PROCESSING),
        settings.blpop_timeout_seconds,
        lambda payload: procesar_mensaje_notificacion(payload, redis_client, settings),
    )


async def _consumir_cola_media_tick(redis_client: Any, settings: WorkerSettings) -> None:
    await consumir_cola_tick(
        redis_client,
        (_MEDIA_QUEUE, _MEDIA_PROCESSING),
        settings.blpop_timeout_seconds,
        lambda payload: procesar_mensaje_media(payload, redis_client, settings),
    )


async def _loop_notificaciones(
    settings: WorkerSettings,
    stop_event: asyncio.Event,
    redis_getter: Callable[[], Any],
) -> None:
    fallos = 0
    while not stop_event.is_set():
        try:
            await _consumir_cola_notificaciones_tick(redis_getter(), settings)
            fallos = 0
        except (RedisError, OSError, RuntimeError) as exc:
            fallos += 1
            delay = min(settings.poll_seconds * (2 ** min(fallos - 1, 4)), 5.0)
            logger.warning("Error transitorio en consumidor KeyDB de notificaciones: %s", exc)
            await _esperar_o_detener(stop_event, delay)


async def _loop_media_opcional(
    settings: WorkerSettings,
    stop_event: asyncio.Event,
    redis_getter: Callable[[], Any],
) -> None:
    if not settings.media_enabled:
        return
    fallos = 0
    while not stop_event.is_set():
        try:
            await _consumir_cola_media_tick(redis_getter(), settings)
            fallos = 0
        except (RedisError, OSError, RuntimeError) as exc:
            fallos += 1
            delay = min(settings.poll_seconds * (2 ** min(fallos - 1, 4)), 5.0)
            logger.warning("Error transitorio en cola de medios AVIF: %s", exc)
            await _esperar_o_detener(stop_event, delay)


async def _cancelar_tareas(tasks: dict[str, asyncio.Task[None]]) -> None:
    for task in tasks.values():
        if not task.done():
            task.cancel()
    await asyncio.gather(*tasks.values(), return_exceptions=True)


def _crear_tareas_supervisor(
    cfg: WorkerSettings,
    evento_parada: asyncio.Event,
    session_factory: Callable[[], Any] | None,
    redis_getter: Callable[[], Any] | None,
) -> dict[str, asyncio.Task[None]]:
    db_factory = session_factory or AsyncSessionLocal
    redis_fn = redis_getter or get_redis_client
    return {
        "daily_tasks_scheduler": asyncio.create_task(
            _loop_scheduler_diario(cfg, evento_parada, db_factory),
            name="daily_tasks_scheduler",
        ),
        "notifications_consumer": asyncio.create_task(
            _loop_notificaciones(cfg, evento_parada, redis_fn),
            name="notifications_consumer",
        ),
        "media_avif_consumer": asyncio.create_task(
            _loop_media_opcional(cfg, evento_parada, redis_fn),
            name="media_avif_consumer",
        ),
    }


def _alcanzo_max_ticks(ticks: int, max_ticks: int | None) -> bool:
    return max_ticks is not None and ticks >= max_ticks


async def _supervisar_ciclo_worker(
    cfg: WorkerSettings,
    evento_parada: asyncio.Event,
    tasks: dict[str, asyncio.Task[None]],
    max_ticks: int | None,
) -> int:
    ticks = 0
    while not evento_parada.is_set():
        await asyncio.sleep(0)
        if not is_supervisor_healthy(tasks):
            logger.error("Supervisor worker detectó estado no saludable.")
            cfg.heartbeat_path.unlink(missing_ok=True)
            return 1
        write_worker_heartbeat(cfg.heartbeat_path)
        ticks += 1
        if _alcanzo_max_ticks(ticks, max_ticks):
            break
        await _esperar_o_detener(evento_parada, cfg.poll_seconds)
    return 0


async def run_worker_orchestrator(
    settings: WorkerSettings | None = None,
    *,
    stop_event: asyncio.Event | None = None,
    max_ticks: int | None = None,
    session_factory: Callable[[], Any] | None = None,
    redis_getter: Callable[[], Any] | None = None,
) -> int:
    """Arranca los loops del worker bajo supervisión QA-HEALTH-01 y emite heartbeat físico."""
    validate_production_security_settings()
    cfg = settings or WorkerSettings.from_env()
    evento_parada = stop_event or asyncio.Event()
    tasks = _crear_tareas_supervisor(cfg, evento_parada, session_factory, redis_getter)
    try:
        return await _supervisar_ciclo_worker(cfg, evento_parada, tasks, max_ticks)
    finally:
        evento_parada.set()
        await _cancelar_tareas(tasks)


async def _run_with_signals(cfg: WorkerSettings, max_ticks: int | None) -> int:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)
    return await run_worker_orchestrator(cfg, stop_event=stop_event, max_ticks=max_ticks)


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.worker",
        description="Worker asíncrono de Condominio App (AVIF/MinIO, KeyDB/SMTP y scheduler diario).",
    )
    parser.add_argument(
        "--check-health",
        action="store_true",
        help="Verifica el heartbeat físico del worker (código 0 si saludable, 1 si degradado).",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Ejecuta un ciclo de supervisión verificando arranque productivo y finaliza.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Punto de entrada CLI productivo para el contenedor worker."""
    parser = _build_cli_parser()
    args = parser.parse_args(argv)
    cfg = WorkerSettings.from_env()
    if args.check_health:
        return 0 if verify_worker_heartbeat(cfg.heartbeat_path, cfg.max_heartbeat_age_seconds) else 1
    max_ticks = 1 if args.once else None
    return asyncio.run(_run_with_signals(cfg, max_ticks))
