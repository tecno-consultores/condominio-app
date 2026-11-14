"""Worker asíncrono y supervisor productivo Nivel 11X (AVIF/MinIO, KeyDB/SMTP, scheduler LPH y QA-HEALTH-01)."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import hmac
import json
import logging
import os
import signal
import smtplib
import ssl
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import AsyncSessionLocal
from src.models import PlantillaTarea, TareaDiaria
from src.redis_client import get_redis_client
from src.security import validate_production_security_settings

logger = logging.getLogger(__name__)

DEFAULT_HEARTBEAT_PATH = Path(tempfile.gettempdir()) / "worker_heartbeat"
OPTIONAL_WORKERS: frozenset[str] = frozenset({"media_avif_consumer"})
_NOTIFICATIONS_QUEUE = "queue:notifications"
_NOTIFICATIONS_DLQ = "queue:notifications:dlq"
_MEDIA_QUEUE = "queue:media:avif"


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


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

    @classmethod
    def from_env(cls) -> WorkerSettings:
        hb_raw = os.getenv("WORKER_HEARTBEAT_PATH", "").strip()
        hb_path = Path(hb_raw) if hb_raw else DEFAULT_HEARTBEAT_PATH
        return cls(
            heartbeat_path=hb_path,
            poll_seconds=_env_float("WORKER_POLL_SECONDS", 1.0),
            blpop_timeout_seconds=max(1, _env_int("WORKER_BLPOP_TIMEOUT_SECONDS", 1)),
            scheduler_interval_seconds=_env_float("WORKER_SCHEDULER_INTERVAL_SECONDS", 300.0),
            max_heartbeat_age_seconds=_env_float("WORKER_HEARTBEAT_MAX_AGE_SECONDS", 90.0),
            media_enabled=_env_flag("WORKER_MEDIA_ENABLED", False),
            smtp_enabled=_env_flag("SMTP_ENABLED", False),
            smtp_host=os.getenv("SMTP_HOST", "").strip(),
            smtp_port=_env_int("SMTP_PORT", 587),
            smtp_user=os.getenv("SMTP_USER", "").strip(),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            smtp_from=os.getenv("SMTP_FROM", "no-responder@condominio.local").strip(),
            smtp_use_tls=_env_flag("SMTP_USE_TLS", True),
            max_retries=max(1, _env_int("WORKER_MAX_RETRIES", 3)),
            minio_endpoint=os.getenv("MINIO_ENDPOINT", "").strip(),
        )


def _hmac_sha256(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def _signing_key_sigv4(secret_key: str, date_stamp: str, region: str, service: str) -> bytes:
    k_date = _hmac_sha256(f"AWS4{secret_key}".encode("utf-8"), date_stamp)
    k_region = _hmac_sha256(k_date, region)
    k_service = _hmac_sha256(k_region, service)
    return _hmac_sha256(k_service, "aws4_request")


def _build_sigv4_headers(
    host: str,
    canonical_uri: str,
    payload_hash: str,
    access_key: str,
    secret_key: str,
    region: str = "us-east-1",
) -> dict[str, str]:
    now_utc = datetime.now(UTC)
    amz_date = now_utc.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now_utc.strftime("%Y%m%d")
    canonical_headers = f"host:{host}\nx-amz-content-sha256:{payload_hash}\nx-amz-date:{amz_date}\n"
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = f"PUT\n{canonical_uri}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    credential_scope = f"{date_stamp}/{region}/s3/aws4_request"
    request_digest = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    string_to_sign = f"AWS4-HMAC-SHA256\n{amz_date}\n{credential_scope}\n{request_digest}"
    signing_key = _signing_key_sigv4(secret_key, date_stamp, region, "s3")
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = (
        f"AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    return {
        "Host": host,
        "Content-Type": "image/avif",
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
        "Authorization": authorization,
    }


def codificar_imagen_avif(contenido: bytes, *, strict_image: bool = False) -> bytes:
    """Transcodifica bytes de imagen a formato AVIF corrigiendo orientación EXIF."""
    if not contenido:
        raise ValueError("El archivo de imagen no puede estar vacío.")
    try:
        with Image.open(BytesIO(contenido)) as img:
            normalized = ImageOps.exif_transpose(img).convert("RGB")
            salida = BytesIO()
            normalized.save(salida, format="AVIF", quality=60)
            return salida.getvalue()
    except (UnidentifiedImageError, OSError) as exc:
        if strict_image:
            raise ValueError("Contenido de imagen inválido para conversión AVIF.") from exc
        return contenido


def subir_objeto_minio_s3(
    datos_avif: bytes,
    objeto_key: str,
    minio_endpoint: str,
    *,
    bucket_name: str | None = None,
    http_client: httpx.Client | None = None,
) -> str:
    """Sube bytes AVIF a MinIO mediante HTTP PUT autenticado con AWS SigV4."""
    access_key = os.getenv("MINIO_ROOT_USER", "").strip()
    secret_key = os.getenv("MINIO_ROOT_PASSWORD", "")
    if not access_key or not secret_key:
        raise ValueError("Credenciales MinIO no configuradas para carga S3.")

    raw_bucket = (
        bucket_name
        if bucket_name is not None and bucket_name.strip()
        else (os.getenv("MINIO_BUCKET_NAME") or os.getenv("MINIO_BUCKET") or "condominio-media")
    )
    bucket = raw_bucket.strip() or "condominio-media"
    base_url = minio_endpoint.rstrip("/")
    parsed = urlparse(base_url)
    base_path = parsed.path.rstrip("/")
    canonical_uri = f"{base_path}/{bucket}/{objeto_key}"
    upload_url = f"{base_url}/{bucket}/{objeto_key}"
    payload_hash = hashlib.sha256(datos_avif).hexdigest()
    headers = _build_sigv4_headers(parsed.netloc, canonical_uri, payload_hash, access_key, secret_key)

    if http_client is not None:
        resp = http_client.put(upload_url, content=datos_avif, headers=headers, timeout=15.0)
        resp.raise_for_status()
    else:
        with httpx.Client(timeout=15.0) as client:
            resp = client.put(upload_url, content=datos_avif, headers=headers)
            resp.raise_for_status()
    return f"s3://{bucket}/{objeto_key}"


def convertir_y_subir_avif(
    contenido: bytes,
    prefijo: str,
    minio_endpoint: str = "s3://condominio-media",
    *,
    strict_image: bool = False,
    http_client: httpx.Client | None = None,
) -> str:
    """Convierte el binario recibido a formato AVIF y lo carga en MinIO si hay endpoint HTTP(S)."""
    datos_avif = codificar_imagen_avif(contenido, strict_image=strict_image)
    digest = hashlib.sha256(datos_avif).hexdigest()[:24]
    ruta_limpia = prefijo.strip("/") or "general"
    objeto_key = f"{ruta_limpia}/{digest}.avif"
    base_limpia = minio_endpoint.rstrip("/")
    if base_limpia.startswith(("http://", "https://")):
        return subir_objeto_minio_s3(datos_avif, objeto_key, base_limpia, http_client=http_client)
    return f"{base_limpia}/{objeto_key}"


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
        await redis_client.rpush(_NOTIFICATIONS_QUEUE, json.dumps(evento))
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

    if creadas > 0:
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            return 0
    return creadas


def _sanitize_header(valor: str) -> str:
    return valor.replace("\r", " ").replace("\n", " ").strip()


def enviar_correo_smtp(evento: dict[str, Any], settings: WorkerSettings) -> None:
    """Envía una notificación por SMTP STARTTLS cuando SMTP está habilitado."""
    destinatarios = [str(d).strip() for d in evento.get("destinatarios", []) if str(d).strip()]
    if not destinatarios:
        raise ValueError("Evento de notificación sin destinatarios válidos.")
    if not settings.smtp_enabled or not settings.smtp_host:
        logger.info(
            "Notificación omitida (SMTP deshabilitado): asunto=%s", _sanitize_header(str(evento.get("asunto", "")))
        )
        return

    msg = EmailMessage()
    msg["From"] = _sanitize_header(settings.smtp_from)
    msg["To"] = _sanitize_header(", ".join(destinatarios))
    msg["Subject"] = _sanitize_header(str(evento.get("asunto", "")))
    msg.set_content(str(evento.get("cuerpo", "")))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls(context=ssl.create_default_context())
        if settings.smtp_user and settings.smtp_password:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)


async def _reencolar_o_dlq(
    redis_client: Any,
    evento: dict[str, Any],
    error: str,
    max_retries: int,
) -> None:
    intentos = int(evento.get("intentos", 0)) + 1
    actualizado = dict(evento)
    actualizado["intentos"] = intentos
    actualizado["ultimo_error"] = error
    destino = _NOTIFICATIONS_QUEUE if intentos < max_retries else _NOTIFICATIONS_DLQ
    if hasattr(redis_client, "rpush"):
        await redis_client.rpush(destino, json.dumps(actualizado))


async def procesar_mensaje_notificacion(
    raw_payload: str,
    redis_client: Any,
    settings: WorkerSettings,
) -> bool:
    """Procesa un payload JSON de correo y aplica reintento acotado o envío a DLQ."""
    try:
        evento = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        logger.warning("Payload malformado enviado a DLQ: %s", exc)
        if hasattr(redis_client, "rpush"):
            await redis_client.rpush(_NOTIFICATIONS_DLQ, raw_payload)
        return False

    try:
        await asyncio.to_thread(enviar_correo_smtp, evento, settings)
        return True
    except (OSError, smtplib.SMTPException, ValueError) as exc:
        logger.warning("Fallo procesando notificación por correo: %s", exc)
        await _reencolar_o_dlq(redis_client, evento, str(exc), settings.max_retries)
        return False


def is_supervisor_healthy(tasks: dict[str, asyncio.Task[None]]) -> bool:
    """Evalúa salud del supervisor QA-HEALTH-01 diferenciando workers opcionales deshabilitados."""
    for name, task in tasks.items():
        if task.cancelled():
            return False
        if task.done():
            if task.exception() is not None:
                return False
            if name not in OPTIONAL_WORKERS:
                return False
    return True


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


async def _consumir_cola_notificaciones_tick(
    redis_client: Any,
    settings: WorkerSettings,
) -> None:
    item = await redis_client.blpop(_NOTIFICATIONS_QUEUE, timeout=settings.blpop_timeout_seconds)
    if not item:
        return
    _, raw_payload = item
    payload_str = raw_payload.decode("utf-8") if isinstance(raw_payload, bytes) else str(raw_payload)
    await procesar_mensaje_notificacion(payload_str, redis_client, settings)


async def _loop_notificaciones(
    settings: WorkerSettings,
    stop_event: asyncio.Event,
    redis_getter: Callable[[], Any],
) -> None:
    while not stop_event.is_set():
        try:
            redis_client = redis_getter()
            await _consumir_cola_notificaciones_tick(redis_client, settings)
        except (OSError, RuntimeError) as exc:
            logger.warning("Error transitorio en consumidor KeyDB de notificaciones: %s", exc)
            await _esperar_o_detener(stop_event, settings.poll_seconds)


async def _loop_media_opcional(
    settings: WorkerSettings,
    stop_event: asyncio.Event,
    redis_getter: Callable[[], Any],
) -> None:
    if not settings.media_enabled:
        return
    while not stop_event.is_set():
        try:
            redis_client = redis_getter()
            await redis_client.blpop(_MEDIA_QUEUE, timeout=settings.blpop_timeout_seconds)
        except (OSError, RuntimeError) as exc:
            logger.warning("Error transitorio en cola de medios AVIF: %s", exc)
            await _esperar_o_detener(stop_event, settings.poll_seconds)


async def _cancelar_tareas(tasks: dict[str, asyncio.Task[None]]) -> None:
    for task in tasks.values():
        if not task.done():
            task.cancel()
    await asyncio.gather(*tasks.values(), return_exceptions=True)


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
    db_factory = session_factory or AsyncSessionLocal
    redis_fn = redis_getter or get_redis_client

    tasks: dict[str, asyncio.Task[None]] = {
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

    ticks = 0
    try:
        while not evento_parada.is_set():
            await asyncio.sleep(0)
            if not is_supervisor_healthy(tasks):
                logger.error("Supervisor worker detectó estado no saludable.")
                cfg.heartbeat_path.unlink(missing_ok=True)
                return 1
            write_worker_heartbeat(cfg.heartbeat_path)
            ticks += 1
            if max_ticks is not None and ticks >= max_ticks:
                break
            await _esperar_o_detener(evento_parada, cfg.poll_seconds)
        return 0
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


if __name__ == "__main__":
    raise SystemExit(main())
