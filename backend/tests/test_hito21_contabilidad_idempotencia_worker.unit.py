"""Pruebas Nivel 11X del Hito 21: Exactitud Contable LPH, Idempotencia con Replay y Worker Productivo."""

from __future__ import annotations

import asyncio
import base64
import importlib.util
import json
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from pydantic import ValidationError
from redis.exceptions import RedisError
from sqlalchemy import event, select
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
from src.security import get_password_hash, get_qr_signing_key
from src.worker import (
    _MEDIA_DLQ,
    _MEDIA_PROCESSING,
    _MEDIA_QUEUE,
    _NOTIFICATIONS_DLQ,
    _NOTIFICATIONS_PROCESSING,
    _NOTIFICATIONS_QUEUE,
    MAX_DLQ_ITEMS,
    MAX_IMAGE_PIXELS,
    WorkerSettings,
    _consumir_cola_media_tick,
    _consumir_cola_notificaciones_tick,
    _loop_media_opcional,
    codificar_imagen_avif,
    encolar_tarea_media,
    generar_tareas_diarias_desde_plantillas,
    procesar_mensaje_media,
    procesar_mensaje_notificacion,
    subir_objeto_minio_s3,
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
