"""Pruebas Nivel 11X del Hito 21: Exactitud Contable LPH, Idempotencia con Replay y Worker Productivo."""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import hmac
import importlib.util
import json
import logging
import os
import secrets
import signal
import smtplib
import ssl
import tempfile
import time
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError
from redis.exceptions import RedisError
from sqlalchemy import event, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database import Base, get_db
from src.dependencies import get_current_user
from src.facturacion_lph import (
    calcular_cargos_modalidad,
    cargar_contexto_facturacion,
    persistir_lote_facturacion,
    verificar_periodo_facturable,
)
from src.finanzas import (
    ErrorFinanciero,
    aplicar_pago,
    calcular_excedente_pago,
    construir_token_pase_qr,
    convertir_a_usd,
    evaluar_escrutinio_consulta,
    generar_firma_pase_qr,
)
from src.main import app
from src.models import (
    AreaSocial,
    AuditoriaRecibo,
    ContratoOcupacion,
    Estructura,
    FondoCondominio,
    PagoReportado,
    PaseVisita,
    PlantillaTarea,
    Recibo,
    ReciboItem,
    TareaDiaria,
    TasaCambio,
    Unidad,
    Usuario,
)
from src.redis_client import (
    IdempotencyResponsePayload,
    acquire_idempotency_slot,
    build_scoped_idempotency_key,
    get_redis_client,
    release_idempotency_slot,
    reset_local_security_state,
    store_idempotency_response,
)
from src.redis_idempotency import MAX_LOCAL_SECURITY_ENTRIES, _local_idempotency_records
from src.schemas import (
    CierreMensualRequest,
    EgresoCreate,
    FacturarPeriodoRequest,
    ReciboCreate,
    TasaCambioCreate,
    UsuarioCreate,
)
from src import worker as worker_mod
from src import worker_media as worker_media_mod
from src.security import get_password_hash, get_qr_signing_key
from src.worker import (
    _MEDIA_DLQ,
    _MEDIA_PROCESSING,
    _MEDIA_QUEUE,
    _NOTIFICATIONS_DLQ,
    _NOTIFICATIONS_PROCESSING,
    _NOTIFICATIONS_QUEUE,
    DEFAULT_HEARTBEAT_PATH,
    MAX_DLQ_ITEMS,
    MAX_IMAGE_PIXELS,
    OPTIONAL_WORKERS,
    WorkerSettings,
    __all__ as worker_exports,
    _alcanzo_max_ticks,
    _build_cli_parser,
    _build_sigv4_headers,
    _cancelar_tareas,
    _consumir_cola_media_tick,
    _consumir_cola_notificaciones_tick,
    _crear_tareas_supervisor,
    _esperar_o_detener,
    _loop_media_opcional,
    _loop_notificaciones,
    _loop_scheduler_diario,
    _run_with_signals,
    _supervisar_ciclo_worker,
    codificar_imagen_avif,
    construir_clave_evidencia,
    convertir_y_subir_avif,
    ejecutar_subida_media_bytes,
    encolar_tarea_media,
    env_flag,
    enviar_correo_smtp,
    generar_tareas_diarias_desde_plantillas,
    is_supervisor_healthy,
    main,
    normalize_minio_endpoint,
    procesar_mensaje_media,
    procesar_mensaje_notificacion,
    resolver_bucket_minio,
    run_worker_orchestrator,
    subir_objeto_minio_s3,
    verify_worker_heartbeat,
    write_worker_heartbeat,
)
from src.worker_media import (
    _aplicar_esquema_http,
    _construir_destino_s3,
    _decodificar_payload_media,
    _ejecutar_put_http,
    _encode_sigv4_query,
    _encode_sigv4_uri,
    _env_bucket_name,
    _hmac_sha256,
    _resolver_minio_credenciales,
    _signing_key_sigv4,
    _str_campo,
    _subir_pdf_directo,
)


class _FakeStatefulRedis:
    """Implementación en memoria de operaciones KeyDB reales (SET NX, BLMOVE, LREM, LTRIM)."""

    def __init__(self) -> None:
        self.kv: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}
        self.fail_on: set[str] = set()

    def _check(self, op: str) -> None:
        if op in self.fail_on:
            raise RedisError(f"Error simulado en {op}")

    async def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None) -> bool:
        del ex
        self._check("set")
        if nx and key in self.kv:
            return False
        self.kv[key] = value
        return True

    async def get(self, key: str) -> str | None:
        self._check("get")
        return self.kv.get(key)

    async def delete(self, *keys: str) -> int:
        self._check("delete")
        borradas = 0
        for key in keys:
            if key in self.kv:
                del self.kv[key]
                borradas += 1
        return borradas

    async def rpush(self, key: str, *values: str) -> int:
        self._check("rpush")
        bucket = self.lists.setdefault(key, [])
        bucket.extend(str(v) for v in values)
        return len(bucket)

    async def blmove(
        self,
        src: str,
        dst: str,
        timeout: int,
        src_dir: str,
        dst_dir: str,
    ) -> str | None:
        del timeout, src_dir, dst_dir
        self._check("blmove")
        origen = self.lists.get(src, [])
        if not origen:
            return None
        item = origen.pop(0)
        self.lists.setdefault(dst, []).append(item)
        return item

    async def lrem(self, key: str, count: int, value: str) -> int:
        del count
        self._check("lrem")
        bucket = self.lists.get(key, [])
        try:
            bucket.remove(value)
            return 1
        except ValueError:
            return 0

    async def ltrim(self, key: str, start: int, stop: int) -> bool:
        self._check("ltrim")
        bucket = self.lists.get(key, [])
        if not bucket:
            return True
        if start < 0 and stop == -1:
            self.lists[key] = bucket[start:]
        else:
            self.lists[key] = bucket[start : stop + 1]
        return True


def _png_bytes(width: int = 8, height: int = 8) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), color=(15, 110, 210)).save(buf, format="PNG")
    return buf.getvalue()


async def _crear_sqlite_fk(tmp_path: Path) -> tuple[Any, async_sessionmaker[AsyncSession]]:
    db_path = tmp_path / "hito21.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_fk(dbapi_conn: Any, _rec: Any) -> None:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, factory


async def _sembrar_escenario_condo(factory: async_sessionmaker[AsyncSession]) -> dict[str, int]:
    async with factory() as s:
        torre = Estructura(nombre="Torre H21", tipo="TORRE")
        s.add(torre)
        await s.flush()

        u1 = Unidad(identificador="21-A", estructura_id=torre.id, alicuota=Decimal("60.0000"))
        u2 = Unidad(identificador="21-B", estructura_id=torre.id, alicuota=Decimal("40.0000"))
        s.add_all([u1, u2])
        await s.flush()

        pw = get_password_hash("ClaveHito21#123")
        tesorero = Usuario(
            nombre="Tesorero H21",
            cedula="V-21000001",
            correo="tesorero.h21@test.com",
            telefono="+584140002101",
            password_hash=pw,
            es_activo=True,
            rol="TESORERO",
        )
        prop1 = Usuario(
            nombre="Propietario H21",
            cedula="V-21000002",
            correo="prop1.h21@test.com",
            telefono="+584140002102",
            password_hash=pw,
            es_activo=True,
            rol="PROPIETARIO",
        )
        pres = Usuario(
            nombre="Presidente H21",
            cedula="V-21000003",
            correo="pres.h21@test.com",
            telefono="+584140002103",
            password_hash=pw,
            es_activo=True,
            rol="PRESIDENTE",
        )
        conserje = Usuario(
            nombre="Conserje H21",
            cedula="V-21000004",
            correo="conserje.h21@test.com",
            telefono="+584140002104",
            password_hash=pw,
            es_activo=True,
            rol="CONSERJE",
        )
        s.add_all([tesorero, prop1, pres, conserje])
        await s.flush()

        s.add_all(
            [
                ContratoOcupacion(usuario_id=prop1.id, unidad_id=u1.id, tipo_ocupante="PROPIETARIO", es_activo=True),
                ContratoOcupacion(usuario_id=tesorero.id, unidad_id=u2.id, tipo_ocupante="PROPIETARIO", es_activo=True),
            ]
        )
        tasa = TasaCambio(fecha=date.today(), tasa_usd_ves=Decimal("40.0000"))
        area = AreaSocial(
            nombre="Salón H21",
            aforo_maximo=40,
            costo_uso_usd=Decimal("30.00"),
            deposito_garantia_usd=Decimal("50.00"),
            requiere_solvencia_estricta=True,
            es_activa=True,
        )
        s.add_all([tasa, area])
        await s.commit()
        return {
            "u1": u1.id,
            "u2": u2.id,
            "tesorero": tesorero.id,
            "prop1": prop1.id,
            "pres": pres.id,
            "conserje": conserje.id,
            "area": area.id,
        }


# ==============================================================================
# 1. Exactitud Matemática, Validación de Esquemas y Quórum LPH
# ==============================================================================


def test_finanzas_montos_no_positivos_micro_ves_y_quorum_estricto() -> None:
    with pytest.raises(ErrorFinanciero, match="mayor que cero"):
        convertir_a_usd(Decimal("0.00"), "USD", Decimal("36.00"))
    with pytest.raises(ErrorFinanciero, match="mayor que cero"):
        convertir_a_usd(Decimal("0.01"), "VES", Decimal("100.00"))
    with pytest.raises(ErrorFinanciero, match="negativos"):
        aplicar_pago(Decimal("10.00"), Decimal("-0.01"), Decimal("5.00"))
    with pytest.raises(ErrorFinanciero, match="mayor que cero"):
        calcular_excedente_pago(Decimal("10.00"), Decimal("0.00"), Decimal("0.00"))

    # Quórum MAYORIA_SIMPLE exige estrictamente > 50.0000%
    empate = evaluar_escrutinio_consulta(
        Decimal("50.0000"),
        {1},
        {1: Decimal("50.0000")},
        regla_quorum="MAYORIA_SIMPLE",
    )
    assert empate[0] == "CERRADA_SIN_QUORUM"

    mitad_exacta = evaluar_escrutinio_consulta(
        Decimal("50.0000"),
        {1},
        {1: Decimal("50.0000"), 2: Decimal("30.0000")},
        regla_quorum="MAYORIA_SIMPLE",
    )
    assert mitad_exacta[0] == "CERRADA_RECHAZADA"

    mayoria_minima = evaluar_escrutinio_consulta(
        Decimal("50.0000"),
        {1},
        {1: Decimal("50.0001"), 2: Decimal("30.0000")},
        regla_quorum="MAYORIA_SIMPLE",
    )
    assert mayoria_minima[0] == "CERRADA_APROBADA"


def test_schemas_rechazan_nan_inf_desbordamiento_y_meses_invalidos() -> None:
    with pytest.raises(ValidationError):
        TasaCambioCreate(tasa_usd_ves=Decimal("NaN"))
    with pytest.raises(ValidationError):
        ReciboCreate(unidad_id=1, periodo="2026-10", monto_usd=Decimal("Infinity"))
    with pytest.raises(ValidationError):
        ReciboCreate(unidad_id=1, periodo="2026-10", monto_usd=Decimal("10000000000.00"))
    for bad_periodo in ("2026-00", "2026-13"):
        with pytest.raises(ValidationError):
            ReciboCreate(unidad_id=1, periodo=bad_periodo, monto_usd=Decimal("10.00"))
        with pytest.raises(ValidationError):
            CierreMensualRequest(periodo=bad_periodo)
        with pytest.raises(ValidationError):
            EgresoCreate(
                periodo=bad_periodo,
                categoria="MANTENIMIENTO",
                descripcion="Reparación válida bomba",
                monto=Decimal("10.00"),
                moneda="USD",
                es_gasto_comun=True,
            )

    u_exact = UsuarioCreate.model_validate(
        {
            "nombre": "Residente Exacto",
            "cedula": "V-57000001",
            "correo": "exacto57@test.com",
            "telefono": "+584145550057",
            "password": "Password123!",
            "unidad_solicitada_id": 57.0,
            "tipo_ocupante_solicitado": "PROPIETARIO",
        }
    )
    assert u_exact.unidad_solicitada_id == 57
    assert isinstance(u_exact.unidad_solicitada_id, int)
    assert UsuarioCreate.model_json_schema()["properties"]["unidad_solicitada_id"]["minimum"] == 1
    for bad_uid in (57.5, True, "57", 0):
        with pytest.raises(ValidationError):
            UsuarioCreate.model_validate(
                {
                    "nombre": "Residente Malo",
                    "cedula": "V-57000002",
                    "correo": "malo57@test.com",
                    "telefono": "+584145550058",
                    "password": "Password123!",
                    "unidad_solicitada_id": bad_uid,
                    "tipo_ocupante_solicitado": "PROPIETARIO",
                }
            )


