"""Pruebas unitarias e integración Nivel 11X para el Hito 18 (Worker real AVIF/MinIO, KeyDB/SMTP y QA-HEALTH-01)."""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import logging
import os
import secrets
import signal
import smtplib
import ssl
import tempfile
from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from PIL import Image
from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src import worker as worker_mod
from src import worker_scheduler as scheduler_mod
from src.database import Base
from src.models import PlantillaTarea, TareaDiaria
from src.worker import (
    DEFAULT_HEARTBEAT_PATH,
    MAX_DLQ_ITEMS,
    OPTIONAL_WORKERS,
    WorkerSettings,
    codificar_imagen_avif,
    convertir_y_subir_avif,
    enviar_correo_smtp,
    env_flag,
    generar_tareas_diarias_desde_plantillas,
    is_supervisor_healthy,
    main,
    procesar_mensaje_media,
    procesar_mensaje_notificacion,
    run_worker_orchestrator,
    subir_objeto_minio_s3,
    verify_worker_heartbeat,
    write_worker_heartbeat,
)
from src.worker_scheduler import (
    consumir_cola_tick,
    debe_generar_por_frecuencia,
    decodificar_json_objeto,
    encolar_notificacion_correo,
    encolar_tarea_media,
    enviar_a_dlq_acotado,
    reencolar_o_dlq,
)


def _crear_png_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (16, 16), color=(24, 96, 168)).save(buf, format="PNG")
    return buf.getvalue()


def test_codificar_y_subir_avif_real_con_sigv4(monkeypatch: pytest.MonkeyPatch) -> None:
    png_bytes = _crear_png_bytes()
    avif_bytes = codificar_imagen_avif(png_bytes, strict_image=True)
    with Image.open(BytesIO(avif_bytes)) as img_avif:
        assert img_avif.format == "AVIF"

    with pytest.raises(ValueError, match="inválido"):
        codificar_imagen_avif(b"contenido-no-imagen", strict_image=True)

    assert codificar_imagen_avif(b"contenido-no-imagen", strict_image=False) == b"contenido-no-imagen"

    capturado: dict[str, Any] = {}

    def _handler(request: httpx.Request) -> httpx.Response:
        capturado["method"] = request.method
        capturado["url"] = str(request.url)
        capturado["headers"] = dict(request.headers)
        capturado["size"] = len(request.content)
        return httpx.Response(200)

    monkeypatch.setenv("MINIO_ROOT_USER", "minio_qa_user")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "minio_qa_secret_123")
    monkeypatch.setenv("MINIO_BUCKET_NAME", "condo-test")

    with httpx.Client(transport=httpx.MockTransport(_handler)) as client:
        uri = convertir_y_subir_avif(
            png_bytes,
            "incidencias/2026-11",
            minio_endpoint="http://minio.local:9000",
            strict_image=True,
            http_client=client,
        )

    assert uri.startswith("s3://condo-test/incidencias/2026-11/")
    assert uri.endswith(".avif")
    assert capturado["method"] == "PUT"
    assert capturado["headers"]["content-type"] == "image/avif"
    assert capturado["headers"]["authorization"].startswith("AWS4-HMAC-SHA256 ")
    assert "x-amz-content-sha256" in capturado["headers"]
    assert capturado["size"] > 0

    monkeypatch.delenv("MINIO_ROOT_USER", raising=False)
    monkeypatch.delenv("MINIO_ROOT_PASSWORD", raising=False)
    with pytest.raises(ValueError, match="Credenciales MinIO"):
        subir_objeto_minio_s3(avif_bytes, "incidencias/a.avif", "http://minio.local:9000")


async def test_tarea_diaria_unique_constraint_y_carrera_db(tmp_path: Path) -> None:
    db_file = tmp_path / "hito18_tareas.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    fecha = date(2026, 11, 14)
    async with session_factory() as db:
        plantilla = PlantillaTarea(titulo="Inspección bombas", area="Sótano", frecuencia="DIARIA", activa=True)
        db.add(plantilla)
        await db.commit()
        await db.refresh(plantilla)

        assert await generar_tareas_diarias_desde_plantillas(db, fecha_objetivo=fecha) == 1
        assert await generar_tareas_diarias_desde_plantillas(db, fecha_objetivo=fecha) == 0

        # Múltiples tareas ad-hoc (plantilla_id=None) están permitidas en la misma fecha
        db.add(TareaDiaria(plantilla_id=None, titulo="Ad-hoc 1", area="Lobby", fecha=fecha))
        db.add(TareaDiaria(plantilla_id=None, titulo="Ad-hoc 2", area="Lobby", fecha=fecha))
        await db.commit()

        # Dos tareas con misma (plantilla_id, fecha) violan uq_tarea_diaria_plantilla_fecha
        db.add(TareaDiaria(plantilla_id=plantilla.id, titulo="Duplicada", area="Sótano", fecha=fecha))
        with pytest.raises(IntegrityError):
            await db.commit()
        await db.rollback()

    await engine.dispose()

    # Carrera simulada en commit() devuelve 0 tras rollback limpio
    mock_session = AsyncMock()
    res_p = MagicMock()
    res_p.scalars.return_value.all.return_value = [
        PlantillaTarea(id=9, condominio_id=1, titulo="Ronda", area="Garita", activa=True)
    ]
    res_t = MagicMock()
    res_t.scalars.return_value.all.return_value = []
    mock_session.execute.side_effect = [res_p, res_t]
    mock_session.add = MagicMock()
    mock_session.commit.side_effect = IntegrityError("INSERT", {}, Exception("unique"))
    assert await generar_tareas_diarias_desde_plantillas(mock_session, fecha_objetivo=fecha) == 0
    mock_session.rollback.assert_awaited_once()


async def test_enviar_correo_smtp_y_reintentos_dlq(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="destinatarios"):
        enviar_correo_smtp({"destinatarios": []}, WorkerSettings())

    # Modo deshabilitado ejecuta no-op seguro
    enviar_correo_smtp(
        {"destinatarios": ["residente@condominio.test"], "asunto": "Hola\r\nBcc:evil", "cuerpo": "OK"},
        WorkerSettings(smtp_enabled=False),
    )

    enviados: list[dict[str, Any]] = []

    class _FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int = 10) -> None:
            enviados.append({"host": host, "port": port, "timeout": timeout, "tls": False, "login": None})

        def __enter__(self) -> _FakeSMTP:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def starttls(self, context: object | None = None) -> None:
            assert context is not None
            enviados[-1]["tls"] = True

        def login(self, user: str, password: str) -> None:
            enviados[-1]["login"] = (user, password)

        def send_message(self, msg: Any) -> None:
            enviados[-1]["subject"] = msg["Subject"]
            enviados[-1]["to"] = msg["To"]

    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)
    cfg_smtp = WorkerSettings(
        smtp_enabled=True,
        smtp_host="smtp.condominio.local",
        smtp_port=587,
        smtp_user="notifier",
        smtp_password="smtp-test-value",
        smtp_use_tls=True,
        max_retries=2,
    )
    enviar_correo_smtp(
        {"destinatarios": ["a@test.com"], "asunto": "Alerta\nInyectada", "cuerpo": "Cuerpo"},
        cfg_smtp,
    )
    assert len(enviados) == 1
    assert enviados[0]["tls"] is True
    assert enviados[0]["subject"] == "Alerta Inyectada"

    fake_redis = AsyncMock()
    assert await procesar_mensaje_notificacion("{json-invalido", fake_redis, cfg_smtp) is False
    assert fake_redis.rpush.await_args_list[-1].args[0] == "queue:notifications:dlq"

    def _boom_smtp(*args: object, **kwargs: object) -> None:
        raise OSError("Conexión SMTP rechazada")

    monkeypatch.setattr(smtplib, "SMTP", _boom_smtp)
    payload_0 = json.dumps({"destinatarios": ["b@test.com"], "asunto": "Prueba", "cuerpo": "Msg", "intentos": 0})
    assert await procesar_mensaje_notificacion(payload_0, fake_redis, cfg_smtp) is False
    cola_1, cuerpo_1 = fake_redis.rpush.await_args_list[-1].args
    assert cola_1 == "queue:notifications"
    assert json.loads(cuerpo_1)["intentos"] == 1

    payload_max = json.dumps({"destinatarios": ["b@test.com"], "asunto": "Prueba", "cuerpo": "Msg", "intentos": 1})
    assert await procesar_mensaje_notificacion(payload_max, fake_redis, cfg_smtp) is False
    cola_dlq, cuerpo_dlq = fake_redis.rpush.await_args_list[-1].args
    assert cola_dlq == "queue:notifications:dlq"
    assert json.loads(cuerpo_dlq)["intentos"] == 2


