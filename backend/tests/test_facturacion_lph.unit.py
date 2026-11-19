# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
"""Pruebas unitarias e integración SQLite FK para el motor de facturación mensual LPH."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.facturacion_lph import (
    _TIPOS_FACTURACION_MENSUAL,
    _ContextoAuditoriaLote,
    _EntradaLoteUnidad,
    _actualizar_fondo_reserva,
    _construir_items_recibo,
    _crear_recibo_e_items_unidad,
    _decimal_or_default,
    _fusionar_recibo_existente,
    _motivo_auditoria_lote,
    _obtener_id_recibo,
    _validar_fondo_ausente,
    calcular_cargos_modalidad,
    cargar_contexto_facturacion,
    persistir_lote_facturacion,
    verificar_periodo_facturable,
)
from src.finanzas import ErrorFinanciero
from src.models import (
    AuditoriaRecibo,
    Egreso,
    FondoCondominio,
    Recibo,
    ReciboItem,
    ReporteMensual,
    Unidad,
)
from src.schemas import FacturarPeriodoRequest
from src.security import compute_worm_record_hash
from tests._sqlite_helpers import create_sqlite_fk_factory, seed_condo_base


def _unidad_mem(
    unidad_id: int,
    alicuota: Decimal | None,
    cuota_fija: Decimal | None = None,
) -> Unidad:
    return Unidad(
        id=unidad_id,
        condominio_id=1,
        identificador=f"U-{unidad_id}",
        estructura_id=1,
        alicuota=cast(Decimal, alicuota),
        cuota_fija_usd=cuota_fija,
        credito_disponible_usd=Decimal("0.00"),
    )


def test_calcular_cargos_modalidad_alicuota_exacta_y_centavos() -> None:
    """Prorratea por alícuota con redondeo determinista a 2 decimales y ajuste de centavos."""
    unidades = [
        _unidad_mem(1, Decimal("33.3333")),
        _unidad_mem(2, Decimal("33.3333")),
        _unidad_mem(3, Decimal("33.3334")),
    ]
    datos = FacturarPeriodoRequest(
        periodo="2026-10",
        modalidad="ALICUOTA",
        incluir_fondo_reserva=True,
        cuota_extraordinaria_total_usd=Decimal("10.00"),
        descripcion_cuota_extraordinaria="Pintura fachada",
    )
    items, superavit = calcular_cargos_modalidad(
        datos,
        unidades,
        total_egresos_comunes=Decimal("100.01"),
        recargo_reserva_total=Decimal("10.00"),
    )
    assert superavit == Decimal("0.00")
    suma_gastos = sum(monto for u_items in items.values() for t, _, monto in u_items if t == "GASTO_COMUN")
    suma_reserva = sum(monto for u_items in items.values() for t, _, monto in u_items if t == "FONDO_RESERVA")
    suma_extra = sum(monto for u_items in items.values() for t, _, monto in u_items if t == "CUOTA_EXTRAORDINARIA")
    assert suma_gastos == Decimal("100.01")
    assert suma_reserva == Decimal("10.00")
    assert suma_extra == Decimal("10.00")
    for u_items in items.values():
        for _, _, monto in u_items:
            assert monto == monto.quantize(Decimal("0.01"))


def test_calcular_cargos_modalidad_alicuotas_invalidas_y_cero_gastos() -> None:
    """Rechaza alícuotas distintas de 100% y maneja periodo con cero egresos comunes."""
    unidades_bad = [_unidad_mem(1, Decimal("50.0000")), _unidad_mem(2, Decimal("40.0000"))]
    datos = FacturarPeriodoRequest(periodo="2026-10", modalidad="ALICUOTA")
    with pytest.raises(ErrorFinanciero, match="100.0000%"):
        calcular_cargos_modalidad(datos, unidades_bad, Decimal("100.00"), Decimal("10.00"))

    unidades_none = [_unidad_mem(1, None), _unidad_mem(2, Decimal("50.0000"))]
    with pytest.raises(ErrorFinanciero, match="100.0000%"):
        calcular_cargos_modalidad(datos, unidades_none, Decimal("100.00"), Decimal("0.00"))

    unidades_ok = [_unidad_mem(1, Decimal("60.0000")), _unidad_mem(2, Decimal("40.0000"))]
    items_cero, superavit = calcular_cargos_modalidad(datos, unidades_ok, Decimal("0.00"), Decimal("0.00"))
    assert superavit == Decimal("0.00")
    assert items_cero[1] == [("GASTO_COMUN", "Cuota parte de gastos comunes (2026-10)", Decimal("0.00"))]
    assert items_cero[2] == [("GASTO_COMUN", "Cuota parte de gastos comunes (2026-10)", Decimal("0.00"))]


def test_calcular_cargos_modalidad_partes_iguales_y_cuota_fija() -> None:
    """Verifica prorrateo en partes iguales y conciliación de cuota fija con o sin tarifa."""
    unidades = [
        _unidad_mem(1, Decimal("10.0000")),
        _unidad_mem(2, Decimal("20.0000")),
        _unidad_mem(3, Decimal("30.0000")),
    ]
    datos_iguales = FacturarPeriodoRequest(
        periodo="2026-11",
        modalidad="PARTES_IGUALES",
        cuota_extraordinaria_total_usd=Decimal("5.00"),
    )
    items_eq, sup_eq = calcular_cargos_modalidad(datos_iguales, unidades, Decimal("100.00"), Decimal("0.00"))
    assert sup_eq == Decimal("0.00")
    assert [items_eq[uid][0][2] for uid in (1, 2, 3)] == [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")]
    assert items_eq[1][1] == ("CUOTA_EXTRAORDINARIA", "Cuota extraordinaria aprobada", Decimal("1.67"))

    unidades_fijas = [_unidad_mem(1, Decimal("60.0000"), Decimal("35.00")), _unidad_mem(2, Decimal("40.0000"), None)]
    datos_fijo = FacturarPeriodoRequest(
        periodo="2026-11",
        modalidad="CUOTA_FIJA",
        monto_cuota_fija_usd=Decimal("25.00"),
    )
    items_fijo, superavit = calcular_cargos_modalidad(datos_fijo, unidades_fijas, Decimal("48.00"), Decimal("0.00"))
    assert items_fijo[1][0][2] == Decimal("35.00")
    assert items_fijo[2][0][2] == Decimal("25.00")
    assert superavit == Decimal("12.00")

    datos_sin_tarifa = FacturarPeriodoRequest(periodo="2026-11", modalidad="CUOTA_FIJA", monto_cuota_fija_usd=None)
    with pytest.raises(ErrorFinanciero, match="monto_cuota_fija_usd"):
        calcular_cargos_modalidad(datos_sin_tarifa, unidades_fijas, Decimal("48.00"), Decimal("0.00"))


def test_obtener_id_recibo_sin_flush_falla() -> None:
    """Verifica guarda defensiva cuando un recibo no tiene clave primaria asignada."""
    recibo = Recibo(condominio_id=1, unidad_id=1, periodo="2026-11", monto_usd=Decimal("10.00"))
    with pytest.raises(RuntimeError, match="no obtuvo ID primario"):
        _obtener_id_recibo(recibo)


async def test_verificar_periodo_facturable_candado_duplicados_y_multa() -> None:
    """Valida Candado Contable, rechazo por cargos mensuales previos y permiso para fusión sobre multas."""
    engine, factory = await create_sqlite_fk_factory()
    try:
        ctx = await seed_condo_base(factory)
        async with factory() as session:
            await verificar_periodo_facturable(session, "2026-01", condominio_id=1)

            session.add(ReporteMensual(condominio_id=1, periodo="2026-01", estado="PRELIMINAR"))
            session.add(ReporteMensual(condominio_id=2, periodo="2026-02", estado="CERRADO"))
            session.add(ReporteMensual(condominio_id=1, periodo="2026-03", estado="CERRADO"))
            await session.flush()

            await verificar_periodo_facturable(session, "2026-01", condominio_id=1)
            await verificar_periodo_facturable(session, "2026-02", condominio_id=1)

            with pytest.raises(HTTPException) as exc_cerrado:
                await verificar_periodo_facturable(session, "2026-03", condominio_id=1)
            assert exc_cerrado.value.status_code == 409

            rec_multa = Recibo(
                condominio_id=1,
                unidad_id=ctx.unidad_a_id,
                periodo="2026-04",
                monto_usd=Decimal("15.00"),
                bloqueado=False,
            )
            session.add(rec_multa)
            await session.flush()
            session.add(
                ReciboItem(
                    condominio_id=1,
                    recibo_id=rec_multa.id,
                    tipo_item="MULTA",
                    descripcion="Multa ruido",
                    monto_usd=Decimal("15.00"),
                )
            )
            await session.flush()
            await verificar_periodo_facturable(session, "2026-04", condominio_id=1)

            session.add(
                ReciboItem(
                    condominio_id=1,
                    recibo_id=rec_multa.id,
                    tipo_item="GASTO_COMUN",
                    descripcion="Ya emitido",
                    monto_usd=Decimal("20.00"),
                )
            )
            await session.flush()
            with pytest.raises(HTTPException) as exc_dup:
                await verificar_periodo_facturable(session, "2026-04", condominio_id=1)
            assert exc_dup.value.status_code == 409

            rec_bloq = Recibo(
                condominio_id=1,
                unidad_id=ctx.unidad_b_id,
                periodo="2026-05",
                monto_usd=Decimal("10.00"),
                bloqueado=True,
            )
            session.add(rec_bloq)
            await session.flush()
            with pytest.raises(HTTPException) as exc_bloq:
                await verificar_periodo_facturable(session, "2026-05", condominio_id=1)
            assert exc_bloq.value.status_code == 409
    finally:
        await engine.dispose()


async def test_cargar_contexto_facturacion_egresos_y_fondo() -> None:
    """Comprueba suma selectiva de egresos comunes, periodo sin gastos y ausencia/presencia de fondo legal."""
    engine, factory = await create_sqlite_fk_factory()
    try:
        await seed_condo_base(factory)
        async with factory() as session:
            datos_con_fondo = FacturarPeriodoRequest(periodo="2026-06", incluir_fondo_reserva=True)
            with pytest.raises(HTTPException) as exc_sin_uni:
                await cargar_contexto_facturacion(session, datos_con_fondo, condominio_id=99)
            assert exc_sin_uni.value.status_code == 400

            with pytest.raises(ErrorFinanciero, match="Fondo de Reserva Legal activo"):
                await cargar_contexto_facturacion(session, datos_con_fondo, condominio_id=1)

            datos_sin_fondo = FacturarPeriodoRequest(periodo="2026-06", incluir_fondo_reserva=False)
            unidades, total_cero, fondo_none, recargo_cero = await cargar_contexto_facturacion(
                session, datos_sin_fondo, condominio_id=1
            )
            assert len(unidades) == 2
            assert total_cero == Decimal("0.00")
            assert fondo_none is None
            assert recargo_cero == Decimal("0.00")

            session.add_all(
                [
                    Egreso(
                        condominio_id=1,
                        periodo="2026-06",
                        categoria="LIMPIEZA",
                        descripcion="Común",
                        monto=Decimal("80.00"),
                        moneda="USD",
                        monto_usd=Decimal("80.00"),
                        tasa_cambio=Decimal("45.5000"),
                        es_gasto_comun=True,
                    ),
                    Egreso(
                        condominio_id=1,
                        periodo="2026-06",
                        categoria="PRIVADO",
                        descripcion="No común",
                        monto=Decimal("500.00"),
                        moneda="USD",
                        monto_usd=Decimal("500.00"),
                        tasa_cambio=Decimal("45.5000"),
                        es_gasto_comun=False,
                    ),
                    FondoCondominio(
                        condominio_id=1,
                        nombre="Reserva Legal",
                        tipo="RESERVA_LEGAL",
                        porcentaje_recargo=Decimal("10.00"),
                        saldo_actual_usd=Decimal("100.00"),
                        es_activo=True,
                    ),
                ]
            )
            await session.commit()

            unidades_2, total_eg, fondo_2, recargo = await cargar_contexto_facturacion(
                session, datos_con_fondo, condominio_id=1
            )
            assert len(unidades_2) == 2
            assert total_eg == Decimal("80.00")
            assert fondo_2 is not None
            assert recargo == Decimal("8.00")
    finally:
        await engine.dispose()


async def test_persistir_lote_facturacion_creditos_upsert_y_worm() -> None:
    """Prueba emisión completa con abono parcial/total de crédito, fusión UPSERT y auditoría WORM."""
    engine, factory = await create_sqlite_fk_factory()
    try:
        ctx = await seed_condo_base(factory)
        async with factory() as session:
            uni_a = (await session.execute(select(Unidad).where(Unidad.id == ctx.unidad_a_id))).scalar_one()
            uni_b = (await session.execute(select(Unidad).where(Unidad.id == ctx.unidad_b_id))).scalar_one()
            uni_a.credito_disponible_usd = Decimal("15.00")
            uni_b.credito_disponible_usd = Decimal("100.00")

            fondo = FondoCondominio(
                condominio_id=1,
                nombre="Reserva Legal",
                tipo="RESERVA_LEGAL",
                porcentaje_recargo=Decimal("10.00"),
                saldo_actual_usd=Decimal("50.00"),
                es_activo=True,
            )
            session.add(fondo)
            await session.commit()

            datos = FacturarPeriodoRequest(periodo="2026-07", modalidad="ALICUOTA", incluir_fondo_reserva=True)
            items, superavit = calcular_cargos_modalidad(datos, [uni_a, uni_b], Decimal("100.00"), Decimal("10.00"))
            bruto, credito, neto = await persistir_lote_facturacion(
                session,
                [uni_a, uni_b],
                "2026-07",
                "ALICUOTA",
                items,
                fondo,
                Decimal("10.00"),
                superavit,
                condominio_id=1,
                usuario_id=ctx.tesorero_id,
            )
            assert bruto == Decimal("110.00")
            assert credito == Decimal("59.00")
            assert neto == Decimal("51.00")

        async with factory() as verify:
            rec_a = (
                await verify.execute(
                    select(Recibo).where(Recibo.unidad_id == ctx.unidad_a_id, Recibo.periodo == "2026-07")
                )
            ).scalar_one()
            rec_b = (
                await verify.execute(
                    select(Recibo).where(Recibo.unidad_id == ctx.unidad_b_id, Recibo.periodo == "2026-07")
                )
            ).scalar_one()
            uni_a_db = (await verify.execute(select(Unidad).where(Unidad.id == ctx.unidad_a_id))).scalar_one()
            uni_b_db = (await verify.execute(select(Unidad).where(Unidad.id == ctx.unidad_b_id))).scalar_one()
            fondo_db = (await verify.execute(select(FondoCondominio))).scalar_one()

            assert rec_a.monto_usd == Decimal("51.00")
            assert rec_a.estado == "PENDIENTE"
            assert uni_a_db.credito_disponible_usd == Decimal("0.00")

            assert rec_b.monto_usd == Decimal("0.00")
            assert rec_b.estado == "PAGADO"
            assert uni_b_db.credito_disponible_usd == Decimal("56.00")
            assert fondo_db.saldo_actual_usd == Decimal("60.00")

            abonos = (
                (await verify.execute(select(ReciboItem).where(ReciboItem.tipo_item == "ABONO_CREDITO_PREVIO")))
                .scalars()
                .all()
            )
            assert sorted(item.monto_usd for item in abonos) == [Decimal("-44.00"), Decimal("-15.00")]

            auds = (await verify.execute(select(AuditoriaRecibo).order_by(AuditoriaRecibo.id.asc()))).scalars().all()
            assert len(auds) == 2
            assert auds[1].prev_hash == auds[0].record_hash

            # Fusión UPSERT en periodo 2026-08 con recibo previo pagado parcialmente y multa
            rec_prev = Recibo(
                condominio_id=1,
                unidad_id=ctx.unidad_a_id,
                periodo="2026-08",
                monto_usd=Decimal("20.00"),
                monto_pagado_usd=Decimal("5.00"),
                estado="PAGADO_PARCIAL",
            )
            verify.add(rec_prev)
            await verify.flush()
            verify.add(
                ReciboItem(
                    condominio_id=1,
                    recibo_id=rec_prev.id,
                    tipo_item="MULTA",
                    descripcion="Multa previa",
                    monto_usd=Decimal("20.00"),
                )
            )
            uni_a_db.credito_disponible_usd = Decimal("10.00")
            uni_b_db.credito_disponible_usd = Decimal("0.00")
            await verify.commit()

            items_ups, _ = calcular_cargos_modalidad(
                FacturarPeriodoRequest(periodo="2026-08", modalidad="PARTES_IGUALES"),
                [uni_a_db, uni_b_db],
                Decimal("40.00"),
                Decimal("0.00"),
            )
            bruto2, cred2, neto2 = await persistir_lote_facturacion(
                verify,
                [uni_a_db, uni_b_db],
                "2026-08",
                "PARTES_IGUALES",
                items_ups,
                fondo_db,
                Decimal("0.00"),
                Decimal("0.00"),
                condominio_id=1,
                usuario_id=ctx.presidente_id,
            )
            assert bruto2 == Decimal("40.00")
            assert cred2 == Decimal("10.00")
            assert neto2 == Decimal("30.00")

            await verify.refresh(rec_prev)
            assert rec_prev.monto_usd == Decimal("30.00")
            assert rec_prev.estado == "PAGADO_PARCIAL"
    finally:
        await engine.dispose()


async def test_persistir_lote_cuota_fija_conciliacion_y_deficit_excedido() -> None:
    """Valida conciliación de cuota fija con fondo ausente, déficit permitido y déficit que excede saldo."""
    engine, factory = await create_sqlite_fk_factory()
    try:
        ctx = await seed_condo_base(factory)
        async with factory() as session:
            unidades = list((await session.execute(select(Unidad).order_by(Unidad.id.asc()))).scalars().all())
            items = {
                ctx.unidad_a_id: [("CUOTA_FIJA", "Fija A", Decimal("25.00"))],
                ctx.unidad_b_id: [("CUOTA_FIJA", "Fija B", Decimal("25.00"))],
            }
            with pytest.raises(ErrorFinanciero, match="Fondo de Reserva Legal activo"):
                await persistir_lote_facturacion(
                    session,
                    unidades,
                    "2026-09",
                    "CUOTA_FIJA",
                    items,
                    None,
                    Decimal("0.00"),
                    Decimal("5.00"),
                    condominio_id=1,
                )
            await session.rollback()
            unidades = list((await session.execute(select(Unidad).order_by(Unidad.id.asc()))).scalars().all())

            fondo = FondoCondominio(
                condominio_id=1,
                nombre="Reserva",
                tipo="RESERVA_LEGAL",
                porcentaje_recargo=Decimal("10.00"),
                saldo_actual_usd=Decimal("10.00"),
                es_activo=True,
            )
            session.add(fondo)
            await session.commit()

            with pytest.raises(ErrorFinanciero, match="déficit de cuota fija"):
                await persistir_lote_facturacion(
                    session,
                    unidades,
                    "2026-09",
                    "CUOTA_FIJA",
                    items,
                    fondo,
                    Decimal("0.00"),
                    Decimal("-15.00"),
                    condominio_id=1,
                )
            await session.rollback()
            unidades = list((await session.execute(select(Unidad).order_by(Unidad.id.asc()))).scalars().all())

            # Con superávit 0 y sin fondo también debe persistir sin error
            bruto, _, _ = await persistir_lote_facturacion(
                session,
                unidades,
                "2026-09",
                "CUOTA_FIJA",
                items,
                None,
                Decimal("0.00"),
                Decimal("0.00"),
                condominio_id=1,
            )
            assert bruto == Decimal("50.00")
    finally:
        await engine.dispose()


def test_constantes_dataclasses_y_decimal_or_default() -> None:
    """Verifica tupla de tipos mensuales, dataclasses congelados y fallback de decimales."""
    assert _TIPOS_FACTURACION_MENSUAL == (
        "GASTO_COMUN",
        "CUOTA_FIJA",
        "FONDO_RESERVA",
        "CUOTA_EXTRAORDINARIA",
    )
    assert is_dataclass(_EntradaLoteUnidad)
    recibo = Recibo(condominio_id=1, unidad_id=1, periodo="2026-10", monto_usd=Decimal("10.00"))
    item = ReciboItem(
        condominio_id=1,
        recibo_id=0,
        tipo_item="GASTO_COMUN",
        descripcion="Cargo",
        monto_usd=Decimal("10.00"),
    )
    entrada = _EntradaLoteUnidad(
        recibo=recibo,
        items=[item],
        credito_usado=Decimal("1.50"),
        estado_viejo="INEXISTENTE",
        es_upsert=False,
    )
    assert entrada.recibo is recibo
    assert entrada.items == [item]
    assert entrada.credito_usado == Decimal("1.50")
    assert entrada.estado_viejo == "INEXISTENTE"
    assert entrada.es_upsert is False
    with pytest.raises(FrozenInstanceError):
        cast(Any, entrada).es_upsert = True

    assert is_dataclass(_ContextoAuditoriaLote)
    ctx_aud = _ContextoAuditoriaLote(periodo="2026-10", condominio_id=2, usuario_id=None)
    assert ctx_aud.periodo == "2026-10"
    assert ctx_aud.condominio_id == 2
    assert ctx_aud.usuario_id is None
    with pytest.raises(FrozenInstanceError):
        cast(Any, ctx_aud).periodo = "2026-11"

    assert _decimal_or_default(None, Decimal("9.99")) == Decimal("9.99")
    assert _decimal_or_default(Decimal("0.00"), Decimal("9.99")) == Decimal("0.00")
    assert _decimal_or_default(Decimal("3.25"), Decimal("9.99")) == Decimal("3.25")


def test_calcular_cargos_modalidad_tuplas_exactas_y_fronteras_cuota_fija() -> None:
    """Verifica etiquetas exactas, fallback de descripción, redondeos y bordes de cuota fija."""
    unidades = [_unidad_mem(1, Decimal("60.0000")), _unidad_mem(2, Decimal("40.0000"))]
    datos_alicuota = FacturarPeriodoRequest(
        periodo="2026-10",
        modalidad="ALICUOTA",
        incluir_fondo_reserva=True,
        cuota_extraordinaria_total_usd=Decimal("10.00"),
        descripcion_cuota_extraordinaria=None,
    )
    items_ali, superavit_ali = calcular_cargos_modalidad(
        datos_alicuota,
        unidades,
        total_egresos_comunes=Decimal("100.00"),
        recargo_reserva_total=Decimal("10.00"),
    )
    assert superavit_ali == Decimal("0.00")
    assert items_ali[1] == [
        ("GASTO_COMUN", "Cuota parte de gastos comunes (2026-10)", Decimal("60.00")),
        ("FONDO_RESERVA", "Aporte al Fondo de Reserva Legal", Decimal("6.00")),
        ("CUOTA_EXTRAORDINARIA", "Cuota extraordinaria aprobada", Decimal("6.00")),
    ]
    assert items_ali[2] == [
        ("GASTO_COMUN", "Cuota parte de gastos comunes (2026-10)", Decimal("40.00")),
        ("FONDO_RESERVA", "Aporte al Fondo de Reserva Legal", Decimal("4.00")),
        ("CUOTA_EXTRAORDINARIA", "Cuota extraordinaria aprobada", Decimal("4.00")),
    ]

    datos_desc_vacia = FacturarPeriodoRequest(
        periodo="2026-10",
        modalidad="PARTES_IGUALES",
        incluir_fondo_reserva=True,
        cuota_extraordinaria_total_usd=Decimal("2.00"),
        descripcion_cuota_extraordinaria="",
    )
    items_vacia, _ = calcular_cargos_modalidad(
        datos_desc_vacia,
        unidades,
        total_egresos_comunes=Decimal("20.00"),
        recargo_reserva_total=Decimal("0.02"),
    )
    assert items_vacia[1] == [
        ("GASTO_COMUN", "Cuota parte de gastos comunes (2026-10)", Decimal("10.00")),
        ("FONDO_RESERVA", "Aporte al Fondo de Reserva Legal", Decimal("0.01")),
        ("CUOTA_EXTRAORDINARIA", "Cuota extraordinaria aprobada", Decimal("1.00")),
    ]

    datos_desc_custom = FacturarPeriodoRequest(
        periodo="2026-10",
        modalidad="PARTES_IGUALES",
        cuota_extraordinaria_total_usd=Decimal("4.00"),
        descripcion_cuota_extraordinaria="Impermeabilización techo",
    )
    items_custom, _ = calcular_cargos_modalidad(
        datos_desc_custom,
        unidades,
        total_egresos_comunes=Decimal("20.00"),
        recargo_reserva_total=Decimal("0.00"),
    )
    assert items_custom[2] == [
        ("GASTO_COMUN", "Cuota parte de gastos comunes (2026-10)", Decimal("10.00")),
        ("CUOTA_EXTRAORDINARIA", "Impermeabilización techo", Decimal("2.00")),
    ]

    sin_attr = cast(Unidad, SimpleNamespace(id=1))
    con_cien = _unidad_mem(2, Decimal("100.0000"))
    items_attr, _ = calcular_cargos_modalidad(
        FacturarPeriodoRequest(periodo="2026-10", modalidad="ALICUOTA"),
        [sin_attr, con_cien],
        total_egresos_comunes=Decimal("50.00"),
        recargo_reserva_total=Decimal("0.00"),
    )
    assert items_attr[1] == [("GASTO_COMUN", "Cuota parte de gastos comunes (2026-10)", Decimal("0.00"))]
    assert items_attr[2] == [("GASTO_COMUN", "Cuota parte de gastos comunes (2026-10)", Decimal("50.00"))]

    with pytest.raises(
        ErrorFinanciero,
        match=r"^La suma de alícuotas de las unidades debe equivaler a 100\.0000% antes de facturar$",
    ):
        calcular_cargos_modalidad(
            FacturarPeriodoRequest(periodo="2026-10", modalidad="ALICUOTA"),
            [_unidad_mem(1, Decimal("70.0000")), _unidad_mem(2, Decimal("20.0000"))],
            total_egresos_comunes=Decimal("10.00"),
            recargo_reserva_total=Decimal("0.00"),
        )

    unidades_fija_redondeo = [
        _unidad_mem(1, Decimal("60.0000"), Decimal("25.005")),
        _unidad_mem(2, Decimal("40.0000"), None),
    ]
    datos_fija = FacturarPeriodoRequest(
        periodo="2026-11",
        modalidad="CUOTA_FIJA",
        monto_cuota_fija_usd=Decimal("20.004"),
        cuota_extraordinaria_total_usd=Decimal("10.00"),
        descripcion_cuota_extraordinaria="Bomba de agua",
    )
    items_fija, deficit_fija = calcular_cargos_modalidad(
        datos_fija,
        unidades_fija_redondeo,
        total_egresos_comunes=Decimal("50.005"),
        recargo_reserva_total=Decimal("99.00"),
    )
    assert items_fija[1] == [
        ("CUOTA_FIJA", "Cuota fija mensual (2026-11)", Decimal("25.01")),
        ("CUOTA_EXTRAORDINARIA", "Bomba de agua", Decimal("5.00")),
    ]
    assert items_fija[2] == [
        ("CUOTA_FIJA", "Cuota fija mensual (2026-11)", Decimal("20.00")),
        ("CUOTA_EXTRAORDINARIA", "Bomba de agua", Decimal("5.00")),
    ]
    assert deficit_fija == Decimal("-5.00")

    msg_cuota = r"^En modalidad CUOTA_FIJA debe definir monto_cuota_fija_usd mayor que cero$"
    for tarifa_invalida in (Decimal("0.00"), Decimal("-5.00")):
        with pytest.raises(ErrorFinanciero, match=msg_cuota):
            calcular_cargos_modalidad(
                FacturarPeriodoRequest(
                    periodo="2026-11",
                    modalidad="CUOTA_FIJA",
                    monto_cuota_fija_usd=Decimal("25.00"),
                ),
                [_unidad_mem(1, Decimal("100.0000"), tarifa_invalida)],
                total_egresos_comunes=Decimal("10.00"),
                recargo_reserva_total=Decimal("0.00"),
            )
    with pytest.raises(ErrorFinanciero, match=msg_cuota):
        calcular_cargos_modalidad(
            FacturarPeriodoRequest(periodo="2026-11", modalidad="CUOTA_FIJA", monto_cuota_fija_usd=None),
            [_unidad_mem(1, Decimal("100.0000"), None)],
            total_egresos_comunes=Decimal("10.00"),
            recargo_reserva_total=Decimal("0.00"),
        )


def test_helpers_items_recibos_fondos_y_motivos_auditoria() -> None:
    """Cubre campos exactos de ReciboItem, fusión/creación de recibos, fondos y motivos WORM."""
    items_sin_cred = _construir_items_recibo(
        7,
        [("GASTO_COMUN", "Desc gasto", Decimal("12.34"))],
        Decimal("0.00"),
    )
    assert len(items_sin_cred) == 1
    assert items_sin_cred[0].condominio_id == 7
    assert items_sin_cred[0].recibo_id == 0
    assert items_sin_cred[0].tipo_item == "GASTO_COMUN"
    assert items_sin_cred[0].descripcion == "Desc gasto"
    assert items_sin_cred[0].monto_usd == Decimal("12.34")

    items_con_cred = _construir_items_recibo(
        7,
        [("GASTO_COMUN", "Desc gasto", Decimal("12.34"))],
        Decimal("5.25"),
    )
    assert len(items_con_cred) == 2
    assert items_con_cred[1].condominio_id == 7
    assert items_con_cred[1].recibo_id == 0
    assert items_con_cred[1].tipo_item == "ABONO_CREDITO_PREVIO"
    assert items_con_cred[1].descripcion == "Abono automático de saldo a favor disponible"
    assert items_con_cred[1].monto_usd == Decimal("-5.25")

    uni_sin_condo = cast(Unidad, SimpleNamespace(id=11, condominio_id=None, credito_disponible_usd=None))
    rec_nuevo, items_nuevo, bruto_n, cred_n = _crear_recibo_e_items_unidad(
        uni_sin_condo,
        "2026-10",
        [("GASTO_COMUN", "A", Decimal("10.004")), ("FONDO_RESERVA", "B", Decimal("5.001"))],
        condominio_id=4,
    )
    assert bruto_n == Decimal("15.01")
    assert cred_n == Decimal("0.00")
    assert rec_nuevo.condominio_id == 4
    assert rec_nuevo.unidad_id == 11
    assert rec_nuevo.periodo == "2026-10"
    assert rec_nuevo.monto_usd == Decimal("15.01")
    assert rec_nuevo.monto_pagado_usd == Decimal("0.00")
    assert rec_nuevo.estado == "PENDIENTE"
    assert rec_nuevo.bloqueado is False
    assert len(items_nuevo) == 2
    assert all(it.condominio_id == 4 and it.recibo_id == 0 for it in items_nuevo)

    uni_con_condo = _unidad_mem(12, Decimal("100.0000"))
    uni_con_condo.condominio_id = 9
    uni_con_condo.credito_disponible_usd = Decimal("20.00")
    rec_pag, items_pag, bruto_p, cred_p = _crear_recibo_e_items_unidad(
        uni_con_condo,
        "2026-10",
        [("GASTO_COMUN", "A", Decimal("15.01"))],
        condominio_id=4,
    )
    assert bruto_p == Decimal("15.01")
    assert cred_p == Decimal("15.01")
    assert rec_pag.condominio_id == 9
    assert rec_pag.monto_usd == Decimal("0.00")
    assert rec_pag.estado == "PAGADO"
    assert uni_con_condo.credito_disponible_usd == Decimal("4.99")
    assert len(items_pag) == 2
    assert items_pag[1].condominio_id == 9
    assert items_pag[1].monto_usd == Decimal("-15.01")

    rec_prev_none = cast(
        Recibo,
        SimpleNamespace(condominio_id=None, monto_usd=Decimal("20.00"), monto_pagado_usd=None, estado="PENDIENTE"),
    )
    uni_fusion_1 = cast(Unidad, SimpleNamespace(credito_disponible_usd=Decimal("30.00")))
    items_f1, bruto_f1, cred_f1, est_viejo_1 = _fusionar_recibo_existente(
        rec_prev_none,
        uni_fusion_1,
        [("GASTO_COMUN", "X", Decimal("15.00"))],
        condominio_id=6,
    )
    assert bruto_f1 == Decimal("15.00")
    assert cred_f1 == Decimal("30.00")
    assert est_viejo_1 == "PENDIENTE"
    assert rec_prev_none.monto_usd == Decimal("5.00")
    assert rec_prev_none.estado == "PENDIENTE"
    assert uni_fusion_1.credito_disponible_usd == Decimal("0.00")
    assert all(it.condominio_id == 6 for it in items_f1)

    rec_prev_parcial = Recibo(
        condominio_id=8,
        unidad_id=1,
        periodo="2026-10",
        monto_usd=Decimal("20.00"),
        monto_pagado_usd=Decimal("5.00"),
        estado="PAGADO_PARCIAL",
    )
    uni_fusion_2 = _unidad_mem(1, Decimal("100.0000"))
    uni_fusion_2.credito_disponible_usd = Decimal("35.00")
    items_f2, bruto_f2, cred_f2, est_viejo_2 = _fusionar_recibo_existente(
        rec_prev_parcial,
        uni_fusion_2,
        [("GASTO_COMUN", "X", Decimal("10.00"))],
        condominio_id=1,
    )
    assert bruto_f2 == Decimal("10.00")
    assert cred_f2 == Decimal("25.00")
    assert est_viejo_2 == "PAGADO_PARCIAL"
    assert rec_prev_parcial.monto_usd == Decimal("5.00")
    assert rec_prev_parcial.estado == "PAGADO"
    assert uni_fusion_2.credito_disponible_usd == Decimal("10.00")
    assert all(it.condominio_id == 8 for it in items_f2)

    _validar_fondo_ausente("ALICUOTA", Decimal("5.00"))
    _validar_fondo_ausente("CUOTA_FIJA", Decimal("0.00"))
    msg_fondo_ausente = r"^No existe un Fondo de Reserva Legal activo para conciliar la cuota fija\.$"
    for monto_sup in (Decimal("-5.00"), Decimal("5.00")):
        with pytest.raises(ErrorFinanciero, match=msg_fondo_ausente):
            _validar_fondo_ausente("CUOTA_FIJA", monto_sup)

    fondo_none_saldo = cast(FondoCondominio, SimpleNamespace(saldo_actual_usd=None))
    _actualizar_fondo_reserva(fondo_none_saldo, "CUOTA_FIJA", Decimal("99.00"), Decimal("10.00"))
    assert fondo_none_saldo.saldo_actual_usd == Decimal("10.00")

    _actualizar_fondo_reserva(fondo_none_saldo, "CUOTA_FIJA", Decimal("99.00"), Decimal("-10.00"))
    assert fondo_none_saldo.saldo_actual_usd == Decimal("0.00")

    _actualizar_fondo_reserva(fondo_none_saldo, "ALICUOTA", Decimal("5.00"), Decimal("99.00"))
    assert fondo_none_saldo.saldo_actual_usd == Decimal("5.00")

    with pytest.raises(
        ErrorFinanciero,
        match=r"^El déficit de cuota fija excede el saldo disponible en el Fondo de Reserva\.$",
    ):
        _actualizar_fondo_reserva(fondo_none_saldo, "CUOTA_FIJA", Decimal("0.00"), Decimal("-5.01"))

    assert (
        _motivo_auditoria_lote("2026-10", Decimal("12.50"), True)
        == "Fusión facturación mensual 2026-10 (crédito aplicado: -12.50 USD)"
    )
    assert _motivo_auditoria_lote("2026-10", Decimal("0.00"), True) == "Fusión facturación mensual 2026-10"
    assert (
        _motivo_auditoria_lote("2026-10", Decimal("7.25"), False)
        == "Aplicación automática de saldo a favor en facturación 2026-10 (-7.25 USD)"
    )


class _SpySession:
    def __init__(self, inner: AsyncSession) -> None:
        self._inner = inner
        self.stmts: list[Any] = []

    async def execute(self, stmt: Any, *args: Any, **kwargs: Any) -> Any:
        self.stmts.append(stmt)
        return await self._inner.execute(stmt, *args, **kwargs)


async def test_verificar_periodo_facturable_detalles_tipos_y_limit_sql() -> None:
    """Valida detalles 409, todos los tipos mensuales, periodo distinto en ReporteMensual y LIMIT 1."""
    engine, factory = await create_sqlite_fk_factory()
    try:
        ctx = await seed_condo_base(factory)
        async with factory() as session:
            session.add(ReporteMensual(condominio_id=1, periodo="2026-99", estado="CERRADO"))
            await session.flush()

            spy = _SpySession(session)
            await verificar_periodo_facturable(cast(AsyncSession, spy), "2026-08", condominio_id=7)
            assert len(spy.stmts) == 2
            compiled = spy.stmts[1].compile()
            sql_text = str(compiled)
            assert "LEFT OUTER JOIN" in sql_text
            assert "LIMIT" in sql_text
            assert any(type(val) is int and val == 1 for val in compiled.params.values())

            session.add(ReporteMensual(condominio_id=1, periodo="2026-10", estado="CERRADO"))
            await session.flush()
            with pytest.raises(HTTPException) as exc_cerrado:
                await verificar_periodo_facturable(session, "2026-10")
            assert exc_cerrado.value.status_code == 409
            assert exc_cerrado.value.detail == "El periodo está cerrado por Candado Contable y no admite facturación."

            for idx, tipo in enumerate(
                ("GASTO_COMUN", "CUOTA_FIJA", "FONDO_RESERVA", "CUOTA_EXTRAORDINARIA"),
                start=1,
            ):
                periodo = f"2026-0{idx}"
                rec = Recibo(
                    condominio_id=1,
                    unidad_id=ctx.unidad_a_id,
                    periodo=periodo,
                    monto_usd=Decimal("10.00"),
                    bloqueado=False,
                )
                session.add(rec)
                await session.flush()
                session.add(
                    ReciboItem(
                        condominio_id=1,
                        recibo_id=rec.id,
                        tipo_item=tipo,
                        descripcion=f"Item {tipo}",
                        monto_usd=Decimal("10.00"),
                    )
                )
                await session.flush()
                with pytest.raises(HTTPException) as exc_dup:
                    await verificar_periodo_facturable(session, periodo)
                assert exc_dup.value.status_code == 409
                assert exc_dup.value.detail == "Los recibos de este periodo ya fueron emitidos previamente."

            rec_otro_condo = Recibo(
                condominio_id=2,
                unidad_id=ctx.unidad_b_id,
                periodo="2026-12",
                monto_usd=Decimal("10.00"),
                bloqueado=True,
            )
            session.add(rec_otro_condo)
            await session.flush()
            await verificar_periodo_facturable(session, "2026-12")
    finally:
        await engine.dispose()


async def test_cargar_contexto_y_persistir_lote_integracion_completa() -> None:
    """Verifica detalles de contexto, filtros de egresos/fondos, sin auditoría con crédito 0 y hash WORM exacto."""
    engine, factory = await create_sqlite_fk_factory()
    try:
        ctx = await seed_condo_base(factory)
        async with factory() as session:
            with pytest.raises(HTTPException) as exc_sin_uni:
                await cargar_contexto_facturacion(
                    session,
                    FacturarPeriodoRequest(periodo="2026-10"),
                    condominio_id=99,
                )
            assert exc_sin_uni.value.status_code == 400
            assert exc_sin_uni.value.detail == "No existen unidades registradas para emitir la facturación."

            with pytest.raises(
                ErrorFinanciero,
                match=r"^No existe un Fondo de Reserva Legal activo configurado para aplicar el recargo\.$",
            ):
                await cargar_contexto_facturacion(
                    session,
                    FacturarPeriodoRequest(periodo="2026-10", modalidad="ALICUOTA", incluir_fondo_reserva=True),
                )

            unidades_fija, egresos_fija, fondo_fija, recargo_fija = await cargar_contexto_facturacion(
                session,
                FacturarPeriodoRequest(
                    periodo="2026-10",
                    modalidad="CUOTA_FIJA",
                    monto_cuota_fija_usd=Decimal("20.00"),
                    incluir_fondo_reserva=True,
                ),
            )
            assert [u.id for u in unidades_fija] == sorted(u.id for u in unidades_fija)
            assert egresos_fija == Decimal("0.00")
            assert fondo_fija is None
            assert recargo_fija == Decimal("0.00")

            session.add_all(
                [
                    Egreso(
                        condominio_id=1,
                        periodo="2026-10",
                        categoria="MANT",
                        descripcion="Válido",
                        monto=Decimal("10.10"),
                        moneda="USD",
                        monto_usd=Decimal("10.10"),
                        tasa_cambio=Decimal("45.5000"),
                        es_gasto_comun=True,
                    ),
                    Egreso(
                        condominio_id=1,
                        periodo="2026-09",
                        categoria="MANT",
                        descripcion="Otro periodo",
                        monto=Decimal("500.00"),
                        moneda="USD",
                        monto_usd=Decimal("500.00"),
                        tasa_cambio=Decimal("45.5000"),
                        es_gasto_comun=True,
                    ),
                    Egreso(
                        condominio_id=2,
                        periodo="2026-10",
                        categoria="MANT",
                        descripcion="Otro condo",
                        monto=Decimal("500.00"),
                        moneda="USD",
                        monto_usd=Decimal("500.00"),
                        tasa_cambio=Decimal("45.5000"),
                        es_gasto_comun=True,
                    ),
                    FondoCondominio(
                        condominio_id=1,
                        nombre="Inactivo",
                        tipo="RESERVA_LEGAL",
                        porcentaje_recargo=Decimal("50.00"),
                        saldo_actual_usd=Decimal("0.00"),
                        es_activo=False,
                    ),
                    FondoCondominio(
                        condominio_id=1,
                        nombre="Especial",
                        tipo="ESPECIAL",
                        porcentaje_recargo=Decimal("50.00"),
                        saldo_actual_usd=Decimal("0.00"),
                        es_activo=True,
                    ),
                    FondoCondominio(
                        condominio_id=1,
                        nombre="Reserva Activa",
                        tipo="RESERVA_LEGAL",
                        porcentaje_recargo=Decimal("5.00"),
                        saldo_actual_usd=Decimal("10.00"),
                        es_activo=True,
                    ),
                ]
            )
            await session.commit()

            unidades_ctx, total_eg, fondo_ctx, recargo_ctx = await cargar_contexto_facturacion(
                session,
                FacturarPeriodoRequest(periodo="2026-10", modalidad="ALICUOTA", incluir_fondo_reserva=True),
            )
            assert [u.id for u in unidades_ctx] == [ctx.unidad_a_id, ctx.unidad_b_id]
            assert total_eg == Decimal("10.10")
            assert fondo_ctx is not None and fondo_ctx.nombre == "Reserva Activa"
            assert recargo_ctx == Decimal("0.51")

            uni_a, uni_b = unidades_ctx[0], unidades_ctx[1]
            uni_a.credito_disponible_usd = Decimal("0.00")
            uni_b.credito_disponible_usd = Decimal("10.00")
            items_10, sup_10 = calcular_cargos_modalidad(
                FacturarPeriodoRequest(periodo="2026-10", modalidad="ALICUOTA", incluir_fondo_reserva=True),
                unidades_ctx,
                Decimal("100.00"),
                Decimal("10.00"),
            )
            bruto_10, cred_10, neto_10 = await persistir_lote_facturacion(
                session,
                unidades_ctx,
                "2026-10",
                "ALICUOTA",
                items_10,
                fondo_ctx,
                Decimal("10.00"),
                sup_10,
                usuario_id=ctx.tesorero_id,
            )
            assert (bruto_10, cred_10, neto_10) == (Decimal("110.00"), Decimal("10.00"), Decimal("100.00"))

        async with factory() as verify:
            auds = list((await verify.execute(select(AuditoriaRecibo).order_by(AuditoriaRecibo.id.asc()))).scalars())
            assert len(auds) == 1
            aud_1 = auds[0]
            rec_b = (
                await verify.execute(
                    select(Recibo).where(Recibo.unidad_id == ctx.unidad_b_id, Recibo.periodo == "2026-10")
                )
            ).scalar_one()
            assert aud_1.recibo_id == rec_b.id
            assert aud_1.condominio_id == 1
            assert aud_1.usuario_id == ctx.tesorero_id
            assert aud_1.estado_viejo == "INEXISTENTE"
            assert aud_1.estado_nuevo == "PENDIENTE"
            assert aud_1.motivo == "Aplicación automática de saldo a favor en facturación 2026-10 (-10.00 USD)"
            payload_1 = (
                f"{rec_b.id}|None|{ctx.tesorero_id}|INEXISTENTE->PENDIENTE|"
                "Aplicación automática de saldo a favor en facturación 2026-10 (-10.00 USD)"
            )
            assert aud_1.record_hash == compute_worm_record_hash(aud_1.prev_hash, payload_1)

            abonos_stmt = select(ReciboItem).where(ReciboItem.tipo_item == "ABONO_CREDITO_PREVIO")
            abonos_10 = list((await verify.execute(abonos_stmt)).scalars())
            assert len(abonos_10) == 1
            assert abonos_10[0].recibo_id == rec_b.id
            assert abonos_10[0].descripcion == "Abono automático de saldo a favor disponible"
            assert abonos_10[0].monto_usd == Decimal("-10.00")

            rec_prev = Recibo(
                condominio_id=1,
                unidad_id=ctx.unidad_a_id,
                periodo="2026-11",
                monto_usd=Decimal("15.00"),
                monto_pagado_usd=Decimal("0.00"),
                estado="PENDIENTE",
            )
            verify.add(rec_prev)
            await verify.flush()
            verify.add(
                ReciboItem(
                    condominio_id=1,
                    recibo_id=rec_prev.id,
                    tipo_item="MULTA",
                    descripcion="Multa",
                    monto_usd=Decimal("15.00"),
                )
            )
            uni_a_db = (await verify.execute(select(Unidad).where(Unidad.id == ctx.unidad_a_id))).scalar_one()
            uni_b_db = (await verify.execute(select(Unidad).where(Unidad.id == ctx.unidad_b_id))).scalar_one()
            uni_a_db.credito_disponible_usd = Decimal("0.00")
            uni_b_db.credito_disponible_usd = Decimal("0.00")
            await verify.commit()

            items_11, _ = calcular_cargos_modalidad(
                FacturarPeriodoRequest(periodo="2026-11", modalidad="PARTES_IGUALES"),
                [uni_a_db, uni_b_db],
                Decimal("20.00"),
                Decimal("0.00"),
            )
            await persistir_lote_facturacion(
                verify,
                [uni_a_db, uni_b_db],
                "2026-11",
                "PARTES_IGUALES",
                items_11,
                None,
                Decimal("0.00"),
                Decimal("0.00"),
                condominio_id=1,
                usuario_id=None,
            )

            auds_2 = list((await verify.execute(select(AuditoriaRecibo).order_by(AuditoriaRecibo.id.asc()))).scalars())
            assert len(auds_2) == 2
            aud_2 = auds_2[1]
            assert aud_2.recibo_id == rec_prev.id
            assert aud_2.usuario_id is None
            assert aud_2.estado_viejo == "PENDIENTE"
            assert aud_2.estado_nuevo == "PENDIENTE"
            assert aud_2.motivo == "Fusión facturación mensual 2026-11"
            assert aud_2.prev_hash == aud_1.record_hash
            payload_2 = f"{rec_prev.id}|None|None|PENDIENTE->PENDIENTE|Fusión facturación mensual 2026-11"
            assert aud_2.record_hash == compute_worm_record_hash(aud_2.prev_hash, payload_2)
    finally:
        await engine.dispose()