# ==============================================================================
# 2. LPH: UPSERT Área Social <-> Facturación, Créditos, Fondos y Cierre con Pagos
# ==============================================================================


@pytest.mark.asyncio
async def test_lph_upsert_reservas_credito_fondos_y_cierre_bloqueado(tmp_path: Path) -> None:
    engine, factory = await _crear_sqlite_fk(tmp_path)
    ids = await _sembrar_escenario_condo(factory)
    mock_redis = _FakeStatefulRedis()
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

    async def _override_db() -> AsyncIterator[AsyncSession]:
        async with factory() as s:
            yield s

    app.dependency_overrides[get_db] = _override_db

    try:
        async with factory() as s:
            tesorero = await s.get(Usuario, ids["tesorero"])
            prop1 = await s.get(Usuario, ids["prop1"])
            assert tesorero is not None and prop1 is not None

        periodo_reserva = (date.today() + timedelta(days=5)).strftime("%Y-%m")
        fecha_ev = (date.today() + timedelta(days=5)).isoformat()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Residente reserva área social pagada -> genera Recibo preliminar con USO_AREA_SOCIAL
            app.dependency_overrides[get_current_user] = lambda: prop1
            r_res = await client.post(
                "/api/reservas/solicitar",
                headers={"Idempotency-Key": "res-uso-001"},
                json={
                    "area_id": ids["area"],
                    "unidad_id": ids["u1"],
                    "fecha_evento": fecha_ev,
                    "motivo_evento": "Grado",
                },
            )
            assert r_res.status_code == 201
            reserva_id = r_res.json()["id"]

            # 2. Facturar el mismo periodo sin crear Fondo -> 400 porque incluir_fondo_reserva=True
            app.dependency_overrides[get_current_user] = lambda: tesorero
            r_no_fondo = await client.post(
                "/api/finanzas/facturar-periodo",
                headers={"Idempotency-Key": "fact-sin-fondo-01"},
                json={"periodo": periodo_reserva, "modalidad": "ALICUOTA", "incluir_fondo_reserva": True},
            )
            assert r_no_fondo.status_code == 400

            # Crea fondo de reserva legal e intenta egreso patrimonial sin saldo -> 400
            r_fondo = await client.post(
                "/api/finanzas/fondos",
                headers={"Idempotency-Key": "crear-fondo-h21"},
                json={"nombre": "Fondo Legal H21", "tipo": "RESERVA_LEGAL", "porcentaje_recargo": "10.00"},
            )
            assert r_fondo.status_code == 201

            r_egr_fail = await client.post(
                "/api/finanzas/egresos",
                headers={"Idempotency-Key": "egreso-sin-saldo"},
                json={
                    "periodo": periodo_reserva,
                    "categoria": "FONDO",
                    "descripcion": "Uso reserva sin saldo",
                    "monto": "25.00",
                    "moneda": "USD",
                    "es_gasto_comun": False,
                },
            )
            assert r_egr_fail.status_code == 400

            # Egreso común $100.00 + facturar-periodo hace UPSERT sobre el recibo preliminar de u1
            r_egr_com = await client.post(
                "/api/finanzas/egresos",
                headers={"Idempotency-Key": "egreso-comun-100"},
                json={
                    "periodo": periodo_reserva,
                    "categoria": "MANTENIMIENTO",
                    "descripcion": "Mantenimiento mensual ascensor",
                    "monto": "100.00",
                    "moneda": "USD",
                    "es_gasto_comun": True,
                },
            )
            assert r_egr_com.status_code == 201

            r_fact = await client.post(
                "/api/finanzas/facturar-periodo",
                headers={"Idempotency-Key": "fact-upsert-h21"},
                json={"periodo": periodo_reserva, "modalidad": "ALICUOTA", "incluir_fondo_reserva": True},
            )
            assert r_fact.status_code == 201

            # Refacturar el mismo periodo ahora sí bloquea con 409 porque ya tiene GASTO_COMUN
            r_fact_dup = await client.post(
                "/api/finanzas/facturar-periodo",
                headers={"Idempotency-Key": "fact-upsert-dup"},
                json={"periodo": periodo_reserva, "modalidad": "ALICUOTA", "incluir_fondo_reserva": True},
            )
            assert r_fact_dup.status_code == 409

            # Egreso patrimonial contra fondo ya fondeado (+10.00) -> 201 y descuenta saldo
            r_egr_pat = await client.post(
                "/api/finanzas/egresos",
                headers={"Idempotency-Key": "egreso-fondo-ok"},
                json={
                    "periodo": periodo_reserva,
                    "categoria": "FONDO",
                    "descripcion": "Compra repuesto desde reserva",
                    "monto": "4.00",
                    "moneda": "USD",
                    "es_gasto_comun": False,
                },
            )
            assert r_egr_pat.status_code == 201
            r_fondos_get = await client.get("/api/finanzas/fondos?limit=1&offset=0")
            assert r_fondos_get.status_code == 200
            assert Decimal(r_fondos_get.json()[0]["saldo_actual_usd"]) == Decimal("6.00")

            # Verifica fusión contable: u1 sum(ReciboItem) == Recibo.monto_usd
            async with factory() as s:
                rec_u1 = (
                    (
                        await s.execute(
                            select(Recibo).where(Recibo.unidad_id == ids["u1"], Recibo.periodo == periodo_reserva)
                        )
                    )
                    .scalars()
                    .first()
                )
                assert rec_u1 is not None
                items_u1 = (
                    (await s.execute(select(ReciboItem).where(ReciboItem.recibo_id == rec_u1.id))).scalars().all()
                )
                assert any(it.tipo_item == "USO_AREA_SOCIAL" for it in items_u1)
                assert any(it.tipo_item == "GASTO_COMUN" for it in items_u1)
                assert sum((it.monto_usd for it in items_u1), Decimal("0.00")) == rec_u1.monto_usd

            # Cancela reserva con cargo de uso -> revierte item USO_AREA_SOCIAL en recibo abierto y registra auditoría
            app.dependency_overrides[get_current_user] = lambda: prop1
            r_cancel = await client.put(
                f"/api/reservas/{reserva_id}/cancelar", headers={"Idempotency-Key": "cancelar-h21-01"}
            )
            assert r_cancel.status_code == 200

            # Reporta pago EN_REVISION -> cierre mensual DEBE bloquearse con 409
            r_pago = await client.post(
                "/api/pagos/reportar",
                headers={"Idempotency-Key": "pago-rev-01"},
                json={
                    "recibo_id": rec_u1.id,
                    "monto": "66.00",
                    "moneda": "USD",
                    "metodo_pago": "ZELLE",
                    "numero_referencia": "REF-H21-001",
                },
            )
            assert r_pago.status_code == 201
            pago_id = r_pago.json()["id"]

            app.dependency_overrides[get_current_user] = lambda: tesorero
            r_cierre_block = await client.post(
                "/api/finanzas/cierre-mensual",
                headers={"Idempotency-Key": "cierre-blq-01"},
                json={"periodo": periodo_reserva},
            )
            assert r_cierre_block.status_code == 409
            assert "revisión" in r_cierre_block.json()["detail"].lower()

            # Aprueba pago y valida cierre exitoso + AuditoriaRecibo
            r_aprob = await client.put(f"/api/pagos/{pago_id}/aprobar", headers={"Idempotency-Key": "aprob-01"})
            assert r_aprob.status_code == 200

            r_cierre_ok = await client.post(
                "/api/finanzas/cierre-mensual",
                headers={"Idempotency-Key": "cierre-ok-01"},
                json={"periodo": periodo_reserva},
            )
            assert r_cierre_ok.status_code == 200

            # Crédito excedente cubriendo 100% de factura siguiente (sum(items) == 0.00)
            sig_mes = (date.today() + timedelta(days=36)).strftime("%Y-%m")
            async with factory() as s:
                u1_db = await s.get(Unidad, ids["u1"])
                assert u1_db is not None
                u1_db.credito_disponible_usd = Decimal("500.00")
                await s.commit()

            r_fact_cred = await client.post(
                "/api/finanzas/facturar-periodo",
                headers={"Idempotency-Key": "fact-cred-100"},
                json={"periodo": sig_mes, "modalidad": "PARTES_IGUALES", "incluir_fondo_reserva": False},
            )
            assert r_fact_cred.status_code == 201
            async with factory() as s:
                rec_cred = (
                    (await s.execute(select(Recibo).where(Recibo.unidad_id == ids["u1"], Recibo.periodo == sig_mes)))
                    .scalars()
                    .first()
                )
                assert rec_cred is not None
                assert rec_cred.monto_usd == Decimal("0.00")
                assert rec_cred.estado == "PAGADO"
                items_cred = (
                    (await s.execute(select(ReciboItem).where(ReciboItem.recibo_id == rec_cred.id))).scalars().all()
                )
                assert sum((it.monto_usd for it in items_cred), Decimal("0.00")) == Decimal("0.00")
                auds = (await s.execute(select(AuditoriaRecibo))).scalars().all()
                assert any(a.pago_id == pago_id for a in auds)
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_facturacion_lph_errores_y_cancelacion_con_credito(tmp_path: Path) -> None:
    reset_local_security_state()
    u = Unidad(id=1, identificador="X-1", estructura_id=1, alicuota=Decimal("100.0000"), credito_disponible_usd=None)
    # Cuota fija sin Fondo de Reserva Legal cuando hay excedente != 0 -> ErrorFinanciero
    with pytest.raises(ErrorFinanciero, match="Fondo de Reserva Legal"):
        await persistir_lote_facturacion(
            _FakeAsyncSession(),  # type: ignore[arg-type]
            [u],
            "2026-10",
            "CUOTA_FIJA",
            {1: [("CUOTA_FIJA", "Fija", Decimal("20.00"))]},
            None,
            Decimal("0.00"),
            Decimal("5.00"),
        )

    fondo_bajo = FondoCondominio(
        id=1, nombre="F", tipo="RESERVA_LEGAL", porcentaje_recargo=Decimal("10.00"), saldo_actual_usd=Decimal("1.00")
    )
    with pytest.raises(ErrorFinanciero, match="excede el saldo"):
        await persistir_lote_facturacion(
            _FakeAsyncSession(),  # type: ignore[arg-type]
            [u],
            "2026-10",
            "CUOTA_FIJA",
            {1: [("CUOTA_FIJA", "Fija", Decimal("20.00"))]},
            fondo_bajo,
            Decimal("0.00"),
            Decimal("-2.00"),
        )

    # Verifica calcular_cargos_modalidad / cargar_contexto_facturacion con credito_disponible_usd=0.00 explícito
    u.credito_disponible_usd = Decimal("0.00")
    req = FacturarPeriodoRequest(periodo="2026-10", modalidad="ALICUOTA", incluir_fondo_reserva=False)
    items, _ = calcular_cargos_modalidad(req, [u], Decimal("50.00"), Decimal("0.00"))
    assert items[1][0][2] == Decimal("50.00")

    # Cancelación sobre recibo bloqueado en SQLite acreditando credito_disponible_usd
    engine, factory = await _crear_sqlite_fk(tmp_path)
    ids = await _sembrar_escenario_condo(factory)
    app.dependency_overrides[get_redis_client] = lambda: _FakeStatefulRedis()

    async def _override_db() -> AsyncIterator[AsyncSession]:
        async with factory() as s:
            yield s

    app.dependency_overrides[get_db] = _override_db
    try:
        async with factory() as s:
            prop1 = await s.get(Usuario, ids["prop1"])
            assert prop1 is not None
        fecha_ev = (date.today() + timedelta(days=9)).isoformat()
        periodo = (date.today() + timedelta(days=9)).strftime("%Y-%m")
        app.dependency_overrides[get_current_user] = lambda: prop1
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(
                "/api/reservas/solicitar",
                headers={"Idempotency-Key": "res-blq-cred-01"},
                json={
                    "area_id": ids["area"],
                    "unidad_id": ids["u1"],
                    "fecha_evento": fecha_ev,
                    "motivo_evento": "Reunión bloqueada prueba",
                },
            )
            assert r.status_code == 201
            reserva_id = r.json()["id"]

            async with factory() as s:
                rec = (
                    (await s.execute(select(Recibo).where(Recibo.unidad_id == ids["u1"], Recibo.periodo == periodo)))
                    .scalars()
                    .first()
                )
                assert rec is not None
                rec.bloqueado = True
                await s.commit()

            r_canc = await client.put(f"/api/reservas/{reserva_id}/cancelar", headers={"Idempotency-Key": "canc-blq-1"})
            assert r_canc.status_code == 200
            async with factory() as s:
                u1_db = await s.get(Unidad, ids["u1"])
                assert u1_db is not None
                assert u1_db.credito_disponible_usd == Decimal("30.00")
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