async def test_qa_health_01_arranque_productivo_sin_mocks_y_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "worker_prod.db"
    hb_path = tmp_path / "worker_heartbeat"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    class _FakeRedisEmpty:
        async def blmove(
            self, src: str, dst: str, timeout: int = 1, src_dir: str = "LEFT", dst_dir: str = "RIGHT"
        ) -> None:
            del src, dst, timeout, src_dir, dst_dir
            await asyncio.sleep(0)
            return None

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", secrets.token_hex(32))
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("WORKER_HEARTBEAT_PATH", str(hb_path))
    monkeypatch.setenv("WORKER_MEDIA_ENABLED", "false")
    monkeypatch.setenv("WORKER_POLL_SECONDS", "0.01")

    assert verify_worker_heartbeat(hb_path) is False
    assert main(["--check-health"]) == 1
    with pytest.raises(SystemExit) as exc_help:
        main(["--help"])
    assert exc_help.value.code == 0

    settings = WorkerSettings.from_env()
    assert settings.media_enabled is False

    # Arranque real sin mockear _loop_media_opcional: media_avif_consumer termina limpio (OPTIONAL_WORKERS)
    exit_code = await run_worker_orchestrator(
        settings,
        max_ticks=3,
        session_factory=session_factory,
        redis_getter=lambda: _FakeRedisEmpty(),
    )
    assert exit_code == 0
    assert hb_path.exists()
    assert verify_worker_heartbeat(hb_path) is True
    assert main(["--check-health"]) == 0

    # Latido expirado falla verificación de salud
    stale_ts = hb_path.stat().st_mtime - 200.0
    os.utime(hb_path, (stale_ts, stale_ts))
    assert verify_worker_heartbeat(hb_path, max_age_seconds=90.0) is False
    assert main(["--check-health"]) == 1

    await engine.dispose()


def test_worker_cli_once_ejecuta_asyncio_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hb_path = tmp_path / "worker_cli_once_hb"
    fake_engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'cli_once.db'}")
    fake_factory = async_sessionmaker(fake_engine, class_=AsyncSession, expire_on_commit=False)

    async def _init_db() -> None:
        async with fake_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init_db())

    class _FakeRedisSyncCli:
        async def blmove(
            self, src: str, dst: str, timeout: int = 1, src_dir: str = "LEFT", dst_dir: str = "RIGHT"
        ) -> None:
            del src, dst, timeout, src_dir, dst_dir
            await asyncio.sleep(0)
            return None

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", secrets.token_hex(32))
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'cli_once.db'}")
    monkeypatch.setenv("WORKER_HEARTBEAT_PATH", str(hb_path))
    monkeypatch.setenv("WORKER_MEDIA_ENABLED", "false")
    monkeypatch.setenv("WORKER_POLL_SECONDS", "0.01")
    monkeypatch.setattr(worker_mod, "AsyncSessionLocal", fake_factory)
    monkeypatch.setattr(worker_mod, "get_redis_client", lambda: _FakeRedisSyncCli())

    assert main(["--once"]) == 0
    assert hb_path.exists()
    asyncio.run(fake_engine.dispose())


async def test_supervisor_detecta_salida_o_excepcion_de_tarea_obligatoria(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _ok_once() -> None:
        return None

    async def _fail_once() -> None:
        raise RuntimeError("Fallo crítico simulado")

    async def _never_ending() -> None:
        await asyncio.sleep(10)

    optional_ok = asyncio.create_task(_ok_once(), name="media_avif_consumer")
    mandatory_ok = asyncio.create_task(_never_ending(), name="notifications_consumer")
    await asyncio.sleep(0)
    assert is_supervisor_healthy({"media_avif_consumer": optional_ok, "notifications_consumer": mandatory_ok}) is True

    mandatory_exited = asyncio.create_task(_ok_once(), name="daily_tasks_scheduler")
    await asyncio.sleep(0)
    assert is_supervisor_healthy({"daily_tasks_scheduler": mandatory_exited}) is False

    optional_crashed = asyncio.create_task(_fail_once(), name="media_avif_consumer")
    await asyncio.sleep(0)
    assert is_supervisor_healthy({"media_avif_consumer": optional_crashed}) is False

    mandatory_ok.cancel()
    with pytest.raises(asyncio.CancelledError):
        await mandatory_ok
    assert is_supervisor_healthy({"notifications_consumer": mandatory_ok}) is False

    # Orquestador real devuelve 1 y borra el heartbeat si una tarea obligatoria muere con excepción no manejada
    hb_path = tmp_path / "hb_crash"
    write_worker_heartbeat(hb_path)
    assert hb_path.exists()

    async def _fatal_loop(*args: object, **kwargs: object) -> None:
        raise ZeroDivisionError("Crash no manejado")

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(worker_mod, "_loop_notificaciones", _fatal_loop)
    monkeypatch.setattr(worker_mod, "_loop_scheduler_diario", lambda s, ev, sf: _never_ending())

    rc = await run_worker_orchestrator(
        WorkerSettings(heartbeat_path=hb_path, poll_seconds=0.01),
        max_ticks=2,
        session_factory=lambda: AsyncMock(),
        redis_getter=lambda: AsyncMock(),
    )
    assert rc == 1
    assert not hb_path.exists()


async def test_consumidor_notificaciones_y_media_opcional(monkeypatch: pytest.MonkeyPatch) -> None:
    stop_notif = asyncio.Event()
    llamadas = {"notif": 0, "media": 0}
    payload = json.dumps({"destinatarios": ["ok@test.com"], "asunto": "Aviso", "cuerpo": "Todo bien"}).encode("utf-8")

    class _RedisNotif:
        def __init__(self) -> None:
            self.lrem_calls = 0

        async def blmove(
            self, src: str, dst: str, timeout: int = 1, src_dir: str = "LEFT", dst_dir: str = "RIGHT"
        ) -> bytes | None:
            del src, dst, timeout, src_dir, dst_dir
            llamadas["notif"] += 1
            if llamadas["notif"] == 1:
                raise RuntimeError("KeyDB reconectando")
            stop_notif.set()
            return payload

        async def lrem(self, queue: str, count: int, item: object) -> int:
            del queue, count, item
            self.lrem_calls += 1
            return 1

    redis_notif = _RedisNotif()
    monkeypatch.setenv("APP_ENV", "development")
    cfg = WorkerSettings(smtp_enabled=False, poll_seconds=0.01, media_enabled=True)
    await worker_mod._loop_notificaciones(cfg, stop_notif, lambda: redis_notif)
    assert llamadas["notif"] == 2
    assert redis_notif.lrem_calls == 1

    stop_media = asyncio.Event()

    class _RedisMedia:
        async def blmove(
            self, src: str, dst: str, timeout: int = 1, src_dir: str = "LEFT", dst_dir: str = "RIGHT"
        ) -> None:
            del src, dst, timeout, src_dir, dst_dir
            llamadas["media"] += 1
            if llamadas["media"] == 1:
                raise RuntimeError("Cola media ocupada")
            stop_media.set()
            return None

    await worker_mod._loop_media_opcional(cfg, stop_media, lambda: _RedisMedia())
    assert llamadas["media"] == 2


def test_worker_settings_minio_use_ssl_y_normalizacion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MINIO_ENDPOINT", "minio:9000")
    monkeypatch.setenv("MINIO_USE_SSL", "true")
    cfg_ssl = WorkerSettings.from_env()
    assert cfg_ssl.minio_use_ssl is True
    assert cfg_ssl.minio_endpoint == "https://minio:9000"

    monkeypatch.setenv("MINIO_ENDPOINT", "http://minio:9000/")
    cfg_upgrade = WorkerSettings.from_env()
    assert cfg_upgrade.minio_endpoint == "https://minio:9000"

    monkeypatch.setenv("MINIO_USE_SSL", "false")
    monkeypatch.setenv("MINIO_ENDPOINT", "minio:9000")
    cfg_plain = WorkerSettings.from_env()
    assert cfg_plain.minio_use_ssl is False
    assert cfg_plain.minio_endpoint == "http://minio:9000"

    monkeypatch.setenv("MINIO_ROOT_USER", "minio_qa_user")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "minio_qa_secret_123")
    capturado: dict[str, str] = {}

    def _tls_handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = str(request.url)
        return httpx.Response(200)

    png_bytes = _crear_png_bytes()
    with httpx.Client(transport=httpx.MockTransport(_tls_handler)) as client:
        uri = convertir_y_subir_avif(
            png_bytes,
            "incidencias/tls",
            minio_endpoint="minio.internal:9000",
            minio_use_ssl=True,
            http_client=client,
        )
    assert uri.startswith("s3://")
    assert capturado["url"].startswith("https://minio.internal:9000/")
    assert worker_mod._normalize_minio_endpoint("https://minio.local:9000", True) == "https://minio.local:9000"
    assert worker_mod._normalize_minio_endpoint("s3://bucket-local", True) == "s3://bucket-local"
    assert worker_mod._normalize_minio_endpoint("", True) == ""


