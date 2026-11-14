"""Pruebas de integración SQLite y PostgreSQL 17 RLS para Hito 17.4."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.database import Base, apply_rls_session_settings, get_db
from src.dependencies import get_current_user
from src.main import app
from src.models import (
    AreaSocial,
    AuditoriaRecibo,
    BitacoraActa,
    ConsultaComunitaria,
    ContratoOcupacion,
    Estructura,
    OpcionConsulta,
    Recibo,
    ReciboItem,
    TasaCambio,
    TareaDiaria,
    Unidad,
    Usuario,
    VotoConsulta,
)
from src.redis_client import get_redis_client
from src.security import get_password_hash


def _idem_headers() -> dict[str, str]:
    return {"Idempotency-Key": str(uuid.uuid4())}


async def _crear_motor_sqlite(tmp_path: Path) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    db_file = tmp_path / "hito17_4.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


async def _sembrar_datos_base(factory: async_sessionmaker[AsyncSession]) -> dict[str, int]:
    pw = get_password_hash("Password123!")
    ahora = datetime.now(UTC)
    async with factory() as s:
        est = Estructura(nombre="Torre Hito17", tipo="TORRE")
        s.add(est)
        await s.flush()

        u1 = Unidad(identificador="H17-01", estructura_id=est.id, alicuota=Decimal("60.0000"))
        u2 = Unidad(identificador="H17-02", estructura_id=est.id, alicuota=Decimal("40.0000"))
        s.add_all([u1, u2])
        await s.flush()

        tesorero = Usuario(
            nombre="Presidente H17",
            cedula="V-17400001",
            correo="tesorero.h17@test.com",
            telefono="+584141740001",
            password_hash=pw,
            es_activo=True,
            rol="PRESIDENTE",
        )
        prop1 = Usuario(
            nombre="Propietario Uno",
            cedula="V-17400002",
            correo="prop1.h17@test.com",
            telefono="+584141740002",
            password_hash=pw,
            es_activo=True,
            rol="PROPIETARIO",
        )
        prop2 = Usuario(
            nombre="Propietario Dos",
            cedula="V-17400003",
            correo="prop2.h17@test.com",
            telefono="+584141740003",
            password_hash=pw,
            es_activo=True,
            rol="PROPIETARIO",
        )
        inquilino = Usuario(
            nombre="Inquilino Sin Propiedad",
            cedula="V-17400004",
            correo="inq.h17@test.com",
            telefono="+584141740004",
            password_hash=pw,
            es_activo=False,
            rol="FANTASMA",
        )
        expirado = Usuario(
            nombre="ExPropietario Contrato Cerrado",
            cedula="V-17400005",
            correo="ex.h17@test.com",
            telefono="+584141740005",
            password_hash=pw,
            es_activo=True,
            rol="PROPIETARIO",
        )
        fantasma = Usuario(
            nombre="Fantasma Publico",
            cedula="V-17400006",
            correo="fantasma.h17@test.com",
            telefono="+584141740006",
            password_hash=pw,
            es_activo=False,
            rol="FANTASMA",
        )
        s.add_all([tesorero, prop1, prop2, inquilino, expirado, fantasma])
        await s.flush()

        s.add_all(
            [
                ContratoOcupacion(
                    usuario_id=tesorero.id,
                    unidad_id=u1.id,
                    tipo_ocupante="PROPIETARIO",
                    es_activo=True,
                    puede_votar_asamblea=True,
                ),
                ContratoOcupacion(
                    usuario_id=prop1.id,
                    unidad_id=u1.id,
                    tipo_ocupante="PROPIETARIO",
                    es_activo=True,
                    puede_votar_asamblea=True,
                ),
                ContratoOcupacion(
                    usuario_id=prop2.id,
                    unidad_id=u2.id,
                    tipo_ocupante="PROPIETARIO",
                    es_activo=True,
                    puede_votar_asamblea=True,
                ),
                ContratoOcupacion(
                    usuario_id=expirado.id,
                    unidad_id=u2.id,
                    tipo_ocupante="PROPIETARIO",
                    es_activo=True,
                    puede_votar_asamblea=True,
                    fecha_fin=ahora - timedelta(days=2),
                ),
                TasaCambio(fecha=date.today(), tasa_usd_ves=Decimal("40.0000")),
            ]
        )

        c_exp = ConsultaComunitaria(
            titulo="Consulta Expirada",
            descripcion_legal="Consulta fuera de plazo",
            tipo_consulta="CARTA_CONSULTA_1RA",
            regla_quorum="DOS_TERCIOS",
            quorum_minimo_alicuota=Decimal("66.6700"),
            fecha_apertura=ahora - timedelta(days=5),
            fecha_cierre=ahora - timedelta(minutes=10),
            estado="ABIERTA",
            creada_por_id=tesorero.id,
        )
        c_ok = ConsultaComunitaria(
            titulo="Consulta Vigente JTI",
            descripcion_legal="Aprobación de portón",
            tipo_consulta="CARTA_CONSULTA_1RA",
            regla_quorum="DOS_TERCIOS",
            quorum_minimo_alicuota=Decimal("66.6700"),
            fecha_apertura=ahora - timedelta(hours=1),
            fecha_cierre=ahora + timedelta(days=2),
            estado="ABIERTA",
            creada_por_id=tesorero.id,
        )
        s.add_all([c_exp, c_ok])
        await s.flush()

        op_exp = OpcionConsulta(consulta_id=c_exp.id, etiqueta="Sí", es_opcion_aprobatoria=True)
        op_ok = OpcionConsulta(consulta_id=c_ok.id, etiqueta="Aprobar", es_opcion_aprobatoria=True)
        area_pago = AreaSocial(
            nombre="Salón Imperial H17",
            aforo_maximo=60,
            costo_uso_usd=Decimal("25.00"),
            deposito_garantia_usd=Decimal("100.00"),
            requiere_solvencia_estricta=True,
            es_activa=True,
        )
        area_libre = AreaSocial(
            nombre="Caney Libre H17",
            aforo_maximo=30,
            costo_uso_usd=Decimal("0.00"),
            deposito_garantia_usd=Decimal("0.00"),
            requiere_solvencia_estricta=False,
            es_activa=True,
        )
        s.add_all([op_exp, op_ok, area_pago, area_libre])
        await s.commit()
        return {
            "u1": u1.id,
            "u2": u2.id,
            "tesorero": tesorero.id,
            "prop1": prop1.id,
            "prop2": prop2.id,
            "inquilino": inquilino.id,
            "expirado": expirado.id,
            "fantasma": fantasma.id,
            "c_exp": c_exp.id,
            "op_exp": op_exp.id,
            "c_ok": c_ok.id,
            "op_ok": op_ok.id,
            "area_pago": area_pago.id,
            "area_libre": area_libre.id,
        }


async def _cargar_usuario(factory: async_sessionmaker[AsyncSession], uid: int) -> Usuario:
    async with factory() as s:
        user = await s.get(Usuario, uid)
        assert user is not None
        return user


@pytest.mark.asyncio
async def test_consultas_jti_cierre_y_solvencia_dinamica_hito17_4(tmp_path: Path) -> None:
    engine, factory = await _crear_motor_sqlite(tmp_path)
    ids = await _sembrar_datos_base(factory)

    async def _override_db() -> AsyncIterator[AsyncSession]:
        async with factory() as s:
            yield s

    mock_redis = AsyncMock()
    mock_redis.set.return_value = True
    tesorero = await _cargar_usuario(factory, ids["tesorero"])
    prop1 = await _cargar_usuario(factory, ids["prop1"])

    try:
        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_redis_client] = lambda: mock_redis

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            app.dependency_overrides[get_current_user] = lambda: prop1

            # 1. Consulta con fecha_cierre vencida rechaza voto con 409
            resp_exp = await client.post(
                f"/api/consultas/{ids['c_exp']}/votar",
                headers=_idem_headers(),
                json={"unidad_id": ids["u1"], "opcion_id": ids["op_exp"]},
            )
            assert resp_exp.status_code == 409

            # 2. Voto en consulta vigente persiste UUID jti en VotoConsulta y detalle
            resp_voto = await client.post(
                f"/api/consultas/{ids['c_ok']}/votar",
                headers=_idem_headers(),
                json={"unidad_id": ids["u1"], "opcion_id": ids["op_ok"]},
            )
            assert resp_voto.status_code == 201
            recibo_voto = resp_voto.json()
            assert str(uuid.UUID(recibo_voto["jti"])) == recibo_voto["jti"]

            resp_det = await client.get(f"/api/consultas/{ids['c_ok']}")
            assert resp_det.status_code == 200
            assert resp_det.json()["mi_voto"]["jti"] == recibo_voto["jti"]

            async with factory() as s:
                voto_db = (
                    await s.execute(select(VotoConsulta).where(VotoConsulta.id == recibo_voto["voto_id"]))
                ).scalar_one()
                assert voto_db.jti == recibo_voto["jti"]

            # 3. Cierre atómico genera 1 sola acta y segunda llamada falla con 409 sin duplicar acta
            app.dependency_overrides[get_current_user] = lambda: tesorero
            resp_cierre = await client.post(f"/api/consultas/{ids['c_ok']}/cerrar", headers=_idem_headers())
            assert resp_cierre.status_code == 200
            assert resp_cierre.json()["estado"].startswith("CERRADA")

            resp_cierre_dup = await client.post(f"/api/consultas/{ids['c_ok']}/cerrar", headers=_idem_headers())
            assert resp_cierre_dup.status_code == 409

            async with factory() as s:
                total_actas = (await s.execute(select(func.count(BitacoraActa.id)))).scalar_one()
                assert total_actas == 1

            # 4. Solvencia: jti UUIDv4 + verificación live cae a vigente=False al nacer deuda viva
            resp_solv = await client.post(f"/api/finanzas/solvencia/{ids['u1']}", headers=_idem_headers())
            assert resp_solv.status_code == 201
            cert = resp_solv.json()
            assert str(uuid.UUID(cert["jti"])) == cert["jti"]

            resp_ver_ok = await client.get(
                f"/api/finanzas/solvencia/verificar/{cert['folio']}",
                params={"sig": cert["firma_hmac"]},
            )
            assert resp_ver_ok.status_code == 200
            assert resp_ver_ok.json()["vigente"] is True
            assert resp_ver_ok.json()["jti"] == cert["jti"]

            async with factory() as s:
                s.add(
                    Recibo(
                        unidad_id=ids["u1"],
                        periodo="2026-12",
                        monto_usd=Decimal("50.00"),
                        monto_pagado_usd=Decimal("0.00"),
                        estado="PENDIENTE",
                    )
                )
                await s.commit()

            resp_ver_mora = await client.get(
                f"/api/finanzas/solvencia/verificar/{cert['folio']}",
                params={"sig": cert["firma_hmac"]},
            )
            assert resp_ver_mora.status_code == 200
            assert resp_ver_mora.json()["vigente"] is False
    finally:
        app.dependency_overrides = {}
        await engine.dispose()


@pytest.mark.asyncio
async def test_reservas_indice_parcial_cancelacion_y_cargo_danos_hito17_4(tmp_path: Path) -> None:
    engine, factory = await _crear_motor_sqlite(tmp_path)
    ids = await _sembrar_datos_base(factory)

    async def _override_db() -> AsyncIterator[AsyncSession]:
        async with factory() as s:
            yield s

    mock_redis = AsyncMock()
    mock_redis.set.return_value = True
    tesorero = await _cargar_usuario(factory, ids["tesorero"])
    prop1 = await _cargar_usuario(factory, ids["prop1"])
    prop2 = await _cargar_usuario(factory, ids["prop2"])
    fecha_reserva = (date.today() + timedelta(days=20)).isoformat()

    try:
        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_redis_client] = lambda: mock_redis

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            app.dependency_overrides[get_current_user] = lambda: prop2
            res1 = await client.post(
                "/api/reservas/solicitar",
                headers=_idem_headers(),
                json={
                    "area_id": ids["area_pago"],
                    "unidad_id": ids["u2"],
                    "fecha_evento": fecha_reserva,
                    "motivo_evento": "Celebración familiar vecinal",
                },
            )
            assert res1.status_code == 201
            r1 = res1.json()
            assert r1["estado"] == "CONFIRMADA"
            assert r1["tarea_inspeccion_id"] is not None

            # Reserva duplicada en fecha ocupada -> 409
            res_dup = await client.post(
                "/api/reservas/solicitar",
                headers=_idem_headers(),
                json={
                    "area_id": ids["area_pago"],
                    "unidad_id": ids["u2"],
                    "fecha_evento": fecha_reserva,
                    "motivo_evento": "Segundo intento misma fecha",
                },
            )
            assert res_dup.status_code == 409

            # Vecino ajeno intentando cancelar -> 403
            app.dependency_overrides[get_current_user] = lambda: prop1
            res_forb = await client.put(f"/api/reservas/{r1['id']}/cancelar", headers=_idem_headers())
            assert res_forb.status_code == 403

            # Solicitante cancela -> 200 CANCELADA y completa tarea de inspección
            app.dependency_overrides[get_current_user] = lambda: prop2
            res_cancel = await client.put(f"/api/reservas/{r1['id']}/cancelar", headers=_idem_headers())
            assert res_cancel.status_code == 200
            assert res_cancel.json()["estado"] == "CANCELADA"

            async with factory() as s:
                tarea_db = await s.get(TareaDiaria, r1["tarea_inspeccion_id"])
                assert tarea_db is not None
                assert tarea_db.completada is True

            # Re-cancelar una reserva cancelada -> 409
            res_cancel_dup = await client.put(f"/api/reservas/{r1['id']}/cancelar", headers=_idem_headers())
            assert res_cancel_dup.status_code == 409

            # Índice único parcial uq_reserva_area_fecha_activa permite re-reservar tras CANCELADA
            res2 = await client.post(
                "/api/reservas/solicitar",
                headers=_idem_headers(),
                json={
                    "area_id": ids["area_pago"],
                    "unidad_id": ids["u2"],
                    "fecha_evento": fecha_reserva,
                    "motivo_evento": "Nueva reserva tras liberación",
                },
            )
            assert res2.status_code == 201
            r2 = res2.json()

            # Inspección FINALIZADA_CON_DANOS genera Recibo + ReciboItem + AuditoriaRecibo cuando deposito > 0
            app.dependency_overrides[get_current_user] = lambda: tesorero
            res_insp = await client.put(
                f"/api/reservas/{r2['id']}/inspeccionar",
                headers=_idem_headers(),
                json={
                    "estado": "FINALIZADA_CON_DANOS",
                    "observaciones_inspeccion": "Sillas rotas y daño en iluminación",
                },
            )
            assert res_insp.status_code == 200
            assert res_insp.json()["estado"] == "FINALIZADA_CON_DANOS"

            async with factory() as s:
                recibos = list((await s.execute(select(Recibo).where(Recibo.unidad_id == ids["u2"]))).scalars().all())
                assert len(recibos) == 1
                assert recibos[0].estado == "PENDIENTE"
                assert recibos[0].monto_usd == Decimal("100.00")

                items = list((await s.execute(select(ReciboItem))).scalars().all())
                assert len(items) == 1
                assert items[0].tipo_item == "DANOS_AREA_SOCIAL"

                auditorias = list((await s.execute(select(AuditoriaRecibo))).scalars().all())
                assert len(auditorias) == 1
                assert auditorias[0].estado_viejo == "INEXISTENTE"
                assert auditorias[0].estado_nuevo == "PENDIENTE"
                assert "depósito por daños en reserva" in auditorias[0].motivo

            # Área con deposito_garantia_usd == 0 no genera recibo adicional al reportar daños
            res_libre = await client.post(
                "/api/reservas/solicitar",
                headers=_idem_headers(),
                json={
                    "area_id": ids["area_libre"],
                    "unidad_id": ids["u1"],
                    "fecha_evento": fecha_reserva,
                    "motivo_evento": "Reunión comité",
                },
            )
            assert res_libre.status_code == 201
            r_libre_id = res_libre.json()["id"]

            res_insp_libre = await client.put(
                f"/api/reservas/{r_libre_id}/inspeccionar",
                headers=_idem_headers(),
                json={
                    "estado": "FINALIZADA_CON_DANOS",
                    "observaciones_inspeccion": "Suciedad menor sin depósito",
                },
            )
            assert res_insp_libre.status_code == 200
            async with factory() as s:
                stmt_u1 = select(Recibo).where(Recibo.unidad_id == ids["u1"])
                recibos_u1 = list((await s.execute(stmt_u1)).scalars().all())
                assert recibos_u1 == []
    finally:
        app.dependency_overrides = {}
        await engine.dispose()


@pytest.mark.asyncio
async def test_administracion_privacidad_historico_contratos_y_lph_hito17_4(tmp_path: Path) -> None:
    engine, factory = await _crear_motor_sqlite(tmp_path)
    ids = await _sembrar_datos_base(factory)

    async def _override_db() -> AsyncIterator[AsyncSession]:
        async with factory() as s:
            yield s

    mock_redis = AsyncMock()
    mock_redis.set.return_value = True
    tesorero = await _cargar_usuario(factory, ids["tesorero"])
    prop2 = await _cargar_usuario(factory, ids["prop2"])
    fantasma = await _cargar_usuario(factory, ids["fantasma"])

    try:
        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_redis_client] = lambda: mock_redis

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1a. Anónimo recibe UnidadPublicaResponse (sin alicuota, cuota_fija_usd ni credito_disponible_usd)
            app.dependency_overrides.pop(get_current_user, None)
            res_anon = await client.get("/api/estructura/unidades")
            assert res_anon.status_code == 200
            for item in res_anon.json():
                assert set(item.keys()) == {"id", "identificador", "estructura_id"}

            # 1b. Usuario Fantasma recibe UnidadPublicaResponse
            app.dependency_overrides[get_current_user] = lambda: fantasma
            res_ghost = await client.get("/api/estructura/unidades")
            assert res_ghost.status_code == 200
            for item in res_ghost.json():
                assert set(item.keys()) == {"id", "identificador", "estructura_id"}

            # 1c. Usuario activo recibe UnidadResponse completo
            app.dependency_overrides[get_current_user] = lambda: prop2
            res_act = await client.get("/api/estructura/unidades")
            assert res_act.status_code == 200
            campos_privados = {
                "id",
                "identificador",
                "estructura_id",
                "alicuota",
                "cuota_fija_usd",
                "credito_disponible_usd",
            }
            for item in res_act.json():
                assert campos_privados <= set(item.keys())

            # 2. Reasignar unidad preserva histórico (contrato previo es_activo=False, fecha_fin != None)
            app.dependency_overrides[get_current_user] = lambda: tesorero
            res_reasignar = await client.put(
                f"/api/usuarios/{ids['prop2']}/asignar",
                headers=_idem_headers(),
                json={"unidad_id": ids["u1"], "tipo_ocupante": "PROPIETARIO", "rol": "PROPIETARIO"},
            )
            assert res_reasignar.status_code == 200

            async with factory() as s:
                contratos = list(
                    (
                        await s.execute(
                            select(ContratoOcupacion)
                            .where(ContratoOcupacion.usuario_id == ids["prop2"])
                            .order_by(ContratoOcupacion.id.asc())
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(contratos) == 2
                assert contratos[0].unidad_id == ids["u2"]
                assert contratos[0].es_activo is False
                assert contratos[0].fecha_fin is not None
                assert contratos[1].unidad_id == ids["u1"]
                assert contratos[1].es_activo is True
                assert contratos[1].fecha_fin is None

            # 3. Regla LPH: asignar cargo de Junta a Inquilino sin contrato propietario activo -> 400
            res_inq_junta = await client.put(
                f"/api/usuarios/{ids['inquilino']}/asignar",
                headers=_idem_headers(),
                json={"unidad_id": ids["u2"], "tipo_ocupante": "INQUILINO", "rol": "TESORERO"},
            )
            assert res_inq_junta.status_code == 400

            # 4. PUT /api/junta/cargos rechaza contrato con fecha_fin vencida y acepta propietario vigente
            res_exp_cargo = await client.put(
                "/api/junta/cargos",
                headers=_idem_headers(),
                json={"usuario_id": ids["expirado"], "cargo": "SECRETARIO"},
            )
            assert res_exp_cargo.status_code == 400

            res_ok_cargo = await client.put(
                "/api/junta/cargos",
                headers=_idem_headers(),
                json={"usuario_id": ids["prop2"], "cargo": "SECRETARIO"},
            )
            assert res_ok_cargo.status_code == 200
            assert res_ok_cargo.json()["rol"] == "SECRETARIO"
    finally:
        app.dependency_overrides = {}
        await engine.dispose()


@pytest.mark.asyncio
async def test_postgresql_17_rls_27_tablas_y_aislamiento_multitenant() -> None:
    pg_url = os.getenv("POSTGRES_TEST_URL", "").strip()
    if not pg_url:
        pytest.skip("Requiere POSTGRES_TEST_URL apuntando a PostgreSQL 17 con Alembic aplicado.")

    engine = create_async_engine(pg_url, echo=False)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    sufijo = uuid.uuid4().hex[:8]
    est1_id = 0
    est2_id = 0

    try:
        # 1. Auditoría de catálogo pg_class / pg_namespace para las 27 tablas del modelo ORM
        async with factory() as s:
            s.sync_session.info["is_superadmin"] = True
            expected_tables = set(Base.metadata.tables.keys())
            assert len(expected_tables) == 27

            rows = (
                await s.execute(
                    text(
                        """
                        SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
                        FROM pg_catalog.pg_class c
                        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                        WHERE n.nspname = 'public' AND c.relkind = 'r'
                        """
                    )
                )
            ).all()
            pg_rls = {name: (bool(rls), bool(force)) for name, rls, force in rows}
            for table_name in expected_tables:
                assert table_name in pg_rls, f"Falta tabla {table_name} en PostgreSQL 17"
                assert pg_rls[table_name] == (True, True), f"RLS no forzado en {table_name}: {pg_rls[table_name]}"

        # 2. Sembrar estructuras aisladas en Tenant 1 y Tenant 2 bajo superadmin
        async with factory() as s:
            s.sync_session.info["is_superadmin"] = True
            s.sync_session.info["tenant_id"] = "1"
            e1 = Estructura(nombre=f"Torre T1 {sufijo}", tipo="TORRE", condominio_id=1)
            e2 = Estructura(nombre=f"Torre T2 {sufijo}", tipo="TORRE", condominio_id=2)
            s.add_all([e1, e2])
            await s.commit()
            est1_id = e1.id
            est2_id = e2.id

        # 3. Rol runtime sin privilegios BYPASSRLS ve exclusivamente su tenant
        async with factory() as s:
            s.sync_session.info["tenant_id"] = "1"
            s.sync_session.info["is_superadmin"] = False
            await s.execute(text("SET LOCAL ROLE condominio_app_runtime"))
            visibles_t1 = {row for row in (await s.execute(select(Estructura.id))).scalars().all()}
            assert est1_id in visibles_t1
            assert est2_id not in visibles_t1

            # Bloqueo de inserción cross-tenant con condominio_id=2
            s.add(Estructura(nombre=f"Intrusa {sufijo}", tipo="TORRE", condominio_id=2))
            with pytest.raises(DBAPIError):
                await s.commit()
            await s.rollback()

        async with factory() as s:
            s.sync_session.info["tenant_id"] = "2"
            s.sync_session.info["is_superadmin"] = False
            await s.execute(text("SET LOCAL ROLE condominio_app_runtime"))
            visibles_t2 = {row for row in (await s.execute(select(Estructura.id))).scalars().all()}
            assert est2_id in visibles_t2
            assert est1_id not in visibles_t2
            await s.rollback()

        # 4. Fail-closed sin tenant_id -> 0 filas visibles
        async with factory() as s:
            s.sync_session.info["tenant_id"] = ""
            s.sync_session.info["is_superadmin"] = False
            await s.execute(text("SET LOCAL ROLE condominio_app_runtime"))
            visibles_vacios = list((await s.execute(select(Estructura.id))).scalars().all())
            assert visibles_vacios == []
            await s.rollback()

        # 5. Superadmin ve ambos tenants
        async with factory() as s:
            s.sync_session.info["tenant_id"] = "1"
            s.sync_session.info["is_superadmin"] = True
            await s.execute(text("SET LOCAL ROLE condominio_app_runtime"))
            visibles_admin = {row for row in (await s.execute(select(Estructura.id))).scalars().all()}
            assert {est1_id, est2_id} <= visibles_admin
            await s.rollback()
    finally:
        if est1_id or est2_id:
            async with factory() as s:
                s.sync_session.info["is_superadmin"] = True
                for eid in (est1_id, est2_id):
                    if eid:
                        obj = await s.get(Estructura, eid)
                        if obj is not None:
                            await s.delete(obj)
                await s.commit()
        await engine.dispose()


def test_apply_rls_session_settings_postgresql_y_sqlite_noop() -> None:
    pg_conn = MagicMock()
    pg_conn.dialect.name = "postgresql"
    apply_rls_session_settings(pg_conn, "7", is_superadmin=True)
    apply_rls_session_settings(pg_conn, None, is_superadmin=False)
    assert pg_conn.execute.call_count == 2
    assert pg_conn.execute.call_args_list[0].args[1] == {"tid": "7", "sa": "true"}
    assert pg_conn.execute.call_args_list[1].args[1] == {"tid": "", "sa": "false"}

    sq_conn = MagicMock()
    sq_conn.dialect.name = "sqlite"
    apply_rls_session_settings(sq_conn, "1")
    sq_conn.execute.assert_not_called()