class _FakeScalarResult:
    def all(self) -> list[Any]:
        return []

    def first(self) -> Any:
        return None


class _FakeExecResult:
    def scalars(self) -> _FakeScalarResult:
        return _FakeScalarResult()


class _FakeAsyncSession:
    def add(self, obj: Any) -> None:
        if isinstance(obj, Recibo) and obj.id is None:
            obj.id = 1

    async def execute(self, stmt: Any) -> _FakeExecResult:
        del stmt
        return _FakeExecResult()

    async def flush(self) -> None:
        return None


# ==============================================================================
# 3. Idempotencia HTTP Replay, Loopback /health, Evidencias, Consultas y QR
# ==============================================================================


@pytest.mark.asyncio
async def test_idempotencia_replay_http_y_liberacion_en_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_local_security_state()
    monkeypatch.setenv("APP_ENV", "development")

    # Pruebas unitarias directas de redis_idempotency (scoped key, LRU, TTL, producción 503)
    scoped = build_scoped_idempotency_key(7, 42, "egreso", "abc-123")
    assert scoped == "idemp:7:42:egreso:abc-123"

    r_cli = _FakeStatefulRedis()
    slot1 = await acquire_idempotency_slot(r_cli, scoped, "hash-a")  # type: ignore[arg-type]
    assert slot1.acquired is True
    in_flight = await acquire_idempotency_slot(r_cli, scoped, "hash-a")  # type: ignore[arg-type]
    assert not in_flight.acquired and "curso" in (in_flight.conflict_detail or "")
    mismatch = await acquire_idempotency_slot(r_cli, scoped, "hash-b")  # type: ignore[arg-type]
    assert not mismatch.acquired and "distinto" in (mismatch.conflict_detail or "")

    await store_idempotency_response(
        r_cli,
        scoped,
        IdempotencyResponsePayload(payload_hash="hash-a", status_code=201, body={"ok": True}),  # type: ignore[arg-type]
    )
    replay = await acquire_idempotency_slot(r_cli, scoped, "hash-a")  # type: ignore[arg-type]
    assert replay.replay_status == 201 and replay.replay_body == {"ok": True}
    await release_idempotency_slot(r_cli, scoped)  # type: ignore[arg-type]

    # Fallback local en dev y cota LRU + fail-closed en prod
    for i in range(MAX_LOCAL_SECURITY_ENTRIES + 5):
        await store_idempotency_response(
            None, f"idemp:1:1:k:{i}", IdempotencyResponsePayload(payload_hash="h", status_code=200, body={})
        )
    assert len(_local_idempotency_records) <= MAX_LOCAL_SECURITY_ENTRIES
    await release_idempotency_slot(None, "idemp:1:1:k:0")

    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(Exception):
        await acquire_idempotency_slot(None, "idemp:prod", "h")
    monkeypatch.setenv("APP_ENV", "development")

    # Ciclo HTTP real: 201 -> replay 201 con X-Idempotency-Replayed: true -> error 4xx libera y permite reintento
    engine, factory = await _crear_sqlite_fk(tmp_path)
    ids = await _sembrar_escenario_condo(factory)
    app.dependency_overrides[get_redis_client] = lambda: r_cli

    async def _override_db() -> AsyncIterator[AsyncSession]:
        async with factory() as s:
            yield s

    app.dependency_overrides[get_db] = _override_db
    try:
        async with factory() as s:
            tesorero = await s.get(Usuario, ids["tesorero"])
            assert tesorero is not None
        app.dependency_overrides[get_current_user] = lambda: tesorero

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload_tasa = {"tasa_usd_ves": "42.5000"}
            res1 = await client.post(
                "/api/finanzas/tasa",
                headers={"Idempotency-Key": "tasa-replay-01"},
                json=payload_tasa,
            )
            assert res1.status_code == 201
            assert "x-idempotency-replayed" not in res1.headers

            res2 = await client.post(
                "/api/finanzas/tasa",
                headers={"Idempotency-Key": "tasa-replay-01"},
                json=payload_tasa,
            )
            assert res2.status_code == 201
            assert res2.headers.get("X-Idempotency-Replayed") == "true"
            assert res2.json() == res1.json()

            res_diff = await client.post(
                "/api/finanzas/tasa",
                headers={"Idempotency-Key": "tasa-replay-01"},
                json={"tasa_usd_ves": "43.0000"},
            )
            assert res_diff.status_code == 409

            # Falla 400 (fondo inexistente) libera la clave para poder reintentar después
            res_err = await client.post(
                "/api/finanzas/egresos",
                headers={"Idempotency-Key": "egreso-retry-key"},
                json={
                    "periodo": "2026-10",
                    "categoria": "FONDO",
                    "descripcion": "Intento sin fondo",
                    "monto": "10.00",
                    "moneda": "USD",
                    "es_gasto_comun": False,
                },
            )
            assert res_err.status_code == 400

            res_retry = await client.post(
                "/api/finanzas/egresos",
                headers={"Idempotency-Key": "egreso-retry-key"},
                json={
                    "periodo": "2026-10",
                    "categoria": "MANTENIMIENTO",
                    "descripcion": "Intento corregido común",
                    "monto": "10.00",
                    "moneda": "USD",
                    "es_gasto_comun": True,
                },
            )
            assert res_retry.status_code == 201

            # Registro sobre unidad inexistente -> 404; offset fuera de cota -> 422
            res_reg_404 = await client.post(
                "/api/auth/register",
                headers={"Idempotency-Key": "reg-unidad-404"},
                json={
                    "nombre": "Residente 404",
                    "cedula": "V-40404040",
                    "correo": "reg404@test.com",
                    "telefono": "+584140000404",
                    "password": "Password123!",
                    "unidad_solicitada_id": 99999,
                    "tipo_ocupante_solicitado": "PROPIETARIO",
                },
            )
            assert res_reg_404.status_code == 404

            res_off_422 = await client.get("/api/estructura/unidades?limit=100&offset=1000001")
            assert res_off_422.status_code == 422

            # /health loopback permitido incluso cuando ALLOWED_HOSTS es restrictivo
            monkeypatch.setenv("ALLOWED_HOSTS", "condominio.example.com")
            res_health = await client.get("/health", headers={"Host": "127.0.0.1:8000"})
            assert res_health.status_code == 200
            res_evil = await client.get("/health", headers={"Host": "atacante.example.com"})
            assert res_evil.status_code == 400
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_subir_evidencia_segura_y_consultas_qr_temporales(tmp_path: Path) -> None:
    engine, factory = await _crear_sqlite_fk(tmp_path)
    ids = await _sembrar_escenario_condo(factory)
    r_cli = _FakeStatefulRedis()
    app.dependency_overrides[get_redis_client] = lambda: r_cli

    async def _override_db() -> AsyncIterator[AsyncSession]:
        async with factory() as s:
            yield s

    app.dependency_overrides[get_db] = _override_db
    try:
        async with factory() as s:
            pres = await s.get(Usuario, ids["pres"])
            conserje = await s.get(Usuario, ids["conserje"])
            assert pres is not None and conserje is not None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            app.dependency_overrides[get_current_user] = lambda: pres

            # 1. Evidencias PNG (octet-stream) y PDF (multipart) -> 202 ENCOLADO
            png = _png_bytes()
            r_png = await client.post(
                "/api/evidencias/subir?categoria=comprobantes",
                headers={"Idempotency-Key": "evid-png-01", "Content-Type": "application/octet-stream"},
                content=png,
            )
            assert r_png.status_code == 202
            assert r_png.json()["formato_destino"] == "image/avif"
            assert len(r_cli.lists[_MEDIA_QUEUE]) == 1

            pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
            r_pdf = await client.post(
                "/api/evidencias/subir?categoria=incidencias",
                headers={"Idempotency-Key": "evid-pdf-01"},
                files={"archivo": ("doc.pdf", pdf, "application/pdf")},
            )
            assert r_pdf.status_code == 202
            assert r_pdf.json()["formato_destino"] == "application/pdf"

            # Ejecutable EXE -> 415, PNG truncado -> 415, >2MB -> 413, KeyDB caída -> 503
            r_exe = await client.post(
                "/api/evidencias/subir",
                headers={"Idempotency-Key": "evid-exe-01", "Content-Type": "application/octet-stream"},
                content=b"MZ" + b"\x00" * 32,
            )
            assert r_exe.status_code == 415

            r_bad_png = await client.post(
                "/api/evidencias/subir",
                headers={"Idempotency-Key": "evid-corrupt-01", "Content-Type": "application/octet-stream"},
                content=b"\x89PNG\r\n\x1a\n" + b"basura-truncada",
            )
            assert r_bad_png.status_code == 415

            r_big = await client.post(
                "/api/evidencias/subir",
                headers={"Idempotency-Key": "evid-big-01", "Content-Type": "application/octet-stream"},
                content=b"\x89PNG\r\n\x1a\n" + (b"A" * ((2 * 1024 * 1024) + 10)),
            )
            assert r_big.status_code == 413

            r_cli.fail_on.add("rpush")
            r_503 = await client.post(
                "/api/evidencias/subir",
                headers={"Idempotency-Key": "evid-503-01", "Content-Type": "application/octet-stream"},
                content=png,
            )
            assert r_503.status_code == 503
            r_cli.fail_on.clear()

            # Multipart inválido o sin campo binario -> 400
            r_no_multi = await client.post(
                "/api/evidencias/subir",
                headers={
                    "Idempotency-Key": "evid-nomulti-01",
                    "Content-Type": "multipart/form-data; boundary=abc",
                },
                content=b"texto plano sin partes",
            )
            assert r_no_multi.status_code == 400

            r_no_file = await client.post(
                "/api/evidencias/subir",
                headers={
                    "Idempotency-Key": "evid-nofile-01",
                    "Content-Type": "multipart/form-data; boundary=B1",
                },
                content=b'--B1\r\nContent-Disposition: form-data; name="nota"\r\n\r\nhola\r\n--B1--\r\n',
            )
            assert r_no_file.status_code == 400

            # 2. Consultas: fecha_cierre <= ahora -> 400; cerrar prematura -> 409; votar antes de apertura -> 409
            ahora = datetime.now(UTC)
            r_c_bad = await client.post(
                "/api/consultas",
                headers={"Idempotency-Key": "cons-bad-date"},
                json={
                    "titulo": "Consulta Pasada",
                    "descripcion_legal": "Descripción legal LPH de prueba",
                    "tipo_consulta": "CARTA_CONSULTA_1RA",
                    "regla_quorum": "DOS_TERCIOS",
                    "fecha_cierre": (ahora - timedelta(minutes=5)).isoformat(),
                    "opciones": [
                        {"etiqueta": "Aprobar", "es_opcion_aprobatoria": True},
                        {"etiqueta": "Rechazar", "es_opcion_aprobatoria": False},
                    ],
                },
            )
            assert r_c_bad.status_code == 400

            r_c_ok = await client.post(
                "/api/consultas",
                headers={"Idempotency-Key": "cons-futura-01"},
                json={
                    "titulo": "Consulta Abierta H21",
                    "descripcion_legal": "Descripción legal LPH de prueba",
                    "tipo_consulta": "CARTA_CONSULTA_1RA",
                    "regla_quorum": "DOS_TERCIOS",
                    "fecha_cierre": (ahora + timedelta(days=2)).isoformat(),
                    "opciones": [
                        {"etiqueta": "Aprobar", "es_opcion_aprobatoria": True},
                        {"etiqueta": "Rechazar", "es_opcion_aprobatoria": False},
                    ],
                },
            )
            assert r_c_ok.status_code == 201
            cid = r_c_ok.json()["id"]
            r_cerrar_premat = await client.post(
                f"/api/consultas/{cid}/cerrar", headers={"Idempotency-Key": "cons-cerrar-premat"}
            )
            assert r_cerrar_premat.status_code == 409

            from src.models import ConsultaComunitaria

            r_c_futura = await client.post(
                "/api/consultas",
                headers={"Idempotency-Key": "cons-no-abierta-01"},
                json={
                    "titulo": "Consulta Programada",
                    "descripcion_legal": "Descripción legal LPH de prueba",
                    "tipo_consulta": "CARTA_CONSULTA_1RA",
                    "regla_quorum": "DOS_TERCIOS",
                    "fecha_cierre": (ahora + timedelta(days=3)).isoformat(),
                    "opciones": [
                        {"etiqueta": "Aprobar", "es_opcion_aprobatoria": True},
                        {"etiqueta": "Rechazar", "es_opcion_aprobatoria": False},
                    ],
                },
            )
            assert r_c_futura.status_code == 201
            cid_fut = r_c_futura.json()["id"]
            async with factory() as s:
                cons_db = await s.get(ConsultaComunitaria, cid_fut)
                assert cons_db is not None
                cons_db.fecha_apertura = ahora + timedelta(days=1)
                await s.commit()

            op_fut_id = r_c_futura.json()["opciones"][0]["id"]
            r_vot_early = await client.post(
                f"/api/consultas/{cid_fut}/votar",
                headers={"Idempotency-Key": "vot-early-01"},
                json={"unidad_id": ids["u1"], "opcion_id": op_fut_id},
            )
            assert r_vot_early.status_code == 409

            # 3. Accesos QR: fechas en pasado -> 400; estado EXPIRADO -> 409; exp_unix adulterado -> 400
            r_p_bad = await client.post(
                "/api/accesos/pases",
                headers={"Idempotency-Key": "pase-bad-fecha"},
                json={
                    "unidad_id": ids["u2"],
                    "nombre_visitante": "Invitado Viejo",
                    "cedula_visitante": "V-11223344",
                    "modalidad": "UNICO_USO",
                    "valido_desde": (ahora - timedelta(hours=2)).isoformat(),
                    "valido_hasta": (ahora + timedelta(hours=2)).isoformat(),
                },
            )
            assert r_p_bad.status_code == 400

            exp_real = ahora + timedelta(hours=4)
            exp_falso = int((ahora + timedelta(hours=6)).timestamp())
            sig_exp = generar_firma_pase_qr(
                "jti-exp-db", ids["u1"], "VISITA", int(exp_real.timestamp()), get_qr_signing_key()
            )
            tok_exp = construir_token_pase_qr("jti-exp-db", ids["u1"], "VISITA", int(exp_real.timestamp()), sig_exp)

            sig_tamper = generar_firma_pase_qr("jti-tamper-exp", ids["u1"], "VISITA", exp_falso, get_qr_signing_key())
            tok_tamper = construir_token_pase_qr("jti-tamper-exp", ids["u1"], "VISITA", exp_falso, sig_tamper)

            async with factory() as s:
                s.add_all(
                    [
                        PaseVisita(
                            jti="jti-exp-db",
                            unidad_id=ids["u1"],
                            creado_por_id=pres.id,
                            nombre_visitante="Expirado DB",
                            cedula_visitante="V-90001001",
                            modalidad="UNICO_USO",
                            valido_desde=ahora - timedelta(hours=1),
                            valido_hasta=exp_real,
                            estado="EXPIRADO",
                            firma_hmac=sig_exp,
                        ),
                        PaseVisita(
                            jti="jti-tamper-exp",
                            unidad_id=ids["u1"],
                            creado_por_id=pres.id,
                            nombre_visitante="Tamper Exp",
                            cedula_visitante="V-90001002",
                            modalidad="UNICO_USO",
                            valido_desde=ahora - timedelta(hours=1),
                            valido_hasta=exp_real,
                            estado="ACTIVO",
                            firma_hmac=sig_tamper,
                        ),
                    ]
                )
                await s.commit()

            app.dependency_overrides[get_current_user] = lambda: conserje
            r_qr_exp = await client.post(
                "/api/accesos/verificar-qr",
                headers={"Idempotency-Key": "scan-exp-01"},
                json={"qr_token": tok_exp},
            )
            assert r_qr_exp.status_code == 409

            r_qr_tamper = await client.post(
                "/api/accesos/verificar-qr",
                headers={"Idempotency-Key": "scan-tamper-01"},
                json={"qr_token": tok_tamper},
            )
            assert r_qr_tamper.status_code == 400
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