def test_worker_constants_and_settings_defaults_and_from_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert DEFAULT_HEARTBEAT_PATH == Path(tempfile.gettempdir()) / "worker_heartbeat"
    assert OPTIONAL_WORKERS == frozenset({"media_avif_consumer"})
    assert MAX_DLQ_ITEMS == 1000
    assert scheduler_mod.MAX_DLQ_ITEMS == 1000
    assert scheduler_mod._NOTIFICATIONS_QUEUE == "queue:notifications"
    assert scheduler_mod._NOTIFICATIONS_PROCESSING == "queue:notifications:processing"
    assert scheduler_mod._NOTIFICATIONS_DLQ == "queue:notifications:dlq"
    assert scheduler_mod._MEDIA_QUEUE == "queue:media:avif"
    assert scheduler_mod._MEDIA_PROCESSING == "queue:media:avif:processing"
    assert scheduler_mod._MEDIA_DLQ == "queue:media:avif:dlq"

    monkeypatch.delenv("TEST_ENV_FLOAT", raising=False)
    monkeypatch.delenv("TEST_ENV_INT", raising=False)
    monkeypatch.delenv("TEST_ENV_FLAG", raising=False)
    assert worker_mod._env_float("TEST_ENV_FLOAT", 2.5) == 2.5
    assert worker_mod._env_int("TEST_ENV_INT", 17) == 17
    assert env_flag("TEST_ENV_FLAG", True) is True
    assert env_flag("TEST_ENV_FLAG", False) is False

    monkeypatch.setenv("TEST_ENV_FLOAT", "   ")
    monkeypatch.setenv("TEST_ENV_INT", "   ")
    monkeypatch.setenv("TEST_ENV_FLAG", "   ")
    assert worker_mod._env_float("TEST_ENV_FLOAT", 2.5) == 2.5
    assert worker_mod._env_int("TEST_ENV_INT", 17) == 17
    assert env_flag("TEST_ENV_FLAG", True) is False

    monkeypatch.setenv("TEST_ENV_FLOAT", " 3.75 ")
    monkeypatch.setenv("TEST_ENV_INT", " 42 ")
    assert worker_mod._env_float("TEST_ENV_FLOAT", 1.0) == 3.75
    assert worker_mod._env_int("TEST_ENV_INT", 1) == 42

    for truthy in ("1", "true", " TRUE ", "Yes", "on"):
        monkeypatch.setenv("TEST_ENV_FLAG", truthy)
        assert env_flag("TEST_ENV_FLAG", False) is True
    for falsy in ("0", "false", "no", "off", "other"):
        monkeypatch.setenv("TEST_ENV_FLAG", falsy)
        assert env_flag("TEST_ENV_FLAG", True) is False

    cfg_default = WorkerSettings()
    assert cfg_default.heartbeat_path == DEFAULT_HEARTBEAT_PATH
    assert cfg_default.poll_seconds == 1.0
    assert cfg_default.blpop_timeout_seconds == 1
    assert cfg_default.scheduler_interval_seconds == 300.0
    assert cfg_default.max_heartbeat_age_seconds == 90.0
    assert cfg_default.media_enabled is False
    assert cfg_default.smtp_enabled is False
    assert cfg_default.smtp_host == ""
    assert cfg_default.smtp_port == 587
    assert cfg_default.smtp_user == ""
    assert cfg_default.smtp_password == ""
    assert cfg_default.smtp_from == "no-responder@condominio.local"
    assert cfg_default.smtp_use_tls is True
    assert cfg_default.max_retries == 3
    assert cfg_default.minio_endpoint == ""
    assert cfg_default.minio_use_ssl is False
    with pytest.raises(FrozenInstanceError):
        setattr(cfg_default, "poll_seconds", 9.0)

    env_keys = (
        "WORKER_HEARTBEAT_PATH",
        "WORKER_POLL_SECONDS",
        "WORKER_BLPOP_TIMEOUT_SECONDS",
        "WORKER_SCHEDULER_INTERVAL_SECONDS",
        "WORKER_HEARTBEAT_MAX_AGE_SECONDS",
        "WORKER_MEDIA_ENABLED",
        "SMTP_ENABLED",
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "SMTP_FROM",
        "SMTP_USE_TLS",
        "WORKER_MAX_RETRIES",
        "MINIO_ENDPOINT",
        "MINIO_USE_SSL",
    )
    for key in env_keys:
        monkeypatch.delenv(key, raising=False)

    cfg_empty = WorkerSettings.from_env()
    assert cfg_empty == cfg_default

    custom_hb = tmp_path / "custom_hb"
    monkeypatch.setenv("WORKER_HEARTBEAT_PATH", f"  {custom_hb}  ")
    monkeypatch.setenv("WORKER_POLL_SECONDS", "2.25")
    monkeypatch.setenv("WORKER_BLPOP_TIMEOUT_SECONDS", "0")
    monkeypatch.setenv("WORKER_SCHEDULER_INTERVAL_SECONDS", "120.5")
    monkeypatch.setenv("WORKER_HEARTBEAT_MAX_AGE_SECONDS", "45.5")
    monkeypatch.setenv("WORKER_MEDIA_ENABLED", "yes")
    monkeypatch.setenv("SMTP_ENABLED", "on")
    monkeypatch.setenv("SMTP_HOST", " mail.condo.local ")
    monkeypatch.setenv("SMTP_PORT", "2525")
    monkeypatch.setenv("SMTP_USER", " usr_smtp ")
    monkeypatch.setenv("SMTP_PASSWORD", "  pass_space  ")
    monkeypatch.setenv("SMTP_FROM", " aviso@condo.test ")
    monkeypatch.setenv("SMTP_USE_TLS", "false")
    monkeypatch.setenv("WORKER_MAX_RETRIES", "-2")
    monkeypatch.setenv("MINIO_ENDPOINT", "minio.local:9000")
    monkeypatch.setenv("MINIO_USE_SSL", "1")

    cfg_clamped = WorkerSettings.from_env()
    assert cfg_clamped.heartbeat_path == custom_hb
    assert cfg_clamped.poll_seconds == 2.25
    assert cfg_clamped.blpop_timeout_seconds == 1
    assert cfg_clamped.scheduler_interval_seconds == 120.5
    assert cfg_clamped.max_heartbeat_age_seconds == 45.5
    assert cfg_clamped.media_enabled is True
    assert cfg_clamped.smtp_enabled is True
    assert cfg_clamped.smtp_host == "mail.condo.local"
    assert cfg_clamped.smtp_port == 2525
    assert cfg_clamped.smtp_user == "usr_smtp"
    assert cfg_clamped.smtp_password == "  pass_space  "
    assert cfg_clamped.smtp_from == "aviso@condo.test"
    assert cfg_clamped.smtp_use_tls is False
    assert cfg_clamped.max_retries == 1
    assert cfg_clamped.minio_endpoint == "https://minio.local:9000"
    assert cfg_clamped.minio_use_ssl is True

    monkeypatch.setenv("WORKER_BLPOP_TIMEOUT_SECONDS", "7")
    monkeypatch.setenv("WORKER_MAX_RETRIES", "5")
    cfg_custom = WorkerSettings.from_env()
    assert cfg_custom.blpop_timeout_seconds == 7
    assert cfg_custom.max_retries == 5


