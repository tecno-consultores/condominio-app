# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
"""Pruebas HTTP E2E y de concurrencia real (asyncio.gather) sobre PostgreSQL 17 + KeyDB."""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
import redis.asyncio as aioredis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database import get_db
from src.main import app
from src.models import (
    AreaSocial,
    AuditoriaRecibo,
    ConsultaComunitaria,
    ContratoOcupacion,
    Estructura,
    OpcionConsulta,
    PagoReportado,
    Recibo,
    ReservaAreaSocial,
    TasaCambio,
    Unidad,
    Usuario,
    VotoConsulta,
)
from src.redis_client import get_redis_client
from src.security import get_password_hash


def _require_pg_and_redis() -> tuple[str, str]:
    pg_url = os.getenv("POSTGRES_TEST_URL", "").strip()
    if not pg_url:
        pytest.skip("Requiere POSTGRES_TEST_URL apuntando a PostgreSQL 17 con Alembic aplicado.")
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0").strip()
    return pg_url, redis_url


async def _limpiar_escenario_pg17(
    factory: async_sessionmaker[AsyncSession],
    ids: dict[str, int | bool],
) -> None:
    """Elimina en orden estricto de FK los registros sembrados para esta corrida."""
    async with factory() as s_clean:
        s_clean.sync_session.info["disable_runtime_role"] = True
        s_clean.sync_session.info["is_superadmin"] = True
        recibo_id = int(ids["recibo_id"])
        consulta_id = int(ids["consulta_id"])
        area_id = int(ids["area_id"])

        await s_clean.execute(text("DELETE FROM auditoria_recibos WHERE recibo_id = :rid"), {"rid": recibo_id})
        await s_clean.execute(text("DELETE FROM pagos_reportados WHERE recibo_id = :rid"), {"rid": recibo_id})
        await s_clean.execute(text("DELETE FROM votos_consulta WHERE consulta_id = :cid"), {"cid": consulta_id})
        await s_clean.execute(text("DELETE FROM opciones_consulta WHERE consulta_id = :cid"), {"cid": consulta_id})
        await s_clean.execute(text("DELETE FROM consultas_comunitarias WHERE id = :cid"), {"cid": consulta_id})

        tarea_rows = (
            (
                await s_clean.execute(
                    text("SELECT tarea_inspeccion_id FROM reservas_areas_sociales WHERE area_id = :aid"),
                    {"aid": area_id},
                )
            )
            .scalars()
            .all()
        )
        await s_clean.execute(text("DELETE FROM reservas_areas_sociales WHERE area_id = :aid"), {"aid": area_id})
        for tid in tarea_rows:
            if tid is not None:
                await s_clean.execute(text("DELETE FROM tareas_diarias WHERE id = :tid"), {"tid": int(tid)})
        await s_clean.execute(text("DELETE FROM areas_sociales WHERE id = :aid"), {"aid": area_id})

        await s_clean.execute(
            text("DELETE FROM contratos_ocupacion WHERE unidad_id = :uid"),
            {"uid": int(ids["unidad_id"])},
        )
        await s_clean.execute(text("DELETE FROM recibos WHERE id = :rid"), {"rid": recibo_id})
        if bool(ids.get("created_tasa")):
            await s_clean.execute(
                text("DELETE FROM tasas_cambio WHERE id = :tid"),
                {"tid": int(ids["tasa_id"])},
            )
        await s_clean.execute(
            text("DELETE FROM usuarios WHERE id IN (:u1, :u2)"),
            {"u1": int(ids["tesorero_id"]), "u2": int(ids["propietario_id"])},
        )
        await s_clean.execute(text("DELETE FROM unidades WHERE id = :uid"), {"uid": int(ids["unidad_id"])})
        await s_clean.execute(text("DELETE FROM estructuras WHERE id = :eid"), {"eid": int(ids["estructura_id"])})
        await s_clean.commit()