# ==============================================================================
# 4. Worker Productivo, DecompressionBomb, SigV4 RFC 3986, BLMOVE/DLQ y find_worker
# ==============================================================================


@pytest.mark.asyncio
async def test_worker_avif_bomb_sigv4_blmove_dlq_y_frecuencias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert MAX_IMAGE_PIXELS == 16_000_000
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 10)
    with pytest.raises(ValueError, match="imagen inválido"):
        codificar_imagen_avif(_png_bytes(16, 16), strict_image=True)
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", MAX_IMAGE_PIXELS)

    # AWS SigV4 con clave con espacios/UTF-8 y endpoint con query ordenada
    monkeypatch.setenv("MINIO_ROOT_USER", "minio_user")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "minio_pass_123")
    monkeypatch.setenv("MINIO_BUCKET_NAME", "condo-media")
    capturado: dict[str, Any] = {}

    def _sig_handler(req: httpx.Request) -> httpx.Response:
        capturado["url"] = str(req.url)
        capturado["ct"] = req.headers.get("Content-Type")
        capturado["auth"] = req.headers.get("Authorization")
        return httpx.Response(200)

    with httpx.Client(transport=httpx.MockTransport(_sig_handler)) as hclient:
        uri = subir_objeto_minio_s3(
            b"avif-data",
            "comprobantes/archivo con espacio.avif",
            "http://minio.local:9000?z=2&a=1",
            http_client=hclient,
            content_type="image/avif",
        )
    assert uri == "s3://condo-media/comprobantes/archivo con espacio.avif"
    assert "%20" in capturado["url"] and "a=1&z=2" in capturado["url"]
    assert capturado["ct"] == "image/avif"
    assert "AWS4-HMAC-SHA256" in str(capturado["auth"])

    # Cola BLMOVE -> :processing -> LREM + LTRIM DLQ acotado + JSON no-dict a DLQ
    r_cli = _FakeStatefulRedis()
    cfg = WorkerSettings(max_retries=2, minio_endpoint="s3://condo-media")

    await r_cli.rpush(_NOTIFICATIONS_QUEUE, "[1, 2, 3]")
    await _consumir_cola_notificaciones_tick(r_cli, cfg)
    assert r_cli.lists.get(_NOTIFICATIONS_PROCESSING) == []
    assert r_cli.lists.get(_NOTIFICATIONS_DLQ) == ["[1, 2, 3]"]

    # Encolar y procesar tarea media PDF e imagen
    pdf_bytes = b"%PDF-1.4\n%%EOF\n"
    await encolar_tarea_media(r_cli, pdf_bytes, "incidencias/2026-11", "application/pdf", "incidencias/2026-11/a.pdf")
    await _consumir_cola_media_tick(r_cli, cfg)
    assert r_cli.lists.get(_MEDIA_PROCESSING) == []

    # Rellena DLQ por encima de MAX_DLQ_ITEMS y verifica LTRIM acotado
    r_cli.lists[_MEDIA_DLQ] = [f"err-{i}" for i in range(MAX_DLQ_ITEMS)]
    assert await procesar_mensaje_media("not-json-list", r_cli, cfg) is False
    assert len(r_cli.lists[_MEDIA_DLQ]) == MAX_DLQ_ITEMS

    bad_media_b64 = json.dumps(
        {"tipo": "MEDIA_UPLOAD", "content_base64": base64.b64encode(b"invalido").decode(), "intentos": 1}
    )
    assert await procesar_mensaje_media(bad_media_b64, r_cli, cfg) is False
    assert len(r_cli.lists[_MEDIA_DLQ]) == MAX_DLQ_ITEMS

    # Error no-dict también en notificaciones y BLMOVE en vacío retorna sin error
    assert await procesar_mensaje_notificacion("12345", r_cli, cfg) is False
    await _consumir_cola_media_tick(r_cli, cfg)

    # Scheduler respeta frecuencias UNICA, SEMANAL, MENSUAL y DIARIA
    engine, factory = await _crear_sqlite_fk(tmp_path)
    try:
        async with factory() as s:
            s.add_all(
                [
                    PlantillaTarea(titulo="Única", area="Techo", frecuencia="UNICA", activa=True),
                    PlantillaTarea(titulo="Semanal", area="Bomba", frecuencia="SEMANAL", activa=True),
                    PlantillaTarea(titulo="Mensual", area="Tanque", frecuencia="MENSUAL", activa=True),
                    PlantillaTarea(titulo="Diaria", area="Lobby", frecuencia="DIARIA", activa=True),
                ]
            )
            await s.commit()

            d1 = date(2026, 11, 2)  # Lunes
            d2 = date(2026, 11, 3)  # Martes (misma semana ISO y mismo mes)
            d3 = date(2026, 11, 9)  # Lunes siguiente (nueva semana ISO, mismo mes)
            d4 = date(2026, 12, 1)  # Mes siguiente
            assert await generar_tareas_diarias_desde_plantillas(s, fecha_objetivo=d1) == 4
            assert await generar_tareas_diarias_desde_plantillas(s, fecha_objetivo=d2) == 1
            assert await generar_tareas_diarias_desde_plantillas(s, fecha_objetivo=d3) == 2
            assert await generar_tareas_diarias_desde_plantillas(s, fecha_objetivo=d4) == 3
    finally:
        await engine.dispose()

    # find_worker.py: ignora PID 1/ppid=0 y /bin/bash, maneja ')' en comm, prioriza spawn_main y uvicorn
    fw_path = Path(__file__).resolve().parent.parent / "scripts" / "find_worker.py"
    spec = importlib.util.spec_from_file_location("find_worker", fw_path)
    assert spec is not None and spec.loader is not None
    fw_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fw_mod)

    proc_dir = tmp_path / "proc"
    for pid_str, comm, ppid, cmdline in [
        ("1", "(bash)", "0", b"/bin/bash\x00"),
        ("12", "(uv (wrap) )", "1", b"uv\x00run\x00uvicorn\x00"),
        ("45", "(python3.13)", "12", b"python3\x00-m\x00uvicorn\x00src.main:app\x00"),
        ("99", "(python (w) )", "45", b"python3\x00-c\x00from multiprocessing.spawn import spawn_main\x00"),
    ]:
        pdir = proc_dir / pid_str
        pdir.mkdir(parents=True)
        (pdir / "stat").write_text(f"{pid_str} {comm} S {ppid} 1 1 0\n", encoding="utf-8")
        (pdir / "cmdline").write_bytes(cmdline)

    assert fw_mod.find_target_python_pid(str(proc_dir)) == 99
    (proc_dir / "99" / "cmdline").write_bytes(b"python3\x00-m\x00other\x00")
    assert fw_mod.find_target_python_pid(str(proc_dir)) == 45
    assert fw_mod._parse_ppid_from_stat("corrupt-stat-without-paren") is None

    # Loop media opcional deshabilitado y con RedisError manejado sin tumbar supervisor
    stop_evt = asyncio.Event()
    await _loop_media_opcional(WorkerSettings(media_enabled=False), stop_evt, lambda: r_cli)
    r_cli.fail_on.add("blmove")

    async def _detener_pronto() -> None:
        await asyncio.sleep(0.05)
        stop_evt.set()

    await asyncio.gather(
        _loop_media_opcional(WorkerSettings(media_enabled=True, poll_seconds=0.01), stop_evt, lambda: r_cli),
        _detener_pronto(),
    )
    r_cli.fail_on.clear()

    # verificar_periodo_facturable y cargar_contexto_facturacion permiten recibos preliminares de área social
    ctx_dir = tmp_path / "ctx"
    ctx_dir.mkdir(parents=True, exist_ok=True)
    engine2, factory2 = await _crear_sqlite_fk(ctx_dir)
    try:
        ids2 = await _sembrar_escenario_condo(factory2)
        async with factory2() as s2:
            s2.add(
                Recibo(
                    unidad_id=ids2["u1"],
                    periodo="2099-05",
                    monto_usd=Decimal("30.00"),
                    monto_pagado_usd=Decimal("0.00"),
                    estado="PENDIENTE",
                )
            )
            await s2.flush()
            rec_pre = (await s2.execute(select(Recibo).where(Recibo.periodo == "2099-05"))).scalars().first()
            assert rec_pre is not None
            s2.add(
                ReciboItem(
                    recibo_id=rec_pre.id,
                    tipo_item="USO_AREA_SOCIAL",
                    descripcion="Uso Salón",
                    monto_usd=Decimal("30.00"),
                )
            )
            await s2.commit()
            await verificar_periodo_facturable(s2, "2099-05")
            unidades_ctx, *_ = await cargar_contexto_facturacion(
                s2, FacturarPeriodoRequest(periodo="2099-05", modalidad="PARTES_IGUALES", incluir_fondo_reserva=False)
            )
            assert len(unidades_ctx) == 2
    finally:
        await engine2.dispose()


