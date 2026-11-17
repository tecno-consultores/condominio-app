"""Motor de lote para la facturación mensual LPH por alícuota, cuota fija o partes iguales."""

from dataclasses import dataclass
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import DEFAULT_CONDOMINIO_ID, sellar_cadena_worm
from src.finanzas import (
    CERO,
    ErrorFinanciero,
    aplicar_credito_disponible,
    calcular_saldo_pendiente,
    cuantizar,
    determinar_estado_recibo,
    prorratear_partes_iguales,
    prorratear_por_alicuotas,
    validar_suma_alicuotas,
)
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

_TIPOS_FACTURACION_MENSUAL: tuple[str, ...] = (
    "GASTO_COMUN",
    "CUOTA_FIJA",
    "FONDO_RESERVA",
    "CUOTA_EXTRAORDINARIA",
)


@dataclass(frozen=True)
class _EntradaLoteUnidad:
    recibo: Recibo
    items: list[ReciboItem]
    credito_usado: Decimal
    estado_viejo: str
    es_upsert: bool


def _decimal_or_default(val: Decimal | None, default: Decimal) -> Decimal:
    return default if val is None else val


async def verificar_periodo_facturable(
    db: AsyncSession,
    periodo: str,
    condominio_id: int = DEFAULT_CONDOMINIO_ID,
) -> None:
    """Valida que el periodo no esté cerrado (Candado Contable) ni posea cargos mensuales previos."""
    rep_res = await db.execute(
        select(ReporteMensual).where(
            ReporteMensual.condominio_id == condominio_id,
            ReporteMensual.periodo == periodo,
        )
    )
    reporte = rep_res.scalars().first()
    if reporte and reporte.estado == "CERRADO":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El periodo está cerrado por Candado Contable y no admite facturación.",
        )
    rec_res = await db.execute(
        select(Recibo)
        .join(ReciboItem, ReciboItem.recibo_id == Recibo.id, isouter=True)
        .where(
            Recibo.condominio_id == condominio_id,
            Recibo.periodo == periodo,
            or_(
                Recibo.bloqueado.is_(True),
                ReciboItem.tipo_item.in_(_TIPOS_FACTURACION_MENSUAL),
            ),
        )
        .limit(1)
    )
    if rec_res.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Los recibos de este periodo ya fueron emitidos previamente.",
        )


def _cargos_cuota_fija(
    datos: FacturarPeriodoRequest,
    unidades: list[Unidad],
    total_egresos_comunes: Decimal,
) -> tuple[dict[int, list[tuple[str, str, Decimal]]], Decimal]:
    items_por_unidad: dict[int, list[tuple[str, str, Decimal]]] = {}
    total_fijo = CERO
    for u in unidades:
        u_cuota = getattr(u, "cuota_fija_usd", None)
        tarifa = datos.monto_cuota_fija_usd if u_cuota is None else u_cuota
        if tarifa is None or tarifa <= CERO:
            raise ErrorFinanciero("En modalidad CUOTA_FIJA debe definir monto_cuota_fija_usd mayor que cero")
        cuota_u = cuantizar(tarifa)
        total_fijo += cuota_u
        items_por_unidad[u.id] = [("CUOTA_FIJA", f"Cuota fija mensual ({datos.periodo})", cuota_u)]
    return items_por_unidad, cuantizar(total_fijo - total_egresos_comunes)


def _cargos_variables(
    datos: FacturarPeriodoRequest,
    unidades: list[Unidad],
    total_egresos_comunes: Decimal,
    recargo_reserva_total: Decimal,
) -> dict[int, list[tuple[str, str, Decimal]]]:
    unidad_ids = [u.id for u in unidades]
    pesos_alicuota = [(u.id, _decimal_or_default(getattr(u, "alicuota", None), Decimal("0.0000"))) for u in unidades]
    if datos.modalidad == "ALICUOTA":
        if not validar_suma_alicuotas([peso for _, peso in pesos_alicuota]):
            raise ErrorFinanciero("La suma de alícuotas de las unidades debe equivaler a 100.0000% antes de facturar")
        mapa_gastos = prorratear_por_alicuotas(total_egresos_comunes, pesos_alicuota)
        mapa_reserva = prorratear_por_alicuotas(recargo_reserva_total, pesos_alicuota)
    else:
        mapa_gastos = prorratear_partes_iguales(total_egresos_comunes, unidad_ids)
        mapa_reserva = prorratear_partes_iguales(recargo_reserva_total, unidad_ids)

    items_por_unidad: dict[int, list[tuple[str, str, Decimal]]] = {}
    for u in unidades:
        lineas: list[tuple[str, str, Decimal]] = [
            ("GASTO_COMUN", f"Cuota parte de gastos comunes ({datos.periodo})", mapa_gastos[u.id])
        ]
        if mapa_reserva[u.id] > CERO:
            lineas.append(("FONDO_RESERVA", "Aporte al Fondo de Reserva Legal", mapa_reserva[u.id]))
        items_por_unidad[u.id] = lineas
    return items_por_unidad