@pytest.mark.asyncio
async def test_pg17_http_login_concurrencia_e_idempotencia() -> None:
    """Valida flujos HTTP reales con PostgreSQL 17 + KeyDB bajo concurrencia ``asyncio.gather``."""
    pg_url, redis_url = _require_pg_and_redis()
    engine = create_async_engine(pg_url, echo=False, pool_size=10, max_overflow=10)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    redis_conn = aioredis.from_url(redis_url, decode_responses=True)
    assert await redis_conn.ping() is True

    sufijo = uuid.uuid4().hex[:8]
    clave_plana = f"Pg17Real!{sufijo}"
    pw_hash = get_password_hash(clave_plana)
    ahora = datetime.now(UTC)
    periodo_unico = f"209{int(sufijo[0], 16) % 9}-{(int(sufijo[1], 16) % 12) + 1:02d}"
    ids: dict[str, int | bool] = {"created_tasa": False, "tasa_id": 0}

    try:
        async with factory() as s:
            s.sync_session.info["tenant_id"] = "1"
            s.sync_session.info["is_superadmin"] = True

            tasa_hoy = (
                (
                    await s.execute(
                        select(TasaCambio).where(TasaCambio.condominio_id == 1, TasaCambio.fecha == date.today())
                    )
                )
                .scalars()
                .first()
            )
            if tasa_hoy is None:
                tasa_nueva = TasaCambio(condominio_id=1, fecha=date.today(), tasa_usd_ves=Decimal("45.0000"))
                s.add(tasa_nueva)
                await s.flush()
                ids["created_tasa"] = True
                ids["tasa_id"] = tasa_nueva.id

            torre = Estructura(condominio_id=1, nombre=f"Torre-PG17-{sufijo}", tipo="TORRE")
            s.add(torre)
            await s.flush()

            unidad = Unidad(
                condominio_id=1,
                identificador=f"PG17-{sufijo[:6]}",
                estructura_id=torre.id,
                alicuota=Decimal("50.0000"),
            )
            s.add(unidad)
            await s.flush()

            tes_correo = f"tesorero.pg17.{sufijo}@condo.test"
            prop_correo = f"prop.pg17.{sufijo}@condo.test"
            tesorero = Usuario(
                condominio_id=1,
                nombre="Tesorero PG17",
                cedula=f"V-91{sufijo[:6]}",
                correo=tes_correo,
                telefono="+584149100001",
                password_hash=pw_hash,
                es_activo=True,
                rol="TESORERO",
            )
            propietario = Usuario(
                condominio_id=1,
                nombre="Propietario PG17",
                cedula=f"V-92{sufijo[:6]}",
                correo=prop_correo,
                telefono="+584149100002",
                password_hash=pw_hash,
                es_activo=True,
                rol="PROPIETARIO",
            )
            s.add_all([tesorero, propietario])
            await s.flush()

            s.add(
                ContratoOcupacion(
                    condominio_id=1,
                    usuario_id=propietario.id,
                    unidad_id=unidad.id,
                    tipo_ocupante="PROPIETARIO",
                    es_activo=True,
                    puede_votar_asamblea=True,
                )
            )

            recibo = Recibo(
                condominio_id=1,
                unidad_id=unidad.id,
                periodo=periodo_unico,
                monto_usd=Decimal("100.00"),
                monto_pagado_usd=Decimal("0.00"),
                estado="PENDIENTE",
                bloqueado=False,
            )
            s.add(recibo)
            await s.flush()

            pago = PagoReportado(
                condominio_id=1,
                recibo_id=recibo.id,
                usuario_id=propietario.id,
                monto=Decimal("100.00"),
                moneda="USD",
                monto_usd=Decimal("100.00"),
                tasa_cambio=Decimal("45.0000"),
                metodo_pago="TRANSFERENCIA",
                numero_referencia=f"REF-PG17-{sufijo}",
                estado="EN_REVISION",
            )
            s.add(pago)

            consulta = ConsultaComunitaria(
                condominio_id=1,
                titulo=f"Consulta PG17 {sufijo}",
                descripcion_legal="Votación concurrente bajo aislamiento PostgreSQL 17 RLS",
                tipo_consulta="CARTA_CONSULTA_1RA",
                regla_quorum="DOS_TERCIOS",
                quorum_minimo_alicuota=Decimal("50.0000"),
                fecha_cierre=ahora + timedelta(days=5),
                estado="ABIERTA",
                creada_por_id=tesorero.id,
            )
            s.add(consulta)
            await s.flush()

            opcion = OpcionConsulta(
                condominio_id=1,
                consulta_id=consulta.id,
                etiqueta="Aprobar",
                es_opcion_aprobatoria=True,
            )
            s.add(opcion)

            area = AreaSocial(
                condominio_id=1,
                nombre=f"Caney PG17 {sufijo}",
                aforo_maximo=25,
                costo_uso_usd=Decimal("0.00"),
                deposito_garantia_usd=Decimal("0.00"),
                requiere_solvencia_estricta=True,
            )
            s.add(area)
            await s.flush()

            ids.update(
                {
                    "estructura_id": torre.id,
                    "unidad_id": unidad.id,
                    "tesorero_id": tesorero.id,
                    "propietario_id": propietario.id,
                    "recibo_id": recibo.id,
                    "pago_id": pago.id,
                    "consulta_id": consulta.id,
                    "opcion_id": opcion.id,
                    "area_id": area.id,
                }
            )
            await s.commit()

        async def _override_pg_db() -> AsyncIterator[AsyncSession]:
            async with factory() as session:
                session.sync_session.info.setdefault("tenant_id", "")
                yield session

        app.dependency_overrides[get_db] = _override_pg_db
        app.dependency_overrides[get_redis_client] = lambda: redis_conn

        async with (
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client_tes,
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client_prop,
        ):
            r_login_tes = await client_tes.post(
                "/api/auth/login",
                json={"correo": tes_correo, "password": clave_plana},
            )
            assert r_login_tes.status_code == 200
            csrf_tes = r_login_tes.json()["csrf_token"]

            r_login_prop = await client_prop.post(
                "/api/auth/login",
                json={"correo": prop_correo, "password": clave_plana},
            )
            assert r_login_prop.status_code == 200
            csrf_prop = r_login_prop.json()["csrf_token"]

            r_me = await client_prop.get("/api/auth/me")
            assert r_me.status_code == 200
            assert r_me.json()["rol"] == "PROPIETARIO"

            # Carrera 1: Aprobación simultánea del mismo pago (FOR UPDATE + estado EN_REVISION)
            resps_pago = await asyncio.gather(
                client_tes.put(
                    f"/api/pagos/{ids['pago_id']}/aprobar",
                    headers={"Idempotency-Key": str(uuid.uuid4()), "X-CSRF-Token": csrf_tes},
                ),
                client_tes.put(
                    f"/api/pagos/{ids['pago_id']}/aprobar",
                    headers={"Idempotency-Key": str(uuid.uuid4()), "X-CSRF-Token": csrf_tes},
                ),
            )
            assert sorted(r.status_code for r in resps_pago) == [200, 409]

            # Carrera 2: Doble voto concurrente de la misma unidad en PG17 (uq_voto_consulta_unidad)
            resps_voto = await asyncio.gather(
                client_prop.post(
                    f"/api/consultas/{ids['consulta_id']}/votar",
                    json={"unidad_id": ids["unidad_id"], "opcion_id": ids["opcion_id"]},
                    headers={"Idempotency-Key": str(uuid.uuid4()), "X-CSRF-Token": csrf_prop},
                ),
                client_prop.post(
                    f"/api/consultas/{ids['consulta_id']}/votar",
                    json={"unidad_id": ids["unidad_id"], "opcion_id": ids["opcion_id"]},
                    headers={"Idempotency-Key": str(uuid.uuid4()), "X-CSRF-Token": csrf_prop},
                ),
            )
            assert sorted(r.status_code for r in resps_voto) == [201, 409]

            # Carrera 3: Doble reserva concurrente en la misma fecha/área (uq_reserva_area_fecha_activa)
            fecha_reserva = (date.today() + timedelta(days=30)).isoformat()
            idem_reserva = str(uuid.uuid4())
            resps_reserva = await asyncio.gather(
                client_prop.post(
                    "/api/reservas/solicitar",
                    json={
                        "area_id": ids["area_id"],
                        "unidad_id": ids["unidad_id"],
                        "fecha_evento": fecha_reserva,
                        "motivo_evento": "Reunión vecinal concurrente PG17",
                    },
                    headers={"Idempotency-Key": idem_reserva, "X-CSRF-Token": csrf_prop},
                ),
                client_prop.post(
                    "/api/reservas/solicitar",
                    json={
                        "area_id": ids["area_id"],
                        "unidad_id": ids["unidad_id"],
                        "fecha_evento": fecha_reserva,
                        "motivo_evento": "Reunión vecinal concurrente PG17",
                    },
                    headers={"Idempotency-Key": str(uuid.uuid4()), "X-CSRF-Token": csrf_prop},
                ),
            )
            assert sorted(r.status_code for r in resps_reserva) == [201, 409]

            # Verificación de replay idempotente real contra KeyDB si el primer slot ganó
            r_replay = await client_prop.post(
                "/api/reservas/solicitar",
                json={
                    "area_id": ids["area_id"],
                    "unidad_id": ids["unidad_id"],
                    "fecha_evento": fecha_reserva,
                    "motivo_evento": "Reunión vecinal concurrente PG17",
                },
                headers={"Idempotency-Key": idem_reserva, "X-CSRF-Token": csrf_prop},
            )
            assert r_replay.status_code in (201, 409)

        async with factory() as s_verif:
            s_verif.sync_session.info["tenant_id"] = "1"
            rec_db = (await s_verif.execute(select(Recibo).where(Recibo.id == int(ids["recibo_id"])))).scalar_one()
            assert rec_db.monto_pagado_usd == Decimal("100.00")
            assert rec_db.estado == "PAGADO"

            uni_db = (await s_verif.execute(select(Unidad).where(Unidad.id == int(ids["unidad_id"])))).scalar_one()
            assert uni_db.credito_disponible_usd == Decimal("0.00")

            aud_count = len(
                (
                    await s_verif.execute(
                        select(AuditoriaRecibo).where(AuditoriaRecibo.recibo_id == int(ids["recibo_id"]))
                    )
                )
                .scalars()
                .all()
            )
            assert aud_count == 1

            votos_count = len(
                (await s_verif.execute(select(VotoConsulta).where(VotoConsulta.consulta_id == int(ids["consulta_id"]))))
                .scalars()
                .all()
            )
            assert votos_count == 1

            reservas_count = len(
                (
                    await s_verif.execute(
                        select(ReservaAreaSocial).where(ReservaAreaSocial.area_id == int(ids["area_id"]))
                    )
                )
                .scalars()
                .all()
            )
            assert reservas_count == 1
    finally:
        app.dependency_overrides.clear()
        if "estructura_id" in ids:
            await _limpiar_escenario_pg17(factory, ids)
        await redis_conn.aclose()
        await engine.dispose()