def test_worker_media_constantes_env_flag_y_normalizacion_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    assert MAX_IMAGE_PIXELS == 16_000_000
    assert Image.MAX_IMAGE_PIXELS == 16_000_000
    assert DEFAULT_HEARTBEAT_PATH == Path(tempfile.gettempdir()) / "worker_heartbeat"
    assert OPTIONAL_WORKERS == frozenset({"media_avif_consumer"})
    assert _MEDIA_QUEUE == "queue:media:avif"
    assert _MEDIA_PROCESSING == "queue:media:avif:processing"
    assert _MEDIA_DLQ == "queue:media:avif:dlq"
    assert _NOTIFICATIONS_QUEUE == "queue:notifications"
    assert _NOTIFICATIONS_PROCESSING == "queue:notifications:processing"
    assert _NOTIFICATIONS_DLQ == "queue:notifications:dlq"
    assert MAX_DLQ_ITEMS == 1000
    assert worker_mod._normalize_minio_endpoint is normalize_minio_endpoint

    expected_exports = [
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
    assert worker_exports == expected_exports
    for sym in expected_exports:
        assert hasattr(worker_mod, sym)

    monkeypatch.delenv("QA_TEST_FLAG", raising=False)
    assert env_flag("QA_TEST_FLAG") is False
    assert env_flag("QA_TEST_FLAG", default=False) is False
    assert env_flag("QA_TEST_FLAG", default=True) is True

    for truthy in ("1", " 1 ", "true", " TRUE ", "yes", " YeS ", "on", " oN "):
        monkeypatch.setenv("QA_TEST_FLAG", truthy)
        assert env_flag("QA_TEST_FLAG", default=False) is True

    for falsy in ("", "   ", "0", "false", " FALSE ", "no", "off", "random"):
        monkeypatch.setenv("QA_TEST_FLAG", falsy)
        assert env_flag("QA_TEST_FLAG", default=True) is False

    assert normalize_minio_endpoint("", False) == ""
    assert normalize_minio_endpoint("   ", True) == ""
    assert normalize_minio_endpoint("  s3://condo/ruta/  ", False) == "s3://condo/ruta"
    assert normalize_minio_endpoint("s3://condo/", True) == "s3://condo"
    assert normalize_minio_endpoint("  https://minio.local:9000/  ", False) == "https://minio.local:9000"
    assert normalize_minio_endpoint("https://minio.local:9000/", True) == "https://minio.local:9000"
    assert normalize_minio_endpoint("http://minio.local:9000/", True) == "https://minio.local:9000"
    assert normalize_minio_endpoint("http://minio.local:9000/", False) == "http://minio.local:9000"
    assert normalize_minio_endpoint("  minio.local:9000/  ", True) == "https://minio.local:9000"
    assert normalize_minio_endpoint("  minio.local:9000/  ", False) == "http://minio.local:9000"
    assert _aplicar_esquema_http("http://h:9", True) == "https://h:9"
    assert _aplicar_esquema_http("https://h:9", False) == "https://h:9"
    assert _aplicar_esquema_http("h:9", False) == "http://h:9"


def test_worker_media_sigv4_bucket_credenciales_y_put_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MINIO_BUCKET_NAME", raising=False)
    monkeypatch.delenv("MINIO_BUCKET", raising=False)
    assert _env_bucket_name() == ""
    assert resolver_bucket_minio() == "condominio-media"

    monkeypatch.setenv("MINIO_BUCKET", "  bkt-secundario  ")
    assert _env_bucket_name() == "bkt-secundario"
    assert resolver_bucket_minio() == "bkt-secundario"

    monkeypatch.setenv("MINIO_BUCKET_NAME", "  bkt-primario  ")
    assert _env_bucket_name() == "bkt-primario"
    assert resolver_bucket_minio() == "bkt-primario"
    assert resolver_bucket_minio("   ") == "bkt-primario"
    assert resolver_bucket_minio("  bkt-explicito  ") == "bkt-explicito"

    monkeypatch.setenv("MINIO_BUCKET_NAME", "   ")
    monkeypatch.setenv("MINIO_BUCKET", "   ")
    assert _env_bucket_name() == ""
    assert resolver_bucket_minio() == "condominio-media"

    monkeypatch.delenv("MINIO_ROOT_USER", raising=False)
    monkeypatch.delenv("MINIO_ROOT_PASSWORD", raising=False)
    with pytest.raises(ValueError, match=r"^Credenciales MinIO no configuradas para carga S3\.$"):
        _resolver_minio_credenciales()

    monkeypatch.setenv("MINIO_ROOT_USER", "   ")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "minio_qa_secret_123")
    with pytest.raises(ValueError, match=r"^Credenciales MinIO no configuradas para carga S3\.$"):
        _resolver_minio_credenciales()

    monkeypatch.setenv("MINIO_ROOT_USER", "minio_qa_user")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "")
    with pytest.raises(ValueError, match=r"^Credenciales MinIO no configuradas para carga S3\.$"):
        _resolver_minio_credenciales()

    monkeypatch.setenv("MINIO_ROOT_USER", "  minio_qa_user  ")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", " sec_key_123 ")
    assert _resolver_minio_credenciales() == ("minio_qa_user", " sec_key_123 ")

    pdf_digest = hashlib.sha256(b"pdf-data").hexdigest()[:24]
    img_digest = hashlib.sha256(b"img-data").hexdigest()[:24]
    assert construir_clave_evidencia(b"pdf-data", "/pagos/2026/", "application/pdf") == (
        f"pagos/2026/{pdf_digest}.pdf",
        "application/pdf",
    )
    assert construir_clave_evidencia(b"img-data", "///", "image/png") == (f"general/{img_digest}.avif", "image/avif")

    assert _encode_sigv4_uri("/bkt/a-b_c.d~e/foto%201+ñ.avif") == "/bkt/a-b_c.d~e/foto%201%2B%C3%B1.avif"
    assert _encode_sigv4_query("") == ""
    assert _encode_sigv4_query("z=2&empty=&a=hello world") == "a=hello%20world&empty=&z=2"

    assert _construir_destino_s3("http://minio.local:9000/proxy/?z=2&empty=&a=1", "bkt", "dir/a b.avif") == (
        "minio.local:9000",
        "/proxy/bkt/dir/a%20b.avif",
        "a=1&empty=&z=2",
        "http://minio.local:9000/proxy/bkt/dir/a%20b.avif?a=1&empty=&z=2",
    )
    assert _construir_destino_s3("https://minio.local:9000/", "bkt", "k.avif") == (
        "minio.local:9000",
        "/bkt/k.avif",
        "",
        "https://minio.local:9000/bkt/k.avif",
    )
    assert _construir_destino_s3("//minio.local:9000", "bkt", "k.avif") == (
        "minio.local:9000",
        "/bkt/k.avif",
        "",
        "//minio.local:9000/bkt/k.avif",
    )

    assert _hmac_sha256(b"clave", "msg") == hmac.new(b"clave", b"msg", hashlib.sha256).digest()
    ref_k_date = hmac.new(b"AWS4sk_test", b"20261119", hashlib.sha256).digest()
    ref_k_reg = hmac.new(ref_k_date, b"us-east-1", hashlib.sha256).digest()
    ref_k_srv = hmac.new(ref_k_reg, b"s3", hashlib.sha256).digest()
    ref_signing_key = hmac.new(ref_k_srv, b"aws4_request", hashlib.sha256).digest()
    assert _signing_key_sigv4("sk_test", "20261119", "us-east-1", "s3") == ref_signing_key

    fixed_dt = datetime(2026, 11, 19, 8, 9, 10, tzinfo=UTC)

    class _FrozenDatetime:
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            assert tz is UTC
            return fixed_dt

    monkeypatch.setattr(worker_media_mod, "datetime", _FrozenDatetime)

    payload_hash = hashlib.sha256(b"binario-prueba").hexdigest()
    amz_date = "20261119T080910Z"
    date_stamp = "20261119"

    def _ref_auth(host: str, uri: str, query: str, region: str, ak: str, sk: str) -> str:
        c_hdrs = f"host:{host}\nx-amz-content-sha256:{payload_hash}\nx-amz-date:{amz_date}\n"
        s_hdrs = "host;x-amz-content-sha256;x-amz-date"
        c_req = f"PUT\n{uri}\n{query}\n{c_hdrs}\n{s_hdrs}\n{payload_hash}"
        scope = f"{date_stamp}/{region}/s3/aws4_request"
        req_hash = hashlib.sha256(c_req.encode("utf-8")).hexdigest()
        sts = f"AWS4-HMAC-SHA256\n{amz_date}\n{scope}\n{req_hash}"
        k1 = hmac.new(f"AWS4{sk}".encode("utf-8"), date_stamp.encode("utf-8"), hashlib.sha256).digest()
        k2 = hmac.new(k1, region.encode("utf-8"), hashlib.sha256).digest()
        k3 = hmac.new(k2, b"s3", hashlib.sha256).digest()
        k4 = hmac.new(k3, b"aws4_request", hashlib.sha256).digest()
        sig = hmac.new(k4, sts.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"AWS4-HMAC-SHA256 Credential={ak}/{scope}, SignedHeaders={s_hdrs}, Signature={sig}"

    hdrs_default = _build_sigv4_headers("minio.local:9000", "/bkt/foto 1.avif", payload_hash, "ak_1", "sk_test")
    assert hdrs_default == {
        "Host": "minio.local:9000",
        "Content-Type": "image/avif",
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
        "Authorization": _ref_auth("minio.local:9000", "/bkt/foto%201.avif", "", "us-east-1", "ak_1", "sk_test"),
    }

    hdrs_custom = _build_sigv4_headers(
        "s3.local:9443",
        "/bkt/doc.pdf",
        payload_hash,
        "ak_2",
        "sk_test",
        region="eu-west-1",
        canonical_query="a=1&b=2",
        content_type="application/pdf",
    )
    assert hdrs_custom == {
        "Host": "s3.local:9443",
        "Content-Type": "application/pdf",
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
        "Authorization": _ref_auth("s3.local:9443", "/bkt/doc.pdf", "a=1&b=2", "eu-west-1", "ak_2", "sk_test"),
    }

    capturas: list[dict[str, Any]] = []

    def _ok_transport(req: httpx.Request) -> httpx.Response:
        capturas.append(
            {
                "method": req.method,
                "url": str(req.url),
                "headers": dict(req.headers),
                "content": req.content,
                "timeout": req.extensions.get("timeout"),
            }
        )
        return httpx.Response(200)

    monkeypatch.setenv("MINIO_ROOT_USER", "ak_s3")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "sk_s3")
    monkeypatch.setenv("MINIO_BUCKET_NAME", "bkt-env")

    with httpx.Client(transport=httpx.MockTransport(_ok_transport)) as cli:
        s3_uri = subir_objeto_minio_s3(
            b"binario-prueba",
            "dir/item.avif",
            "https://minio.local:9000/",
            bucket_name="bkt-arg",
            http_client=cli,
        )
    assert s3_uri == "s3://bkt-arg/dir/item.avif"
    assert len(capturas) == 1
    assert capturas[0]["method"] == "PUT"
    assert capturas[0]["url"] == "https://minio.local:9000/bkt-arg/dir/item.avif"
    assert capturas[0]["content"] == b"binario-prueba"
    assert capturas[0]["headers"]["content-type"] == "image/avif"
    assert capturas[0]["headers"]["x-amz-content-sha256"] == payload_hash
    assert capturas[0]["timeout"] == {"connect": 15.0, "read": 15.0, "write": 15.0, "pool": 15.0}

    with httpx.Client(transport=httpx.MockTransport(lambda _r: httpx.Response(500))) as err_cli:
        with pytest.raises(httpx.HTTPStatusError):
            _ejecutar_put_http("https://minio.local:9000/x", b"data", {"Host": "minio.local:9000"}, err_cli)

    recorded_clients: list[dict[str, Any]] = []

    def _make_fake_client(status_code: int) -> type[Any]:
        class _FakeClient:
            def __init__(self, *, timeout: float | None = None) -> None:
                recorded_clients.append({"init_timeout": timeout, "entered": False, "exited": False})

            def __enter__(self) -> _FakeClient:
                recorded_clients[-1]["entered"] = True
                return self

            def __exit__(self, *args: object) -> None:
                recorded_clients[-1]["exited"] = True

            def put(self, url: str, *, content: bytes, headers: dict[str, str]) -> httpx.Response:
                recorded_clients[-1].update({"url": url, "content": content, "headers": dict(headers)})
                req = httpx.Request("PUT", url, headers=headers, content=content)
                return httpx.Response(status_code, request=req)

        return _FakeClient

    monkeypatch.setattr(worker_media_mod.httpx, "Client", _make_fake_client(200))
    uri_no_cli = subir_objeto_minio_s3(
        b"pdf-raw",
        "recibos/r1.pdf",
        "http://minio.local:9000",
        content_type="application/pdf",
    )
    assert uri_no_cli == "s3://bkt-env/recibos/r1.pdf"
    assert recorded_clients[-1]["init_timeout"] == 15.0
    assert recorded_clients[-1]["entered"] is True
    assert recorded_clients[-1]["exited"] is True
    assert recorded_clients[-1]["headers"]["Content-Type"] == "application/pdf"

    monkeypatch.setattr(worker_media_mod.httpx, "Client", _make_fake_client(403))
    with pytest.raises(httpx.HTTPStatusError):
        subir_objeto_minio_s3(b"pdf-raw", "recibos/r1.pdf", "http://minio.local:9000")