async def test_worker_scheduler_queues_dlq_and_json_decode(caplog: pytest.LogCaptureFixture) -> None:
    assert decodificar_json_objeto("{bad") is None
    assert decodificar_json_objeto("[1, 2]") is None
    assert decodificar_json_objeto("123") is None
    assert decodificar_json_objeto('"texto"') is None
    assert decodificar_json_objeto("null") is None
    assert decodificar_json_objeto('{"ok": true, "n": 2}') == {"ok": True, "n": 2}

    with pytest.raises(ValueError, match=r"^Debe especificar al menos un destinatario\.$"):
        await encolar_notificacion_correo([], "Asunto", "Cuerpo")

    ev_none = await encolar_notificacion_correo(["a@test.com"], "Hola", "Mundo", redis_client=None)
    assert ev_none == {
        "tipo": "EMAIL_NOTIFICATION",
        "destinatarios": ["a@test.com"],
        "asunto": "Hola",
        "cuerpo": "Mundo",
    }

    ev_no_rpush = await encolar_notificacion_correo(["b@test.com"], "S", "B", redis_client=object())
    assert ev_no_rpush["destinatarios"] == ["b@test.com"]

    redis_ok = AsyncMock()
    ev_queued = await encolar_notificacion_correo(["c@test.com"], "Aviso", "Detalle", redis_client=redis_ok)
    redis_ok.rpush.assert_awaited_once()
    q_name, q_payload = redis_ok.rpush.await_args.args
    assert q_name == "queue:notifications"
    assert json.loads(q_payload) == ev_queued

    with caplog.at_level(logging.WARNING, logger="src.worker_scheduler"):
        for exc in (RedisError("redis caído"), OSError("socket cerrado")):
            redis_err = AsyncMock()
            redis_err.rpush.side_effect = exc
            ev_fallback = await encolar_notificacion_correo(["d@test.com"], "Err", "Msg", redis_client=redis_err)
            assert ev_fallback["tipo"] == "EMAIL_NOTIFICATION"
    assert caplog.text.count("No se pudo encolar notificación en KeyDB") == 2

    redis_media = AsyncMock()
    media_ev = await encolar_tarea_media(redis_media, b"img-bin", "incidencias/2026", "image/png", "foto.png")
    assert media_ev == {
        "tipo": "MEDIA_UPLOAD",
        "prefijo": "incidencias/2026",
        "mime_origen": "image/png",
        "objeto_key": "foto.png",
        "content_base64": base64.b64encode(b"img-bin").decode("ascii"),
        "intentos": 0,
    }
    redis_media.rpush.assert_awaited_once()
    m_queue, m_payload = redis_media.rpush.await_args.args
    assert m_queue == "queue:media:avif"
    assert json.loads(m_payload) == media_ev

    redis_dlq = AsyncMock()
    await enviar_a_dlq_acotado(redis_dlq, "queue:custom:dlq", '{"id": 1}')
    redis_dlq.rpush.assert_awaited_once_with("queue:custom:dlq", '{"id": 1}')
    redis_dlq.ltrim.assert_awaited_once_with("queue:custom:dlq", -1000, -1)

    await enviar_a_dlq_acotado(object(), "queue:custom:dlq", "noop")

    class _OnlyRpush:
        def __init__(self) -> None:
            self.items: list[tuple[str, str]] = []

        async def rpush(self, queue: str, payload: str) -> int:
            self.items.append((queue, payload))
            return 1

    only_rpush = _OnlyRpush()
    await enviar_a_dlq_acotado(only_rpush, "queue:only:dlq", "p1")
    assert only_rpush.items == [("queue:only:dlq", "p1")]

    redis_retry = AsyncMock()
    await reencolar_o_dlq(redis_retry, {"k": "v"}, "error temporal", max_retries=2)
    redis_retry.rpush.assert_awaited_once()
    rq_name, rq_raw = redis_retry.rpush.await_args.args
    assert rq_name == "queue:notifications"
    assert json.loads(rq_raw) == {"k": "v", "intentos": 1, "ultimo_error": "error temporal"}
    redis_retry.ltrim.assert_not_awaited()

    redis_retry.reset_mock()
    await reencolar_o_dlq(redis_retry, {"k": "v", "intentos": 1}, "error final", max_retries=2)
    redis_retry.rpush.assert_awaited_once()
    dlq_name, dlq_raw = redis_retry.rpush.await_args.args
    assert dlq_name == "queue:notifications:dlq"
    assert json.loads(dlq_raw) == {"k": "v", "intentos": 2, "ultimo_error": "error final"}
    redis_retry.ltrim.assert_awaited_once_with("queue:notifications:dlq", -1000, -1)

    redis_custom = AsyncMock()
    await reencolar_o_dlq(
        redis_custom,
        {"intentos": 1},
        "err-media",
        max_retries=3,
        queue="queue:media:avif",
        dlq_queue="queue:media:avif:dlq",
    )
    cq_name, cq_raw = redis_custom.rpush.await_args.args
    assert cq_name == "queue:media:avif"
    assert json.loads(cq_raw)["intentos"] == 2
    redis_custom.ltrim.assert_not_awaited()

    await reencolar_o_dlq(object(), {"intentos": 0}, "sin-rpush", max_retries=3)


async def test_worker_scheduler_consumir_cola_tick_contract() -> None:
    blmove_calls: list[tuple[str, str, int, str, str]] = []
    lrem_calls: list[tuple[str, int, Any]] = []
    processed: list[str] = []

    class _FakeQueueRedis:
        def __init__(self, item: Any) -> None:
            self._item = item

        async def blmove(
            self,
            src: str,
            dst: str,
            timeout: int,
            src_dir: str,
            dst_dir: str,
        ) -> Any:
            blmove_calls.append((src, dst, timeout, src_dir, dst_dir))
            return self._item

        async def lrem(self, queue: str, count: int, item: Any) -> int:
            lrem_calls.append((queue, count, item))
            return 1

    async def _ok_processor(payload: str) -> bool:
        processed.append(payload)
        return True

    await consumir_cola_tick(_FakeQueueRedis(None), ("q:src", "q:proc"), 4, _ok_processor)
    assert blmove_calls == [("q:src", "q:proc", 4, "LEFT", "RIGHT")]
    assert processed == []
    assert lrem_calls == []

    raw_bytes = '{"msg": "café"}'.encode("utf-8")
    await consumir_cola_tick(_FakeQueueRedis(raw_bytes), ("q:src", "q:proc"), 5, _ok_processor)
    assert processed == ['{"msg": "café"}']
    assert lrem_calls == [("q:proc", 1, raw_bytes)]

    processed.clear()
    lrem_calls.clear()
    raw_str = '{"msg": "texto"}'
    await consumir_cola_tick(_FakeQueueRedis(raw_str), ("q:src", "q:proc"), 6, _ok_processor)
    assert processed == ['{"msg": "texto"}']
    assert lrem_calls == [("q:proc", 1, raw_str)]

    lrem_calls.clear()

    async def _fail_processor(payload: str) -> bool:
        del payload
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await consumir_cola_tick(_FakeQueueRedis(raw_bytes), ("q:src", "q:proc"), 3, _fail_processor)
    assert lrem_calls == [("q:proc", 1, raw_bytes)]

    class _RedisNoLrem:
        async def blmove(self, src: str, dst: str, timeout: int, src_dir: str, dst_dir: str) -> bytes:
            del src, dst, timeout, src_dir, dst_dir
            return b"ok"

    processed.clear()
    await consumir_cola_tick(_RedisNoLrem(), ("q:src", "q:proc"), 2, _ok_processor)
    assert processed == ["ok"]