def _anexar_cuota_extraordinaria(
    datos: FacturarPeriodoRequest,
    unidades: list[Unidad],
    items_por_unidad: dict[int, list[tuple[str, str, Decimal]]],
) -> None:
    if datos.cuota_extraordinaria_total_usd <= CERO:
        return
    if datos.modalidad == "ALICUOTA":
        pesos_alicuota = [
            (u.id, _decimal_or_default(getattr(u, "alicuota", None), Decimal("0.0000"))) for u in unidades
        ]
        if not validar_suma_alicuotas([peso for _, peso in pesos_alicuota]):
            raise ErrorFinanciero("La suma de alícuotas de las unidades debe equivaler a 100.0000% antes de facturar")
        mapa_extra = prorratear_por_alicuotas(datos.cuota_extraordinaria_total_usd, pesos_alicuota)
    else:
        mapa_extra = prorratear_partes_iguales(datos.cuota_extraordinaria_total_usd, [u.id for u in unidades])
    desc_extra = datos.descripcion_cuota_extraordinaria or "Cuota extraordinaria aprobada"
    for uid, monto_extra in mapa_extra.items():
        items_por_unidad[uid].append(("CUOTA_EXTRAORDINARIA", desc_extra, monto_extra))


def calcular_cargos_modalidad(
    datos: FacturarPeriodoRequest,
    unidades: list[Unidad],
    total_egresos_comunes: Decimal,
    recargo_reserva_total: Decimal,
) -> tuple[dict[int, list[tuple[str, str, Decimal]]], Decimal]:
    """Construye los ítems de cargo por unidad según la modalidad (ALICUOTA, CUOTA_FIJA, PARTES_IGUALES)."""
    if datos.modalidad == "CUOTA_FIJA":
        items_por_unidad, superavit_fondo = _cargos_cuota_fija(datos, unidades, total_egresos_comunes)
    else:
        items_por_unidad = _cargos_variables(datos, unidades, total_egresos_comunes, recargo_reserva_total)
        superavit_fondo = CERO

    _anexar_cuota_extraordinaria(datos, unidades, items_por_unidad)
    return items_por_unidad, superavit_fondo


def _construir_items_recibo(
    unidad_condo: int,
    lineas_cargo: list[tuple[str, str, Decimal]],
    credito_usado: Decimal,
) -> list[ReciboItem]:
    items_orm = [
        ReciboItem(condominio_id=unidad_condo, recibo_id=0, tipo_item=t, descripcion=d, monto_usd=m)
        for t, d, m in lineas_cargo
    ]
    if credito_usado > CERO:
        items_orm.append(
            ReciboItem(
                condominio_id=unidad_condo,
                recibo_id=0,
                tipo_item="ABONO_CREDITO_PREVIO",
                descripcion="Abono automático de saldo a favor disponible",
                monto_usd=-credito_usado,
            )
        )
    return items_orm


def _crear_recibo_e_items_unidad(
    unidad: Unidad,
    periodo: str,
    lineas_cargo: list[tuple[str, str, Decimal]],
    condominio_id: int = DEFAULT_CONDOMINIO_ID,
) -> tuple[Recibo, list[ReciboItem], Decimal, Decimal]:
    cargo_bruto = cuantizar(sum((m for _, _, m in lineas_cargo), CERO))
    credito_actual = _decimal_or_default(getattr(unidad, "credito_disponible_usd", None), CERO)
    monto_neto, credito_usado, credito_restante = aplicar_credito_disponible(cargo_bruto, credito_actual)
    unidad.credito_disponible_usd = credito_restante

    monto_recibo = monto_neto
    pagado_inicial = CERO
    estado_inicial = determinar_estado_recibo(monto_recibo, pagado_inicial)
    condo_raw = getattr(unidad, "condominio_id", None)
    unidad_condo = int(condominio_id if condo_raw is None else condo_raw)

    recibo = Recibo(
        condominio_id=unidad_condo,
        unidad_id=unidad.id,
        periodo=periodo,
        monto_usd=monto_recibo,
        monto_pagado_usd=pagado_inicial,
        estado=estado_inicial,
        bloqueado=False,
    )
    items_orm = _construir_items_recibo(unidad_condo, lineas_cargo, credito_usado)
    return recibo, items_orm, cargo_bruto, credito_usado