def test_worker_media_avif_exif_bounds_y_ejecutar_subida(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match=r"^El archivo de imagen no puede estar vacío\.$"):
        codificar_imagen_avif(b"")

    assert codificar_imagen_avif(b"texto-no-imagen") == b"texto-no-imagen"

    with pytest.raises(ValueError, match=r"^Contenido de imagen inválido para conversión AVIF\.$") as exc_info:
        codificar_imagen_avif(b"texto-no-imagen", strict_image=True)
    assert isinstance(exc_info.value.__cause__, UnidentifiedImageError)

    png_16 = _png_bytes(16, 16)
    png_10 = _png_bytes(10, 10)
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)
    assert len(codificar_imagen_avif(png_10, strict_image=True)) > 0

    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 10)
    assert codificar_imagen_avif(png_16, strict_image=False) == png_16
    with pytest.raises(ValueError, match=r"^Contenido de imagen inválido para conversión AVIF\.$"):
        codificar_imagen_avif(png_16, strict_image=True)
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", MAX_IMAGE_PIXELS)

    # EXIF orientation (6 -> 12x6 transpuesto a 6x12), conversión RGBA -> RGB, quality=60 y stripping de EXIF
    exif = Image.Exif()
    exif[0x0112] = 6
    exif[0x010E] = "secreto-exif-gps"
    exif_buf = BytesIO()
    Image.new("RGBA", (12, 6), color=(220, 40, 80, 180)).save(exif_buf, format="PNG", exif=exif.tobytes())
    png_exif_bytes = exif_buf.getvalue()

    orig_save = Image.Image.save
    save_calls: list[dict[str, Any]] = []

    def _spy_save(self: Image.Image, fp: Any, format: str | None = None, **params: Any) -> None:
        save_calls.append(
            {
                "format": format,
                "quality": params.get("quality"),
                "has_exif": "exif" in params,
                "mode": self.mode,
            }
        )
        orig_save(self, fp, format=format, **params)

    monkeypatch.setattr(Image.Image, "save", _spy_save)
    avif_bytes = codificar_imagen_avif(png_exif_bytes, strict_image=True)
    monkeypatch.setattr(Image.Image, "save", orig_save)

    assert save_calls == [{"format": "AVIF", "quality": 60, "has_exif": False, "mode": "RGB"}]
    assert b"secreto-exif-gps" not in avif_bytes
    with Image.open(BytesIO(avif_bytes)) as out_img:
        assert out_img.format == "AVIF"
        assert out_img.mode == "RGB"
        assert out_img.size == (6, 12)
        assert len(out_img.getexif()) == 0

    def _raise_oserror(*_args: Any, **_kwargs: Any) -> Any:
        raise OSError("fallo de lectura")

    with monkeypatch.context() as mp_io:
        mp_io.setattr(worker_media_mod.Image, "open", _raise_oserror)
        assert codificar_imagen_avif(png_10, strict_image=False) == png_10
        with pytest.raises(ValueError, match=r"^Contenido de imagen inválido para conversión AVIF\.$"):
            codificar_imagen_avif(png_10, strict_image=True)

    # convertir_y_subir_avif: defaults, prefijo vacío, override y MINIO_USE_SSL
    raw_fallback = b"no-es-imagen-fallback"
    expected_digest = hashlib.sha256(raw_fallback).hexdigest()[:24]
    assert convertir_y_subir_avif(raw_fallback, "///") == f"s3://condominio-media/general/{expected_digest}.avif"
    assert (
        convertir_y_subir_avif(raw_fallback, "incidencias", objeto_key_override="/custom/ruta.avif/")
        == "s3://condominio-media/custom/ruta.avif"
    )

    monkeypatch.setenv("MINIO_ROOT_USER", "ak_media")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "sk_media")
    monkeypatch.delenv("MINIO_BUCKET_NAME", raising=False)
    monkeypatch.delenv("MINIO_BUCKET", raising=False)

    put_urls: list[tuple[str, str, bytes]] = []

    def _capture_http_put(req: httpx.Request) -> httpx.Response:
        put_urls.append((str(req.url), req.headers.get("Content-Type", ""), req.content))
        return httpx.Response(200)

    with httpx.Client(transport=httpx.MockTransport(_capture_http_put)) as hcli:
        monkeypatch.setenv("MINIO_USE_SSL", "true")
        u_ssl_env = convertir_y_subir_avif(
            png_10,
            "pagos/2026",
            minio_endpoint="minio.local:9000",
            strict_image=True,
            http_client=hcli,
        )
        u_ssl_override = convertir_y_subir_avif(
            png_10,
            "pagos/2026",
            minio_endpoint="minio.local:9000",
            strict_image=True,
            http_client=hcli,
            minio_use_ssl=False,
        )
        monkeypatch.setenv("MINIO_USE_SSL", "false")
        u_plain_env = convertir_y_subir_avif(
            png_10,
            "pagos/2026",
            minio_endpoint="minio.local:9000",
            strict_image=True,
            http_client=hcli,
        )

    assert u_ssl_env.startswith("s3://condominio-media/pagos/2026/")
    assert u_ssl_override.startswith("s3://condominio-media/pagos/2026/")
    assert u_plain_env.startswith("s3://condominio-media/pagos/2026/")
    assert put_urls[0][0].startswith("https://minio.local:9000/condominio-media/pagos/2026/")
    assert put_urls[1][0].startswith("http://minio.local:9000/condominio-media/pagos/2026/")
    assert put_urls[2][0].startswith("http://minio.local:9000/condominio-media/pagos/2026/")

    # _str_campo, _decodificar_payload_media, _subir_pdf_directo y ejecutar_subida_media_bytes
    assert _str_campo({"k": "valor"}, "k") == "valor"
    assert _str_campo({"k": ""}, "k", "general") == "general"
    assert _str_campo({}, "k", "general") == "general"

    for bad_ev in ({}, {"content_base64": None}, {"content_base64": ""}, {"content_base64": 123}):
        with pytest.raises(ValueError, match=r"^Tarea media sin contenido base64\.$"):
            _decodificar_payload_media(bad_ev)

    with pytest.raises(binascii.Error):
        _decodificar_payload_media({"content_base64": "abc$def="})

    payload_ok = _decodificar_payload_media(
        {
            "content_base64": base64.b64encode(b"%PDF-1.4").decode("ascii"),
            "mime_origen": "application/pdf",
            "objeto_key": "/docs/recibo.pdf/",
        }
    )
    assert payload_ok.raw_bytes == b"%PDF-1.4"
    assert payload_ok.mime_origen == "application/pdf"
    assert payload_ok.prefijo == "general"
    assert payload_ok.objeto_key == "docs/recibo.pdf"

    assert _subir_pdf_directo(b"%PDF-1.4", "docs/a.pdf", "s3://bkt", True) == "s3://bkt/docs/a.pdf"
    assert (
        ejecutar_subida_media_bytes(
            {
                "content_base64": base64.b64encode(b"%PDF-1.4").decode("ascii"),
                "mime_origen": "application/pdf",
                "objeto_key": "/docs/local.pdf/",
            },
            "",
            False,
        )
        == "s3://condominio-media/docs/local.pdf"
    )

    captured_media_puts: list[dict[str, Any]] = []

    class _MediaFakeClient:
        def __init__(self, *, timeout: float | None = None) -> None:
            captured_media_puts.append({"timeout": timeout})

        def __enter__(self) -> _MediaFakeClient:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def put(self, url: str, *, content: bytes, headers: dict[str, str]) -> httpx.Response:
            captured_media_puts[-1].update({"url": url, "content": content, "headers": dict(headers)})
            return httpx.Response(200, request=httpx.Request("PUT", url))

    monkeypatch.setattr(worker_media_mod.httpx, "Client", _MediaFakeClient)

    pdf_res = ejecutar_subida_media_bytes(
        {
            "content_base64": base64.b64encode(b"%PDF-1.7\n%%EOF").decode("ascii"),
            "mime_origen": "application/pdf",
            "objeto_key": "/docs/comprobante.pdf/",
        },
        "minio.local:9000",
        True,
    )
    assert pdf_res == "s3://condominio-media/docs/comprobante.pdf"
    assert captured_media_puts[-1]["url"] == "https://minio.local:9000/condominio-media/docs/comprobante.pdf"
    assert captured_media_puts[-1]["headers"]["Content-Type"] == "application/pdf"
    assert captured_media_puts[-1]["content"] == b"%PDF-1.7\n%%EOF"

    img_res = ejecutar_subida_media_bytes(
        {
            "content_base64": base64.b64encode(png_10).decode("ascii"),
            "mime_origen": "image/png",
        },
        "minio.local:9000",
        False,
    )
    assert img_res.startswith("s3://condominio-media/general/") and img_res.endswith(".avif")
    assert captured_media_puts[-1]["url"].startswith("http://minio.local:9000/condominio-media/general/")
    assert captured_media_puts[-1]["headers"]["Content-Type"] == "image/avif"
    with Image.open(BytesIO(captured_media_puts[-1]["content"])) as decoded_avif:
        assert decoded_avif.format == "AVIF"

    with pytest.raises(ValueError, match=r"^Contenido de imagen inválido para conversión AVIF\.$"):
        ejecutar_subida_media_bytes(
            {
                "content_base64": base64.b64encode(b"basura-png").decode("ascii"),
                "mime_origen": "image/png",
            },
            "s3://condominio-media",
            False,
        )