def test_worker_scheduler_frecuencias_y_mapeo_plantillas() -> None:
    assert debe_generar_por_frecuencia(" unica ", date(2026, 11, 10), set()) is True
    assert debe_generar_por_frecuencia("UNICA", date(2026, 11, 10), {date(2026, 1, 1)}) is False

    # Semanal: misma semana ISO -> False (mata slice [:3]); semana previa mismo año -> True (mata slice [:1])
    assert debe_generar_por_frecuencia(" semanal ", date(2026, 11, 11), {date(2026, 11, 9)}) is False
    assert debe_generar_por_frecuencia("SEMANAL", date(2026, 11, 9), {date(2026, 11, 2)}) is True
    assert debe_generar_por_frecuencia("SEMANAL", date(2026, 11, 11), {date(2026, 11, 2), date(2026, 11, 9)}) is False
    assert debe_generar_por_frecuencia("SEMANAL", date(2026, 1, 1), {date(2025, 12, 29)}) is False

    # Mensual: mismo año/mes -> False; mes previo -> True; mismo mes año distinto -> True
    assert debe_generar_por_frecuencia(" Mensual ", date(2026, 11, 20), {date(2026, 11, 1)}) is False
    assert debe_generar_por_frecuencia("MENSUAL", date(2026, 11, 20), {date(2026, 10, 20)}) is True
    assert debe_generar_por_frecuencia("MENSUAL", date(2026, 11, 20), {date(2025, 11, 20)}) is True
    assert debe_generar_por_frecuencia("MENSUAL", date(2026, 11, 20), {date(2026, 10, 1), date(2026, 11, 5)}) is False

    # Diaria / cadena vacía / desconocida
    assert debe_generar_por_frecuencia("DIARIA", date(2026, 11, 20), {date(2026, 11, 19)}) is True
    assert debe_generar_por_frecuencia("DIARIA", date(2026, 11, 20), {date(2026, 11, 20)}) is False
    assert debe_generar_por_frecuencia("", date(2026, 11, 20), {date(2026, 11, 20)}) is False
    assert debe_generar_por_frecuencia("OTRA", date(2026, 11, 20), {date(2026, 11, 19)}) is True

    fallback = date(2026, 11, 15)
    tareas_previas = [
        TareaDiaria(plantilla_id=None, titulo="Ad-hoc", area="Lobby", fecha=date(2026, 11, 1)),
        TareaDiaria(plantilla_id=3, titulo="A", area="X", fecha=date(2026, 11, 1)),
        TareaDiaria(plantilla_id=3, titulo="A", area="X", fecha=date(2026, 11, 2)),
        TareaDiaria(plantilla_id=4, titulo="B", area="Y"),
    ]
    mapeado = scheduler_mod._mapear_fechas_previas(tareas_previas, fallback)
    assert mapeado == {3: {date(2026, 11, 1), date(2026, 11, 2)}, 4: {fallback}}

    agregadas: list[TareaDiaria] = []
    mock_db: Any = MagicMock()
    mock_db.add = agregadas.append

    plantillas = [
        PlantillaTarea(id=10, condominio_id=7, titulo="T1", area="A1", activa=True),
        PlantillaTarea(id=11, condominio_id=0, titulo="T2", area="A2", frecuencia="SEMANAL", activa=True),
        PlantillaTarea(id=12, condominio_id=1, titulo="T3", area="A3", frecuencia="DIARIA", activa=True),
    ]
    creadas = scheduler_mod._agregar_tareas_desde_plantillas(
        mock_db,
        plantillas,
        {11: {date(2026, 11, 2)}, 12: {date(2026, 11, 11)}},
        date(2026, 11, 11),
    )
    assert creadas == 2
    assert len(agregadas) == 2
    assert agregadas[0].condominio_id == 7
    assert agregadas[0].plantilla_id == 10
    assert agregadas[0].incidencia_id is None
    assert agregadas[0].titulo == "T1"
    assert agregadas[0].area == "A1"
    assert agregadas[0].fecha == date(2026, 11, 11)
    assert agregadas[0].completada is False
    assert agregadas[1].condominio_id == 1
    assert agregadas[1].plantilla_id == 11