def _fusionar_recibo_existente(
    recibo: Recibo,
    unidad: Unidad,
    lineas_cargo: list[tuple[str, str, Decimal]],
    condominio_id: int,
) -> tuple[list[ReciboItem], Decimal, Decimal, str]:
    cargo_bruto = cuantizar(sum((m for _, _, m in lineas_cargo), CERO))
    pagado_previo = _decimal_or_default(getattr(recibo, "monto_pagado_usd", None), CERO)
    saldo_previo = calcular_saldo_pendiente(recibo.monto_usd, pagado_previo)
    credito_actual = _decimal_or_default(getattr(unidad, "credito_disponible_usd", None), CERO)
    _, credito_usado, credito_restante = aplicar_credito_disponible(
        cuantizar(saldo_previo + cargo_bruto), credito_actual
    )
    unidad.credito_disponible_usd = credito_restante

    estado_viejo = recibo.estado
    recibo.monto_usd = cuantizar(recibo.monto_usd + cargo_bruto - credito_usado)
    recibo.estado = determinar_estado_recibo(recibo.monto_usd, pagado_previo)
    condo_raw = getattr(recibo, "condominio_id", None)
    unidad_condo = int(condominio_id if condo_raw is None else condo_raw)
    items_orm = _construir_items_recibo(unidad_condo, lineas_cargo, credito_usado)
    return items_orm, cargo_bruto, credito_usado, estado_viejo


def _actualizar_fondo_reserva(
    fondo_reserva: FondoCondominio | None,
    modalidad: str,
    recargo_reserva: Decimal,
    superavit_fondo: Decimal,
) -> None:
    incremento = superavit_fondo if modalidad == "CUOTA_FIJA" else recargo_reserva
    if fondo_reserva is None:
        if modalidad == "CUOTA_FIJA" and incremento != CERO:
            raise ErrorFinanciero("No existe un Fondo de Reserva Legal activo para conciliar la cuota fija.")
        return
    saldo_actual = _decimal_or_default(getattr(fondo_reserva, "saldo_actual_usd", None), CERO)
    nuevo_saldo = cuantizar(saldo_actual + incremento)
    if nuevo_saldo < CERO:
        raise ErrorFinanciero("El déficit de cuota fija excede el saldo disponible en el Fondo de Reserva.")
    fondo_reserva.saldo_actual_usd = nuevo_saldo


def _motivo_auditoria_lote(periodo: str, credito_u: Decimal, es_upsert: bool) -> str:
    if es_upsert and credito_u > CERO:
        return f"Fusión facturación mensual {periodo} (crédito aplicado: -{credito_u} USD)"
    if es_upsert:
        return f"Fusión facturación mensual {periodo}"
    return f"Aplicación automática de saldo a favor en facturación {periodo} (-{credito_u} USD)"


async def _registrar_items_y_auditoria(
    db: AsyncSession,
    entradas: list[_EntradaLoteUnidad],
    periodo: str,
    condominio_id: int,
    usuario_id: int | None,
) -> None:
    for entrada in entradas:
        recibo = entrada.recibo
        if recibo.id is None:
            raise RuntimeError("El recibo no obtuvo ID primario tras flush transaccional")
        for item in entrada.items:
            item.recibo_id = recibo.id
            db.add(item)
        if not entrada.es_upsert and entrada.credito_usado <= CERO:
            continue
        motivo = _motivo_auditoria_lote(periodo, entrada.credito_usado, entrada.es_upsert)
        prev_hash, rec_hash = await sellar_cadena_worm(
            db,
            "auditoria_recibos",
            condominio_id,
            f"{recibo.id}|None|{usuario_id}|{entrada.estado_viejo}->{recibo.estado}|{motivo}",
        )
        db.add(
            AuditoriaRecibo(
                condominio_id=condominio_id,
                recibo_id=recibo.id,
                usuario_id=usuario_id,
                estado_viejo=entrada.estado_viejo,
                estado_nuevo=recibo.estado,
                motivo=motivo,
                prev_hash=prev_hash,
                record_hash=rec_hash,
            )
        )