@pytest.mark.asyncio
async def test_worker_shared_hooks_settings_smtp_y_procesadores(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
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
    for k in env_keys:
        monkeypatch.delenv(k, raising=False)

    defaults = WorkerSettings.from_env()
    assert defaults == WorkerSettings()
    assert defaults.heartbeat_path == DEFAULT_HEARTBEAT_PATH
    assert defaults.poll_seconds == 1.0
    assert defaults.blpop_timeout_seconds == 1
    assert defaults.scheduler_interval_seconds == 300.0
    assert defaults.max_heartbeat_age_seconds == 90.0
    assert defaults.media_enabled is False
    assert defaults.smtp_enabled is False
    assert defaults.smtp_host == ""
    assert defaults.smtp_port == 587
    assert defaults.smtp_user == ""
    assert defaults.smtp_password == ""
    assert defaults.smtp_from == "no-responder@condominio.local"
    assert defaults.smtp_use_tls is True
    assert defaults.max_retries == 3
    assert defaults.minio_endpoint == ""
    assert defaults.minio_use_ssl is False

    monkeypatch.setenv("WORKER_HEARTBEAT_PATH", "   ")
    monkeypatch.setenv("WORKER_POLL_SECONDS", "   ")
    monkeypatch.setenv("WORKER_BLPOP_TIMEOUT_SECONDS", "0")
    monkeypatch.setenv("WORKER_MAX_RETRIES", "-2")
    clamped = WorkerSettings.from_env()
    assert clamped.heartbeat_path == DEFAULT_HEARTBEAT_PATH
    assert clamped.poll_seconds == 1.0
    assert clamped.blpop_timeout_seconds == 1
    assert clamped.max_retries == 1

    monkeypatch.setenv("WORKER_HEARTBEAT_PATH", " /tmp/hb_custom_qa ")
    monkeypatch.setenv("WORKER_POLL_SECONDS", " 2.5 ")
    monkeypatch.setenv("WORKER_BLPOP_TIMEOUT_SECONDS", " 7 ")
    monkeypatch.setenv("WORKER_SCHEDULER_INTERVAL_SECONDS", " 120.5 ")
    monkeypatch.setenv("WORKER_HEARTBEAT_MAX_AGE_SECONDS", " 45.0 ")
    monkeypatch.setenv("WORKER_MEDIA_ENABLED", "on")
    monkeypatch.setenv("SMTP_ENABLED", "yes")
    monkeypatch.setenv("SMTP_HOST", " smtp.condominio.test ")
    monkeypatch.setenv("SMTP_PORT", " 2525 ")
    monkeypatch.setenv("SMTP_USER", " mailer ")
    monkeypatch.setenv("SMTP_PASSWORD", " pass_space ")
    monkeypatch.setenv("SMTP_FROM", " alertas@condominio.test ")
    monkeypatch.setenv("SMTP_USE_TLS", "0")
    monkeypatch.setenv("WORKER_MAX_RETRIES", " 6 ")
    monkeypatch.setenv("MINIO_ENDPOINT", " http://minio.local:9000/ ")
    monkeypatch.setenv("MINIO_USE_SSL", "true")
    custom_cfg = WorkerSettings.from_env()
    assert custom_cfg.heartbeat_path == Path("/tmp/hb_custom_qa")
    assert custom_cfg.poll_seconds == 2.5
    assert custom_cfg.blpop_timeout_seconds == 7
    assert custom_cfg.scheduler_interval_seconds == 120.5
    assert custom_cfg.max_heartbeat_age_seconds == 45.0
    assert custom_cfg.media_enabled is True
    assert custom_cfg.smtp_enabled is True
    assert custom_cfg.smtp_host == "smtp.condominio.test"
    assert custom_cfg.smtp_port == 2525
    assert custom_cfg.smtp_user == "mailer"
    assert custom_cfg.smtp_password == " pass_space "
    assert custom_cfg.smtp_from == "alertas@condominio.test"
    assert custom_cfg.smtp_use_tls is False
    assert custom_cfg.max_retries == 6
    assert custom_cfg.minio_endpoint == "https://minio.local:9000"
    assert custom_cfg.minio_use_ssl is True

    # SMTP validación, logging en modo omitido y combinaciones TLS/login
    with pytest.raises(ValueError, match=r"^Evento de notificación sin destinatarios válidos\.$"):
        enviar_correo_smtp({"destinatarios": ["", "   "]}, WorkerSettings())

    smtp_calls: list[dict[str, Any]] = []

    class _FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int = 10) -> None:
            smtp_calls.append(
                {"host": host, "port": port, "timeout": timeout, "tls": False, "login": None, "msg": None}
            )

        def __enter__(self) -> _FakeSMTP:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def starttls(self, context: Any = None) -> None:
            assert isinstance(context, ssl.SSLContext)
            smtp_calls[-1]["tls"] = True

        def login(self, user: str, password: str) -> None:
            smtp_calls[-1]["login"] = (user, password)

        def send_message(self, msg: Any) -> None:
            smtp_calls[-1]["msg"] = msg

    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)
    with caplog.at_level(logging.INFO, logger="src.worker"):
        enviar_correo_smtp(
            {"destinatarios": ["a@test.com"], "asunto": "Aviso\r\nSeguro", "cuerpo": "Hola"},
            WorkerSettings(smtp_enabled=False, smtp_host="smtp.local"),
        )
        enviar_correo_smtp(
            {"destinatarios": ["a@test.com"], "asunto": "SinHost", "cuerpo": "Hola"},
            WorkerSettings(smtp_enabled=True, smtp_host=""),
        )
    assert smtp_calls == []
    assert "Notificación omitida (SMTP deshabilitado): asunto=Aviso  Seguro" in caplog.text
    assert "Notificación omitida (SMTP deshabilitado): asunto=SinHost" in caplog.text

    enviar_correo_smtp(
        {"destinatarios": [" a@test.com ", "", "b@test.com"], "asunto": "  Hola\nMundo  ", "cuerpo": "Cuerpo"},
        WorkerSettings(
            smtp_enabled=True,
            smtp_host="smtp.local",
            smtp_port=25,
            smtp_from=" remit@test.com\r\n ",
            smtp_use_tls=False,
            smtp_user="",
            smtp_password="",
        ),
    )
    assert smtp_calls[-1]["host"] == "smtp.local"
    assert smtp_calls[-1]["port"] == 25
    assert smtp_calls[-1]["timeout"] == 10
    assert smtp_calls[-1]["tls"] is False
    assert smtp_calls[-1]["login"] is None
    assert smtp_calls[-1]["msg"]["From"] == "remit@test.com"
    assert smtp_calls[-1]["msg"]["To"] == "a@test.com, b@test.com"
    assert smtp_calls[-1]["msg"]["Subject"] == "Hola Mundo"
    assert "Cuerpo" in smtp_calls[-1]["msg"].get_content()

    enviar_correo_smtp(
        {"destinatarios": ["a@test.com"], "asunto": "SoloTLS", "cuerpo": "OK"},
        WorkerSettings(smtp_enabled=True, smtp_host="smtp.local", smtp_use_tls=True, smtp_user="u", smtp_password=""),
    )
    assert smtp_calls[-1]["tls"] is True
    assert smtp_calls[-1]["login"] is None

    enviar_correo_smtp(
        {"destinatarios": ["a@test.com"], "asunto": "ConAuth", "cuerpo": "OK"},
        WorkerSettings(smtp_enabled=True, smtp_host="smtp.local", smtp_use_tls=True, smtp_user="u", smtp_password="p"),
    )
    assert smtp_calls[-1]["tls"] is True
    assert smtp_calls[-1]["login"] == ("u", "p")

    # _consumir_cola_*_tick + procesar_mensaje_media + procesar_mensaje_notificacion
    class _SpyRedis(_FakeStatefulRedis):
        def __init__(self) -> None:
            super().__init__()
            self.blmove_calls: list[tuple[str, str, int, str, str]] = []

        async def blmove(
            self,
            src: str,
            dst: str,
            timeout: int,
            src_dir: str,
            dst_dir: str,
        ) -> str | None:
            self.blmove_calls.append((src, dst, timeout, src_dir, dst_dir))
            return await super().blmove(src, dst, timeout, src_dir, dst_dir)

    spy_r = _SpyRedis()
    tick_cfg = WorkerSettings(
        blpop_timeout_seconds=7,
        max_retries=2,
        minio_endpoint="minio.local:9000",
        minio_use_ssl=True,
    )
    await spy_r.rpush(_NOTIFICATIONS_QUEUE, json.dumps({"destinatarios": ["x@test.com"], "asunto": "A", "cuerpo": "B"}))
    await _consumir_cola_notificaciones_tick(spy_r, tick_cfg)
    assert spy_r.blmove_calls[-1] == (_NOTIFICATIONS_QUEUE, _NOTIFICATIONS_PROCESSING, 7, "LEFT", "RIGHT")
    assert spy_r.lists.get(_NOTIFICATIONS_PROCESSING) == []

    monkeypatch.setenv("MINIO_ROOT_USER", "ak_tick")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "sk_tick")
    monkeypatch.delenv("MINIO_BUCKET_NAME", raising=False)
    monkeypatch.delenv("MINIO_BUCKET", raising=False)
    http_hits: list[str] = []

    class _TickClient:
        def __init__(self, *, timeout: float | None = None) -> None:
            del timeout
            self._status = 200

        def __enter__(self) -> _TickClient:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def put(self, url: str, *, content: bytes, headers: dict[str, str]) -> httpx.Response:
            del content, headers
            http_hits.append(url)
            return httpx.Response(self._status, request=httpx.Request("PUT", url))

    monkeypatch.setattr(worker_media_mod.httpx, "Client", _TickClient)
    png_b64 = base64.b64encode(_png_bytes(8, 8)).decode("ascii")
    await spy_r.rpush(_MEDIA_QUEUE, json.dumps({"content_base64": png_b64, "mime_origen": "image/png"}))
    await _consumir_cola_media_tick(spy_r, tick_cfg)
    assert spy_r.blmove_calls[-1] == (_MEDIA_QUEUE, _MEDIA_PROCESSING, 7, "LEFT", "RIGHT")
    assert len(http_hits) == 1 and http_hits[0].startswith("https://minio.local:9000/condominio-media/")

    class _FailingTickClient(_TickClient):
        def put(self, url: str, *, content: bytes, headers: dict[str, str]) -> httpx.Response:
            del content, headers
            return httpx.Response(500, request=httpx.Request("PUT", url))

    monkeypatch.setattr(worker_media_mod.httpx, "Client", _FailingTickClient)
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="src.worker"):
        assert await procesar_mensaje_media("no-json", spy_r, tick_cfg) is False
        assert spy_r.lists[_MEDIA_DLQ][-1] == "no-json"
        assert "Payload malformado o no-objeto enviado a DLQ de medios." in caplog.text

        ev_http_0 = json.dumps({"content_base64": png_b64, "mime_origen": "image/png", "intentos": 0})
        assert await procesar_mensaje_media(ev_http_0, spy_r, tick_cfg) is False
        requeued = json.loads(spy_r.lists[_MEDIA_QUEUE][-1])
        assert requeued["intentos"] == 1
        assert "500" in requeued["ultimo_error"]

        assert await procesar_mensaje_media(spy_r.lists[_MEDIA_QUEUE][-1], spy_r, tick_cfg) is False
        dlq_item = json.loads(spy_r.lists[_MEDIA_DLQ][-1])
        assert dlq_item["intentos"] == 2
        assert "Fallo procesando evidencia multimedia:" in caplog.text

        bad_b64_ev = json.dumps({"content_base64": "bad$b64=", "mime_origen": "image/png", "intentos": 1})
        assert await procesar_mensaje_media(bad_b64_ev, spy_r, tick_cfg) is False

        assert await procesar_mensaje_notificacion("{bad", spy_r, tick_cfg) is False
        assert "Payload malformado o no-objeto enviado a DLQ de notificaciones." in caplog.text

        assert await procesar_mensaje_notificacion(json.dumps({"destinatarios": []}), spy_r, tick_cfg) is False
        assert "Fallo procesando notificación por correo:" in caplog.text

        def _smtp_boom(*_a: Any, **_kw: Any) -> Any:
            raise smtplib.SMTPException("smtp down")

        with monkeypatch.context() as mp_smtp:
            mp_smtp.setattr(smtplib, "SMTP", _smtp_boom)
            smtp_cfg = WorkerSettings(smtp_enabled=True, smtp_host="smtp.local", max_retries=2)
            payload_smtp = json.dumps({"destinatarios": ["a@test.com"], "asunto": "S", "cuerpo": "C"})
            assert await procesar_mensaje_notificacion(payload_smtp, spy_r, smtp_cfg) is False
            assert json.loads(spy_r.lists[_NOTIFICATIONS_QUEUE][-1])["intentos"] == 1