async def test_worker_scheduler_db_frecuencias_tenant_y_limites_fecha(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_file = tmp_path / "scheduler_frecuencias.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    fecha_base = date(2026, 11, 9)  # Lunes
    async with session_factory() as db:
        assert await generar_tareas_diarias_desde_plantillas(db, fecha_objetivo=fecha_base, condominio_id=1) == 0

        p_inactiva = PlantillaTarea(
            condominio_id=1, titulo="Inactiva", area="Azotea", frecuencia="DIARIA", activa=False
        )
        p_unica = PlantillaTarea(condominio_id=1, titulo="Unica", area="Cisterna", frecuencia="UNICA", activa=True)
        p_semanal = PlantillaTarea(
            condominio_id=1, titulo="Semanal", area="Ascensor", frecuencia="SEMANAL", activa=True
        )
        p_mensual = PlantillaTarea(condominio_id=1, titulo="Mensual", area="Tablero", frecuencia="MENSUAL", activa=True)
        p_condo2 = PlantillaTarea(condominio_id=2, titulo="Condo2", area="Garita", frecuencia="DIARIA", activa=True)
        db.add_all([p_inactiva, p_unica, p_semanal, p_mensual, p_condo2])
        await db.commit()
        await db.refresh(p_unica)

        # Tarea futura (> fecha_base) NO debe bloquear generación en fecha_base (mata <= -> > o >=)
        db.add(
            TareaDiaria(
                condominio_id=1,
                plantilla_id=p_unica.id,
                titulo="Unica futura",
                area="Cisterna",
                fecha=fecha_base + timedelta(days=40),
            )
        )
        await db.commit()

        assert await generar_tareas_diarias_desde_plantillas(db, fecha_objetivo=fecha_base, condominio_id=1) == 3
        assert db.sync_session.info["tenant_id"] == "1"

        commit_spy = AsyncMock(wraps=db.commit)
        rollback_spy = AsyncMock(wraps=db.rollback)
        monkeypatch.setattr(db, "commit", commit_spy)
        monkeypatch.setattr(db, "rollback", rollback_spy)

        # Misma fecha (==) no debe intentar reinsertar ni llamar commit/rollback (mata <= -> < y creadas > 0 -> >= 0)
        assert await generar_tareas_diarias_desde_plantillas(db, fecha_objetivo=fecha_base, condominio_id=1) == 0
        commit_spy.assert_not_awaited()
        rollback_spy.assert_not_awaited()

        # Día siguiente (< fecha_objetivo) ve la tarea de fecha_base (mata <= -> ==)
        assert (
            await generar_tareas_diarias_desde_plantillas(
                db, fecha_objetivo=fecha_base + timedelta(days=1), condominio_id=1
            )
            == 0
        )
        commit_spy.assert_not_awaited()

        # Semana siguiente mismo mes: solo SEMANAL genera
        assert (
            await generar_tareas_diarias_desde_plantillas(
                db, fecha_objetivo=fecha_base + timedelta(days=7), condominio_id=1
            )
            == 1
        )
        # Mes siguiente: SEMANAL y MENSUAL generan (UNICA no)
        assert (
            await generar_tareas_diarias_desde_plantillas(
                db, fecha_objetivo=fecha_base + timedelta(days=35), condominio_id=1
            )
            == 2
        )

        # Otro condominio con fecha_objetivo=None usa date.today()
        assert await generar_tareas_diarias_desde_plantillas(db, condominio_id=2) == 1
        assert db.sync_session.info["tenant_id"] == "2"

    await engine.dispose()


async def test_worker_smtp_branches_and_procesar_notificacion_media(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert worker_mod._sanitize_header("  Hola\r\nMundo  ") == "Hola  Mundo"
    assert worker_mod._sanitize_header("X\rY\nZ") == "X Y Z"

    with pytest.raises(ValueError, match=r"^Evento de notificación sin destinatarios válidos\.$"):
        worker_mod._extraer_destinatarios({})
    with pytest.raises(ValueError, match=r"^Evento de notificación sin destinatarios válidos\.$"):
        worker_mod._extraer_destinatarios({"destinatarios": ["", "   "]})
    assert worker_mod._extraer_destinatarios({"destinatarios": ["  a@x.com  ", " ", "b@x.com"]}) == [
        "a@x.com",
        "b@x.com",
    ]

    with caplog.at_level(logging.INFO, logger="src.worker"):
        enviar_correo_smtp(
            {"destinatarios": ["a@x.com"], "asunto": "Hola\r\nSec"},
            WorkerSettings(smtp_enabled=True, smtp_host=""),
        )
    assert "Notificación omitida (SMTP deshabilitado): asunto=Hola  Sec" in caplog.text

    sesiones: list[dict[str, Any]] = []

    class _FakeSMTPExtended:
        def __init__(self, host: str, port: int, timeout: int = 10) -> None:
            sesiones.append(
                {
                    "host": host,
                    "port": port,
                    "timeout": timeout,
                    "tls": False,
                    "login": None,
                    "msg": None,
                }
            )

        def __enter__(self) -> _FakeSMTPExtended:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def starttls(self, context: object | None = None) -> None:
            assert isinstance(context, ssl.SSLContext)
            sesiones[-1]["tls"] = True

        def login(self, user: str, password: str) -> None:
            sesiones[-1]["login"] = (user, password)

        def send_message(self, msg: Any) -> None:
            sesiones[-1]["msg"] = msg

    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTPExtended)
    enviar_correo_smtp(
        {"destinatarios": ["a@x.com", "b@x.com"]},
        WorkerSettings(
            smtp_enabled=True,
            smtp_host="smtp.local",
            smtp_port=2525,
            smtp_user="u",
            smtp_password="",
            smtp_from="from@condo.test",
            smtp_use_tls=False,
        ),
    )
    assert sesiones[-1]["host"] == "smtp.local"
    assert sesiones[-1]["port"] == 2525
    assert sesiones[-1]["timeout"] == 10
    assert sesiones[-1]["tls"] is False
    assert sesiones[-1]["login"] is None
    assert sesiones[-1]["msg"]["From"] == "from@condo.test"
    assert sesiones[-1]["msg"]["To"] == "a@x.com, b@x.com"
    assert sesiones[-1]["msg"]["Subject"] == ""
    assert sesiones[-1]["msg"].get_content().strip() == ""

    enviar_correo_smtp(
        {"destinatarios": ["c@x.com"], "asunto": "Ok", "cuerpo": "Texto"},
        WorkerSettings(
            smtp_enabled=True,
            smtp_host="smtp.local",
            smtp_port=587,
            smtp_user="",
            smtp_password="secret",
            smtp_from=" remitente@condo.test\r\n ",
            smtp_use_tls=True,
        ),
    )
    assert sesiones[-1]["tls"] is True
    assert sesiones[-1]["login"] is None
    assert sesiones[-1]["msg"]["From"] == "remitente@condo.test"
    assert sesiones[-1]["msg"].get_content().strip() == "Texto"

    fake_redis = AsyncMock()
    cfg_notif = WorkerSettings(smtp_enabled=False, max_retries=2)
    assert await procesar_mensaje_notificacion("[1, 2]", fake_redis, cfg_notif) is False
    fake_redis.rpush.assert_awaited_once_with("queue:notifications:dlq", "[1, 2]")
    fake_redis.ltrim.assert_awaited_once_with("queue:notifications:dlq", -1000, -1)

    fake_redis.reset_mock()
    valid_notif = json.dumps({"destinatarios": ["ok@test.com"], "asunto": "Ok", "cuerpo": "Msg"})
    assert await procesar_mensaje_notificacion(valid_notif, fake_redis, cfg_notif) is True
    fake_redis.rpush.assert_not_awaited()

    assert await procesar_mensaje_notificacion(json.dumps({"destinatarios": []}), fake_redis, cfg_notif) is False
    assert fake_redis.rpush.await_args.args[0] == "queue:notifications"

    def _smtp_err(*args: object, **kwargs: object) -> None:
        raise smtplib.SMTPException("smtp error")

    monkeypatch.setattr(smtplib, "SMTP", _smtp_err)
    fake_redis.reset_mock()
    cfg_smtp_on = WorkerSettings(smtp_enabled=True, smtp_host="smtp.local", max_retries=2)
    assert await procesar_mensaje_notificacion(valid_notif, fake_redis, cfg_smtp_on) is False
    q_err, raw_err = fake_redis.rpush.await_args.args
    assert q_err == "queue:notifications"
    assert json.loads(raw_err)["ultimo_error"] == "smtp error"

    # Media processor: inválido, éxito y errores de reintento/DLQ
    fake_redis.reset_mock()
    cfg_media = WorkerSettings(minio_endpoint="https://minio.test:9000", minio_use_ssl=True, max_retries=2)
    assert await procesar_mensaje_media("[1]", fake_redis, cfg_media) is False
    fake_redis.rpush.assert_awaited_once_with("queue:media:avif:dlq", "[1]")
    fake_redis.ltrim.assert_awaited_once_with("queue:media:avif:dlq", -1000, -1)

    subidas: list[tuple[dict[str, Any], str, bool]] = []

    def _fake_upload(evento: dict[str, Any], endpoint: str, use_ssl: bool) -> str:
        subidas.append((evento, endpoint, use_ssl))
        return "s3://bucket/ok.avif"

    monkeypatch.setattr(worker_mod, "ejecutar_subida_media_bytes", _fake_upload)
    fake_redis.reset_mock()
    media_payload = json.dumps({"tipo": "MEDIA_UPLOAD", "objeto_key": "a.avif", "intentos": 0})
    assert await procesar_mensaje_media(media_payload, fake_redis, cfg_media) is True
    assert subidas == [
        ({"tipo": "MEDIA_UPLOAD", "objeto_key": "a.avif", "intentos": 0}, "https://minio.test:9000", True)
    ]
    fake_redis.rpush.assert_not_awaited()

    for exc in (ValueError("v"), OSError("o"), httpx.HTTPError("h"), binascii.Error("b")):

        def _raise_upload(evento: dict[str, Any], endpoint: str, use_ssl: bool, error: Exception = exc) -> str:
            del evento, endpoint, use_ssl
            raise error

        monkeypatch.setattr(worker_mod, "ejecutar_subida_media_bytes", _raise_upload)
        fake_redis.reset_mock()
        assert await procesar_mensaje_media(media_payload, fake_redis, cfg_media) is False
        mq_name, mq_raw = fake_redis.rpush.await_args.args
        assert mq_name == "queue:media:avif"
        assert json.loads(mq_raw)["intentos"] == 1
        fake_redis.ltrim.assert_not_awaited()

    fake_redis.reset_mock()
    media_max = json.dumps({"tipo": "MEDIA_UPLOAD", "objeto_key": "a.avif", "intentos": 1})
    assert await procesar_mensaje_media(media_max, fake_redis, cfg_media) is False
    md_name, md_raw = fake_redis.rpush.await_args.args
    assert md_name == "queue:media:avif:dlq"
    assert json.loads(md_raw)["intentos"] == 2
    fake_redis.ltrim.assert_awaited_once_with("queue:media:avif:dlq", -1000, -1)


async def test_worker_heartbeat_boundaries_and_supervisor_health(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nested_hb = tmp_path / "nested" / "sub" / "hb"
    write_worker_heartbeat(nested_hb)
    assert nested_hb.is_file()
    parsed = datetime.fromisoformat(nested_hb.read_text(encoding="utf-8"))
    assert parsed.tzinfo == UTC
    write_worker_heartbeat(nested_hb)

    dir_hb = tmp_path / "hb_dir"
    dir_hb.mkdir()
    assert verify_worker_heartbeat(dir_hb) is False
    assert verify_worker_heartbeat(tmp_path / "missing_hb") is False

    mtime = nested_hb.stat().st_mtime
    fake_now = mtime
    monkeypatch.setattr(worker_mod.time, "time", lambda: fake_now)

    fake_now = mtime - 0.5
    assert verify_worker_heartbeat(nested_hb) is False
    fake_now = mtime
    assert verify_worker_heartbeat(nested_hb) is True
    fake_now = mtime + 90.0
    assert verify_worker_heartbeat(nested_hb) is True
    fake_now = mtime + 90.5
    assert verify_worker_heartbeat(nested_hb) is False
    fake_now = mtime + 10.0
    assert verify_worker_heartbeat(nested_hb, max_age_seconds=10.0) is True
    fake_now = mtime + 10.1
    assert verify_worker_heartbeat(nested_hb, max_age_seconds=10.0) is False

    async def _done_ok() -> None:
        return None

    async def _pend() -> None:
        await asyncio.sleep(5)

    assert is_supervisor_healthy({}) is True

    opt_cancelled = asyncio.create_task(_pend(), name="media_avif_consumer")
    await asyncio.sleep(0)
    opt_cancelled.cancel()
    with pytest.raises(asyncio.CancelledError):
        await opt_cancelled
    assert is_supervisor_healthy({"media_avif_consumer": opt_cancelled}) is False

    opt_done = asyncio.create_task(_done_ok(), name="media_avif_consumer")
    mand_done = asyncio.create_task(_done_ok(), name="notifications_consumer")
    mand_pend = asyncio.create_task(_pend(), name="daily_tasks_scheduler")
    await asyncio.sleep(0)
    assert is_supervisor_healthy({"media_avif_consumer": opt_done, "daily_tasks_scheduler": mand_pend}) is True
    assert is_supervisor_healthy({"media_avif_consumer": opt_done, "notifications_consumer": mand_done}) is False
    mand_pend.cancel()
    with pytest.raises(asyncio.CancelledError):
        await mand_pend


async def test_worker_loops_backoff_scheduler_recovery_and_ticks(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    ev_timeout = asyncio.Event()
    await worker_mod._esperar_o_detener(ev_timeout, 0.01)
    assert ev_timeout.is_set() is False

    ev_ready = asyncio.Event()
    ev_ready.set()
    await asyncio.wait_for(worker_mod._esperar_o_detener(ev_ready, 10.0), timeout=1.0)

    # _loop_scheduler_diario: recuperación tras SQLAlchemyError + intervalo exacto
    sched_waits: list[float] = []
    sched_sessions: list[object] = []
    sentinel_session = object()

    class _FakeSessionCtx:
        async def __aenter__(self) -> object:
            return sentinel_session

        async def __aexit__(self, *args: object) -> None:
            return None

    stop_sched = asyncio.Event()
    stop_sched.set()
    await worker_mod._loop_scheduler_diario(
        WorkerSettings(scheduler_interval_seconds=123.5),
        stop_sched,
        _FakeSessionCtx,
    )
    assert sched_sessions == []

    stop_sched = asyncio.Event()
    sched_calls = 0

    async def _fake_gen(session: object) -> int:
        nonlocal sched_calls
        sched_sessions.append(session)
        sched_calls += 1
        if sched_calls == 1:
            raise SQLAlchemyError("db transitoria")
        return 1

    async def _fake_wait_sched(ev: asyncio.Event, delay: float) -> None:
        sched_waits.append(delay)
        if sched_calls >= 2:
            ev.set()

    monkeypatch.setattr(worker_mod, "generar_tareas_diarias_desde_plantillas", _fake_gen)
    monkeypatch.setattr(worker_mod, "_esperar_o_detener", _fake_wait_sched)
    with caplog.at_level(logging.WARNING, logger="src.worker"):
        await asyncio.wait_for(
            worker_mod._loop_scheduler_diario(
                WorkerSettings(scheduler_interval_seconds=123.5),
                stop_sched,
                _FakeSessionCtx,
            ),
            timeout=1.5,
        )
    assert sched_sessions == [sentinel_session, sentinel_session]
    assert sched_waits == [123.5, 123.5]
    assert "Error transitorio generando tareas diarias" in caplog.text

    # _consumir_cola_notificaciones_tick y _consumir_cola_media_tick con payload real
    notif_payload = json.dumps({"destinatarios": ["u@test.com"], "asunto": "T", "cuerpo": "C"}).encode("utf-8")
    media_payload = json.dumps({"tipo": "MEDIA_UPLOAD", "objeto_key": "x.avif"}).encode("utf-8")

    class _TickRedis:
        def __init__(self, item: bytes) -> None:
            self.item = item
            self.blmove_args: list[tuple[str, str, int, str, str]] = []
            self.lrem_args: list[tuple[str, int, Any]] = []

        async def blmove(self, src: str, dst: str, timeout: int, src_dir: str, dst_dir: str) -> bytes:
            self.blmove_args.append((src, dst, timeout, src_dir, dst_dir))
            return self.item

        async def lrem(self, queue: str, count: int, item: Any) -> int:
            self.lrem_args.append((queue, count, item))
            return 1

    tick_cfg = WorkerSettings(blpop_timeout_seconds=6, smtp_enabled=False, minio_endpoint="http://m:9000")
    r_notif = _TickRedis(notif_payload)
    await worker_mod._consumir_cola_notificaciones_tick(r_notif, tick_cfg)
    assert r_notif.blmove_args == [("queue:notifications", "queue:notifications:processing", 6, "LEFT", "RIGHT")]
    assert r_notif.lrem_args == [("queue:notifications:processing", 1, notif_payload)]

    media_calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        worker_mod,
        "ejecutar_subida_media_bytes",
        lambda ev, ep, ssl_flag: media_calls.append({"ev": ev, "ep": ep, "ssl": ssl_flag}) or "s3://ok",
    )
    r_media = _TickRedis(media_payload)
    await worker_mod._consumir_cola_media_tick(r_media, tick_cfg)
    assert r_media.blmove_args == [("queue:media:avif", "queue:media:avif:processing", 6, "LEFT", "RIGHT")]
    assert r_media.lrem_args == [("queue:media:avif:processing", 1, media_payload)]
    assert media_calls == [
        {"ev": {"tipo": "MEDIA_UPLOAD", "objeto_key": "x.avif"}, "ep": "http://m:9000", "ssl": False}
    ]

    # _loop_media_opcional deshabilitado no consulta redis_getter
    def _fail_getter() -> Any:
        raise AssertionError("No debe llamarse si media_enabled=False")

    await worker_mod._loop_media_opcional(WorkerSettings(media_enabled=False), asyncio.Event(), _fail_getter)

    # Backoff exponencial exacto (cap 4 y reset fallos=0) para ambos loops + techo 5.0
    seq_outcomes: list[Exception | None] = [
        RedisError("r1"),
        OSError("r2"),
        RuntimeError("r3"),
        RedisError("r4"),
        RedisError("r5"),
        RedisError("r6"),
        None,
        RedisError("r8"),
    ]

    for loop_fn, log_frag in (
        (worker_mod._loop_notificaciones, "Error transitorio en consumidor KeyDB de notificaciones"),
        (worker_mod._loop_media_opcional, "Error transitorio en cola de medios AVIF"),
    ):
        idx = 0
        delays: list[float] = []
        stop_ev = asyncio.Event()

        class _BackoffRedis:
            async def blmove(self, *args: object) -> None:
                nonlocal idx
                del args
                outcome = seq_outcomes[idx]
                idx += 1
                if outcome is not None:
                    raise outcome
                return None

        async def _capture_wait(ev: asyncio.Event, delay: float) -> None:
            delays.append(delay)
            if idx >= len(seq_outcomes):
                ev.set()

        monkeypatch.setattr(worker_mod, "_esperar_o_detener", _capture_wait)
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="src.worker"):
            await asyncio.wait_for(
                loop_fn(WorkerSettings(poll_seconds=0.2, media_enabled=True), stop_ev, lambda: _BackoffRedis()),
                timeout=1.5,
            )
        assert [round(d, 6) for d in delays] == [0.2, 0.4, 0.8, 1.6, 3.2, 3.2, 0.2]
        assert log_frag in caplog.text

        # Verificar techo 5.0s con poll_seconds=1.0
        idx_cap = 0
        delays_cap: list[float] = []
        stop_cap = asyncio.Event()

        class _CapRedis:
            async def blmove(self, *args: object) -> None:
                nonlocal idx_cap
                del args
                idx_cap += 1
                raise RedisError("cap")

        async def _capture_cap(ev: asyncio.Event, delay: float) -> None:
            delays_cap.append(delay)
            if idx_cap >= 4:
                ev.set()

        monkeypatch.setattr(worker_mod, "_esperar_o_detener", _capture_cap)
        await asyncio.wait_for(
            loop_fn(WorkerSettings(poll_seconds=1.0, media_enabled=True), stop_cap, lambda: _CapRedis()),
            timeout=1.5,
        )
        assert delays_cap == [1.0, 2.0, 4.0, 5.0]


async def test_worker_orchestrator_signals_cancel_and_cli_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert worker_mod._alcanzo_max_ticks(0, None) is False
    assert worker_mod._alcanzo_max_ticks(5, None) is False
    assert worker_mod._alcanzo_max_ticks(0, 1) is False
    assert worker_mod._alcanzo_max_ticks(1, 1) is True
    assert worker_mod._alcanzo_max_ticks(2, 1) is True

    async def _ok_task() -> None:
        return None

    async def _err_task() -> None:
        raise ValueError("ignored")

    async def _sleep_task() -> None:
        await asyncio.sleep(10)

    t_ok = asyncio.create_task(_ok_task())
    t_err = asyncio.create_task(_err_task())
    t_sleep = asyncio.create_task(_sleep_task())
    await asyncio.sleep(0)
    await asyncio.wait_for(
        worker_mod._cancelar_tareas({"ok": t_ok, "err": t_err, "sleep": t_sleep}),
        timeout=1.0,
    )
    assert t_ok.done()
    assert t_err.done()
    assert t_sleep.cancelled()

    # Fail-fast en producción con secreto inseguro
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "insegura")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    with pytest.raises(RuntimeError):
        await run_worker_orchestrator(max_ticks=1)

    monkeypatch.setenv("APP_ENV", "development")

    class _FakeSessionCtx:
        async def __aenter__(self) -> AsyncMock:
            return AsyncMock()

        async def __aexit__(self, *args: object) -> None:
            return None

    class _EmptyRedis:
        async def blmove(self, *args: object) -> None:
            del args
            await asyncio.sleep(0)
            return None

    monkeypatch.setattr(worker_mod, "AsyncSessionLocal", _FakeSessionCtx)
    monkeypatch.setattr(worker_mod, "get_redis_client", lambda: _EmptyRedis())
    monkeypatch.setattr(worker_mod, "generar_tareas_diarias_desde_plantillas", AsyncMock(return_value=0))

    # _crear_tareas_supervisor con fallbacks None usa AsyncSessionLocal y get_redis_client
    ev_sup = asyncio.Event()
    created_tasks = worker_mod._crear_tareas_supervisor(
        WorkerSettings(poll_seconds=0.01, media_enabled=False),
        ev_sup,
        None,
        None,
    )
    assert set(created_tasks.keys()) == {"daily_tasks_scheduler", "notifications_consumer", "media_avif_consumer"}
    for t_name, t_obj in created_tasks.items():
        assert t_obj.get_name() == t_name
    ev_sup.set()
    await asyncio.wait_for(worker_mod._cancelar_tareas(created_tasks), timeout=1.0)

    # settings=None usa from_env(), stop_event termina en True y finally cancela todas las tareas
    hb_none = tmp_path / "hb_from_env"
    monkeypatch.setenv("WORKER_HEARTBEAT_PATH", str(hb_none))
    monkeypatch.setenv("WORKER_POLL_SECONDS", "0.01")
    monkeypatch.setenv("WORKER_MEDIA_ENABLED", "false")
    stop_check = asyncio.Event()
    captured_tasks: dict[str, asyncio.Task[None]] = {}
    orig_create = worker_mod._crear_tareas_supervisor

    def _spy_create(
        cfg_arg: WorkerSettings,
        ev_arg: asyncio.Event,
        sf_arg: Any,
        rg_arg: Any,
    ) -> dict[str, asyncio.Task[None]]:
        res = orig_create(cfg_arg, ev_arg, sf_arg, rg_arg)
        captured_tasks.update(res)
        return res

    with monkeypatch.context() as m:
        m.setattr(worker_mod, "_crear_tareas_supervisor", _spy_create)
        rc_none = await asyncio.wait_for(
            run_worker_orchestrator(
                None,
                stop_event=stop_check,
                max_ticks=2,
                session_factory=_FakeSessionCtx,
                redis_getter=lambda: _EmptyRedis(),
            ),
            timeout=2.0,
        )
    assert rc_none == 0
    assert hb_none.is_file()
    assert stop_check.is_set() is True
    assert captured_tasks
    assert all(task.done() for task in captured_tasks.values())

    # stop_event ya activo sale sin escribir heartbeat
    hb_preset = tmp_path / "hb_preset"
    stop_preset = asyncio.Event()
    stop_preset.set()
    rc_preset = await run_worker_orchestrator(
        WorkerSettings(heartbeat_path=hb_preset, poll_seconds=0.01),
        stop_event=stop_preset,
        max_ticks=2,
        session_factory=_FakeSessionCtx,
        redis_getter=lambda: _EmptyRedis(),
    )
    assert rc_preset == 0
    assert not hb_preset.exists()

    # _supervisar_ciclo_worker con max_ticks=2 espera 1 vez entre ticks; unhealthy sin hb previo no falla unlink
    wait_calls: list[float] = []

    async def _spy_wait(ev: asyncio.Event, timeout_seconds: float) -> None:
        del ev
        wait_calls.append(timeout_seconds)

    monkeypatch.setattr(worker_mod, "_esperar_o_detener", _spy_wait)
    t_live = asyncio.create_task(_sleep_task(), name="notifications_consumer")
    hb_cycle = tmp_path / "hb_cycle"
    rc_cycle = await worker_mod._supervisar_ciclo_worker(
        WorkerSettings(heartbeat_path=hb_cycle, poll_seconds=0.25),
        asyncio.Event(),
        {"notifications_consumer": t_live},
        max_ticks=2,
    )
    assert rc_cycle == 0
    assert hb_cycle.is_file()
    assert wait_calls == [0.25]
    t_live.cancel()
    with pytest.raises(asyncio.CancelledError):
        await t_live

    hb_missing = tmp_path / "hb_nonexistent"
    t_dead = asyncio.create_task(_ok_task(), name="notifications_consumer")
    await asyncio.sleep(0)
    with caplog.at_level(logging.ERROR, logger="src.worker"):
        rc_unhealthy = await worker_mod._supervisar_ciclo_worker(
            WorkerSettings(heartbeat_path=hb_missing, poll_seconds=0.01),
            asyncio.Event(),
            {"notifications_consumer": t_dead},
            max_ticks=2,
        )
    assert rc_unhealthy == 1
    assert "Supervisor worker detectó estado no saludable." in caplog.text

    # _run_with_signals registra SIGINT/SIGTERM e ignora NotImplementedError
    loop = asyncio.get_running_loop()
    registered: dict[signal.Signals, Any] = {}

    def _fake_add_signal(sig: signal.Signals, cb: Any) -> None:
        registered[sig] = cb

    async def _fake_orch(
        cfg: WorkerSettings,
        *,
        stop_event: asyncio.Event | None = None,
        max_ticks: int | None = None,
    ) -> int:
        del cfg, max_ticks
        assert stop_event is not None
        assert stop_event.is_set() is False
        registered[signal.SIGINT]()
        assert stop_event.is_set() is True
        return 0

    monkeypatch.setattr(loop, "add_signal_handler", _fake_add_signal)
    monkeypatch.setattr(worker_mod, "run_worker_orchestrator", _fake_orch)
    assert await worker_mod._run_with_signals(WorkerSettings(), max_ticks=1) == 0
    assert set(registered.keys()) == {signal.SIGINT, signal.SIGTERM}

    async def _fake_orch_term(
        cfg: WorkerSettings,
        *,
        stop_event: asyncio.Event | None = None,
        max_ticks: int | None = None,
    ) -> int:
        del cfg, max_ticks
        assert stop_event is not None
        assert stop_event.is_set() is False
        registered[signal.SIGTERM]()
        assert stop_event.is_set() is True
        return 0

    monkeypatch.setattr(worker_mod, "run_worker_orchestrator", _fake_orch_term)
    assert await worker_mod._run_with_signals(WorkerSettings(), max_ticks=1) == 0

    def _no_sig(sig: signal.Signals, cb: Any) -> None:
        del sig, cb
        raise NotImplementedError("unsupported")

    async def _fake_orch_simple(
        cfg: WorkerSettings,
        *,
        stop_event: asyncio.Event | None = None,
        max_ticks: int | None = None,
    ) -> int:
        del cfg, stop_event, max_ticks
        return 0

    monkeypatch.setattr(loop, "add_signal_handler", _no_sig)
    monkeypatch.setattr(worker_mod, "run_worker_orchestrator", _fake_orch_simple)
    assert await worker_mod._run_with_signals(WorkerSettings(), max_ticks=1) == 0