async def cargar_contexto_facturacion(
    db: AsyncSession,
    datos: FacturarPeriodoRequest,
    condominio_id: int = DEFAULT_CONDOMINIO_ID,
) -> tuple[list[Unidad], Decimal, FondoCondominio | None, Decimal]:
    """Carga unidades, egresos comunes y fondo patrimonial del condominio para facturar el periodo."""
    uni_res = await db.execute(
        select(Unidad).where(Unidad.condominio_id == condominio_id).order_by(Unidad.id.asc()).with_for_update()
    )
    unidades = list(uni_res.scalars().all())
    if not unidades:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No existen unidades registradas para emitir la facturación.",
        )

    egr_res = await db.execute(
        select(Egreso).where(
            Egreso.condominio_id == condominio_id,
            Egreso.periodo == datos.periodo,
            Egreso.es_gasto_comun.is_(True),
        )
    )
    egresos_comunes = list(egr_res.scalars().all())
    total_egresos = cuantizar(sum((e.monto_usd for e in egresos_comunes), CERO))

    fondo_res = await db.execute(
        select(FondoCondominio)
        .where(
            FondoCondominio.condominio_id == condominio_id,
            FondoCondominio.es_activo.is_(True),
            FondoCondominio.tipo == "RESERVA_LEGAL",
        )
        .with_for_update()
    )
    fondo_reserva = fondo_res.scalars().first()
    aplica_reserva = datos.incluir_fondo_reserva and datos.modalidad != "CUOTA_FIJA"
    if aplica_reserva and fondo_reserva is None:
        raise ErrorFinanciero("No existe un Fondo de Reserva Legal activo configurado para aplicar el recargo.")
    porcentaje_reserva = fondo_reserva.porcentaje_recargo if fondo_reserva is not None else Decimal("10.00")
    recargo_reserva = cuantizar(total_egresos * (porcentaje_reserva / Decimal("100.00"))) if aplica_reserva else CERO
    return unidades, total_egresos, fondo_reserva, recargo_reserva


async def persistir_lote_facturacion(
    db: AsyncSession,
    unidades: list[Unidad],
    periodo: str,
    modalidad: str,
    items_por_unidad: dict[int, list[tuple[str, str, Decimal]]],
    fondo_reserva: FondoCondominio | None,
    recargo_reserva: Decimal,
    superavit_fondo: Decimal,
    condominio_id: int = DEFAULT_CONDOMINIO_ID,
    usuario_id: int | None = None,
) -> tuple[Decimal, Decimal, Decimal]:
    """Persiste o fusiona recibos (UPSERT), ítems, auditoría WORM y fondos en bloque transaccional."""
    prev_res = await db.execute(
        select(Recibo).where(Recibo.condominio_id == condominio_id, Recibo.periodo == periodo).with_for_update()
    )
    recibos_previos = {r.unidad_id: r for r in prev_res.scalars().all()}

    total_bruto = CERO
    total_credito = CERO
    total_neto = CERO
    entradas: list[_EntradaLoteUnidad] = []

    for u in unidades:
        lineas = items_por_unidad[u.id]
        recibo_prev = recibos_previos.get(u.id)
        if recibo_prev is not None:
            items_orm, bruto_u, credito_u, estado_viejo = _fusionar_recibo_existente(
                recibo_prev, u, lineas, condominio_id
            )
            entradas.append(_EntradaLoteUnidad(recibo_prev, items_orm, credito_u, estado_viejo, True))
        else:
            recibo, items_orm, bruto_u, credito_u = _crear_recibo_e_items_unidad(
                u, periodo, lineas, condominio_id=condominio_id
            )
            db.add(recibo)
            entradas.append(_EntradaLoteUnidad(recibo, items_orm, credito_u, "INEXISTENTE", False))
        total_bruto += bruto_u
        total_credito += credito_u
        total_neto += cuantizar(bruto_u - credito_u)

    _actualizar_fondo_reserva(fondo_reserva, modalidad, recargo_reserva, superavit_fondo)
    await db.flush()
    await _registrar_items_y_auditoria(db, entradas, periodo, condominio_id, usuario_id)
    await db.commit()
    return cuantizar(total_bruto), cuantizar(total_credito), cuantizar(total_neto)