@pytest.mark.asyncio
async def test_worker_shared_hooks_heartbeat_salud_backoff_y_cli(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    # 1. write_worker_heartbeat y verify_worker_heartbeat
    missing_hb = tmp_path / "missing_hb"
    assert verify_worker_heartbeat(missing_hb) is False
    dir_hb = tmp_path / "dir_hb"
    dir_hb.mkdir()
    assert verify_worker_heartbeat(dir_hb) is False

    nested_hb = tmp_path / "sub" / "nested" / "heartbeat"
    write_worker_heartbeat(nested_hb)
    assert nested_hb.is_file()
    parsed_ts = datetime.fromisoformat(nested_hb.read_text(encoding="utf-8"))
    assert parsed_ts.tzinfo is not None
    assert verify_worker_heartbeat(nested_hb) is True

    future_ts = time.time() + 120.0
    nested_hb.touch()
    os.utime(nested_hb, (future_ts, future_ts))
    assert verify_worker_heartbeat(nested_hb) is False

    stale_ts = time.time() - 95.0
    os.utime(nested_hb, (stale_ts, stale_ts))
    assert verify_worker_heartbeat(nested_hb) is False
    assert verify_worker_heartbeat(nested_hb, max_age_seconds=120.0) is True

    ev_wait = asyncio.Event()
    await _esperar_o_detener(ev_wait, 0.005)
    assert not ev_wait.is_set()
    ev_wait.set()
    await _esperar_o_detener(ev_wait, 5.0)

    # 2. _is_task_healthy e is_supervisor_healthy
    async def _ok() -> None:
        return None

    async def _fail() -> None:
        raise RuntimeError("boom")

    async def _sleep_forever() -> None:
        await asyncio.sleep(10)

    t_opt_ok = asyncio.create_task(_ok(), name="media_avif_consumer")
    t_opt_err = asyncio.create_task(_fail(), name="media_avif_consumer")
    t_mand_ok = asyncio.create_task(_ok(), name="notifications_consumer")
    t_running = asyncio.create_task(_sleep_forever(), name="daily_tasks_scheduler")
    t_cancelled = asyncio.create_task(_sleep_forever(), name="cancelled_worker")
    t_cancelled.cancel()
    await asyncio.sleep(0)

    assert is_supervisor_healthy({"media_avif_consumer": t_opt_ok, "daily_tasks_scheduler": t_running}) is True
    assert is_supervisor_healthy({"media_avif_consumer": t_opt_err}) is False
    assert is_supervisor_healthy({"notifications_consumer": t_mand_ok}) is False
    assert is_supervisor_healthy({"cancelled_worker": t_cancelled}) is False

    t_running.cancel()
    await asyncio.gather(t_opt_ok, t_opt_err, t_mand_ok, t_running, t_cancelled, return_exceptions=True)

    # 3. Backoff exponencial en _loop_notificaciones, _loop_media_opcional y _loop_scheduler_diario
    espera_calls: list[float] = []

    async def _fake_esperar(stop_event: asyncio.Event, timeout_seconds: float) -> None:
        espera_calls.append(timeout_seconds)
        if len(espera_calls) >= 7:
            stop_event.set()

    class _BackoffRedis:
        def __init__(self) -> None:
            self.calls = 0
            self.stop_event: asyncio.Event | None = None

        async def blmove(
            self,
            src: str,
            dst: str,
            timeout: int,
            src_dir: str,
            dst_dir: str,
        ) -> None:
            del src, dst, timeout, src_dir, dst_dir
            self.calls += 1
            if self.calls <= 6:
                raise (RedisError("r"), OSError("o"), RuntimeError("rt"))[(self.calls - 1) % 3]
            if self.calls == 7:
                return None
            if self.calls == 8:
                raise RedisError("reset-check")
            if self.stop_event is not None:
                self.stop_event.set()
            return None

    backoff_cfg = WorkerSettings(media_enabled=True, poll_seconds=0.5, scheduler_interval_seconds=42.0)

    with monkeypatch.context() as mp_loops:
        mp_loops.setattr(worker_mod, "_esperar_o_detener", _fake_esperar)

        r_notif = _BackoffRedis()
        stop_n = asyncio.Event()
        r_notif.stop_event = stop_n
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="src.worker"):
            await _loop_notificaciones(backoff_cfg, stop_n, lambda: r_notif)
        assert espera_calls == [0.5, 1.0, 2.0, 4.0, 5.0, 5.0, 0.5]
        assert "Error transitorio en consumidor KeyDB de notificaciones:" in caplog.text

        espera_calls.clear()
        r_media = _BackoffRedis()
        stop_m = asyncio.Event()
        r_media.stop_event = stop_m
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="src.worker"):
            await _loop_media_opcional(backoff_cfg, stop_m, lambda: r_media)
        assert espera_calls == [0.5, 1.0, 2.0, 4.0, 5.0, 5.0, 0.5]
        assert "Error transitorio en cola de medios AVIF:" in caplog.text

        espera_calls.clear()
        stop_sched = asyncio.Event()

        async def _fake_esperar_once(stop_event: asyncio.Event, timeout_seconds: float) -> None:
            espera_calls.append(timeout_seconds)
            stop_event.set()

        mp_loops.setattr(worker_mod, "_esperar_o_detener", _fake_esperar_once)

        class _FailingSessionCtx:
            async def __aenter__(self) -> Any:
                raise SQLAlchemyError("db temporalmente caída")

            async def __aexit__(self, *args: object) -> None:
                return None

        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="src.worker"):
            await _loop_scheduler_diario(backoff_cfg, stop_sched, _FailingSessionCtx)
        assert espera_calls == [42.0]
        assert "Error transitorio generando tareas diarias:" in caplog.text

    # 4. _alcanzo_max_ticks, _supervisar_ciclo_worker no saludable y run_worker_orchestrator
    assert _alcanzo_max_ticks(0, None) is False
    assert _alcanzo_max_ticks(0, 1) is False
    assert _alcanzo_max_ticks(1, 1) is True
    assert _alcanzo_max_ticks(2, 1) is True

    dead_hb = tmp_path / "dead_hb"
    dead_hb.write_text("alive", encoding="utf-8")
    t_dead = asyncio.create_task(_fail(), name="notifications_consumer")
    await asyncio.sleep(0)
    caplog.clear()
    with caplog.at_level(logging.ERROR, logger="src.worker"):
        rc_unhealthy = await _supervisar_ciclo_worker(
            WorkerSettings(heartbeat_path=dead_hb, poll_seconds=0.01),
            asyncio.Event(),
            {"notifications_consumer": t_dead},
            max_ticks=2,
        )
    assert rc_unhealthy == 1
    assert not dead_hb.exists()
    assert "Supervisor worker detectó estado no saludable." in caplog.text
    await asyncio.gather(t_dead, return_exceptions=True)

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "inseguro")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        await run_worker_orchestrator()

    db_file = tmp_path / "hito21.db"
    orch_hb = tmp_path / "orch_hb"
    engine, factory = await _crear_sqlite_fk(tmp_path)

    class _IdleRedis:
        async def blmove(
            self,
            src: str,
            dst: str,
            timeout: int,
            src_dir: str,
            dst_dir: str,
        ) -> None:
            del src, dst, timeout, src_dir, dst_dir
            await asyncio.sleep(0)
            return None

    try:
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("SECRET_KEY", secrets.token_hex(32))
        monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_file}")
        monkeypatch.setenv("WORKER_HEARTBEAT_PATH", str(orch_hb))
        monkeypatch.setenv("WORKER_POLL_SECONDS", "0.005")
        monkeypatch.setenv("WORKER_MEDIA_ENABLED", "false")
        rc_orch = await run_worker_orchestrator(
            max_ticks=2,
            session_factory=factory,
            redis_getter=lambda: _IdleRedis(),
        )
        assert rc_orch == 0
        assert orch_hb.is_file()

        stop_sup = asyncio.Event()
        sup_tasks = _crear_tareas_supervisor(
            WorkerSettings(media_enabled=True, poll_seconds=0.01),
            stop_sup,
            factory,
            lambda: _IdleRedis(),
        )
        assert {k: t.get_name() for k, t in sup_tasks.items()} == {
            "daily_tasks_scheduler": "daily_tasks_scheduler",
            "notifications_consumer": "notifications_consumer",
            "media_avif_consumer": "media_avif_consumer",
        }
        stop_sup.set()
        await _cancelar_tareas(sup_tasks)
        assert all(t.done() for t in sup_tasks.values())
    finally:
        await engine.dispose()

    # 5. _run_with_signals (SIGINT/SIGTERM y fallback NotImplementedError)
    async def _fake_orch(*_args: Any, **_kwargs: Any) -> int:
        return 0

    loop = asyncio.get_running_loop()
    reg_signals: list[signal.Signals] = []
    monkeypatch.setattr(loop, "add_signal_handler", lambda sig, _cb: reg_signals.append(sig))
    monkeypatch.setattr(worker_mod, "run_worker_orchestrator", _fake_orch)
    assert await _run_with_signals(WorkerSettings(), 1) == 0
    assert reg_signals == [signal.SIGINT, signal.SIGTERM]

    def _no_signals(_sig: signal.Signals, _cb: Any) -> None:
        raise NotImplementedError

    monkeypatch.setattr(loop, "add_signal_handler", _no_signals)
    assert await _run_with_signals(WorkerSettings(), 1) == 0


def test_worker_shared_hooks_cli_main_sync(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Valida parser CLI, healthcheck por heartbeat y ejecución síncrona de main() sin loop activo."""
    parser = _build_cli_parser()
    assert parser.prog == "python -m src.worker"
    assert parser.parse_args([]).once is False
    assert parser.parse_args(["--once"]).once is True
    assert parser.parse_args(["--check-health"]).check_health is True

    cli_hb = tmp_path / "cli_hb"
    monkeypatch.setenv("WORKER_HEARTBEAT_PATH", str(cli_hb))
    monkeypatch.setenv("WORKER_HEARTBEAT_MAX_AGE_SECONDS", "5.0")
    assert main(["--check-health"]) == 1
    write_worker_heartbeat(cli_hb)
    assert main(["--check-health"]) == 0
    os.utime(cli_hb, (time.time() - 10.0, time.time() - 10.0))
    assert main(["--check-health"]) == 1

    run_calls: list[int | None] = []

    async def _fake_run_with_signals(_cfg: WorkerSettings, max_ticks: int | None) -> int:
        run_calls.append(max_ticks)
        return 0

    with monkeypatch.context() as mp_cli:
        mp_cli.setattr(worker_mod, "_run_with_signals", _fake_run_with_signals)
        assert main([]) == 0
        assert main(["--once"]) == 0
    assert run_calls == [None, 1]
