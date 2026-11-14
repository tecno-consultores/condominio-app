"""Pruebas unitarias e integración Nivel 11X para el Hito 18 (Worker real AVIF/MinIO, KeyDB/SMTP y QA-HEALTH-01)."""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import smtplib
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from PIL import Image
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src import worker as worker_mod
from src.database import Base
from src.models import PlantillaTarea, TareaDiaria
from src.worker import (
    WorkerSettings,
    codificar_imagen_avif,
    convertir_y_subir_avif,
    enviar_correo_smtp,
    generar_tareas_diarias_desde_plantillas,
    is_supervisor_healthy,
    main,
    procesar_mensaje_notificacion,
    run_worker_orchestrator,
    subir_objeto_minio_s3,
    verify_worker_heartbeat,
    write_worker_heartbeat,
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
        async def blpop(self, key: str, timeout: int = 1) -> None:
            del key, timeout
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
        async def blpop(self, key: str, timeout: int = 1) -> None:
            del key, timeout
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
        async def blpop(self, key: str, timeout: int = 1) -> tuple[str, bytes] | None:
            del key, timeout
            llamadas["notif"] += 1
            if llamadas["notif"] == 1:
                raise RuntimeError("KeyDB reconectando")
            stop_notif.set()
            return ("queue:notifications", payload)

    monkeypatch.setenv("APP_ENV", "development")
    cfg = WorkerSettings(smtp_enabled=False, poll_seconds=0.01, media_enabled=True)
    await worker_mod._loop_notificaciones(cfg, stop_notif, lambda: _RedisNotif())
    assert llamadas["notif"] == 2

    stop_media = asyncio.Event()

    class _RedisMedia:
        async def blpop(self, key: str, timeout: int = 1) -> None:
            del key, timeout
            llamadas["media"] += 1
            if llamadas["media"] == 1:
                raise RuntimeError("Cola media ocupada")
            stop_media.set()
            return None

    await worker_mod._loop_media_opcional(cfg, stop_media, lambda: _RedisMedia())
    assert llamadas["media"] == 2