def test_worker_cli_contract_sync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parser = worker_mod._build_cli_parser()
    assert parser.prog == "python -m src.worker"
    args_empty = parser.parse_args([])
    assert args_empty.check_health is False
    assert args_empty.once is False
    args_health = parser.parse_args(["--check-health"])
    assert args_health.check_health is True
    assert args_health.once is False
    args_once = parser.parse_args(["--once"])
    assert args_once.check_health is False
    assert args_once.once is True

    cli_calls: list[tuple[WorkerSettings, int | None]] = []

    async def _spy_run_with_signals(cfg: WorkerSettings, max_ticks: int | None) -> int:
        cli_calls.append((cfg, max_ticks))
        return 0

    monkeypatch.setattr(worker_mod, "_run_with_signals", _spy_run_with_signals)
    monkeypatch.setenv("APP_ENV", "development")
    assert main([]) == 0
    assert main(["--once"]) == 0
    assert [mt for _, mt in cli_calls] == [None, 1]
    assert cli_calls[0][0] == WorkerSettings.from_env()

    hb_cli = tmp_path / "hb_cli_age"
    write_worker_heartbeat(hb_cli)
    mtime_cli = hb_cli.stat().st_mtime
    monkeypatch.setattr(worker_mod.time, "time", lambda: mtime_cli + 10.0)
    monkeypatch.setenv("WORKER_HEARTBEAT_PATH", str(hb_cli))
    monkeypatch.setenv("WORKER_HEARTBEAT_MAX_AGE_SECONDS", "5.0")
    assert main(["--check-health"]) == 1
    monkeypatch.setenv("WORKER_HEARTBEAT_MAX_AGE_SECONDS", "20.0")
    assert main(["--check-health"]) == 0
