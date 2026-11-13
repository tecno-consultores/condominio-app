"""Motor de lote para la facturación mensual LPH por alícuota, cuota fija o partes iguales."""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.finanzas import (
    CERO,
    ESTADO_PAGADO,
    ESTADO_PENDIENTE,
    ErrorFinanciero,
    aplicar_credito_disponible,
    cuantizar,
    prorratear_partes_iguales,
    prorratear_por_alicuotas,
    validar_suma_alicuotas,
)
from src.models import (
    Egreso,
    FondoCondominio,
    Recibo,
    ReciboItem,
    ReporteMensual,
    Unidad,
)
from src.schemas import FacturarPeriodoRequest


async def verificar_periodo_facturable(db: AsyncSession, periodo: str) -> None:
    """Valida que el periodo no esté cerrado (Candado Contable) ni facturado previamente."""
    rep_res = await db.execute(select(ReporteMensual).where(ReporteMensual.periodo == periodo))
    reporte = rep_res.scalars().first()
    if reporte and reporte.estado == "CERRADO":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El periodo está cerrado por Candado Contable y no admite facturación.",
        )
    rec_res = await db.execute(select(Recibo).where(Recibo.periodo == periodo))
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
        tarifa = getattr(u, "cuota_fija_usd", None) or datos.monto_cuota_fija_usd
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
    pesos_alicuota = [(u.id, getattr(u, "alicuota", None) or Decimal("0.0000")) for u in unidades]
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
        pesos_alicuota = [(u.id, getattr(u, "alicuota", None) or Decimal("0.0000")) for u in unidades]
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


def _crear_recibo_e_items_unidad(
    unidad: Unidad,
    periodo: str,
    lineas_cargo: list[tuple[str, str, Decimal]],
) -> tuple[Recibo, list[ReciboItem], Decimal, Decimal]:
    cargo_bruto = cuantizar(sum((m for _, _, m in lineas_cargo), CERO))
    credito_actual = getattr(unidad, "credito_disponible_usd", None) or CERO
    monto_neto, credito_usado, credito_restante = aplicar_credito_disponible(cargo_bruto, credito_actual)
    unidad.credito_disponible_usd = credito_restante

    cubierto_por_credito = cargo_bruto > CERO and monto_neto == CERO
    monto_recibo = cargo_bruto if cubierto_por_credito else monto_neto
    pagado_inicial = cargo_bruto if cubierto_por_credito else CERO
    estado_inicial = ESTADO_PAGADO if (cubierto_por_credito or monto_recibo == CERO) else ESTADO_PENDIENTE

    recibo = Recibo(
        unidad_id=unidad.id,
        periodo=periodo,
        monto_usd=monto_recibo,
        monto_pagado_usd=pagado_inicial,
        estado=estado_inicial,
        bloqueado=False,
    )
    items_orm = [ReciboItem(recibo_id=0, tipo_item=t, descripcion=d, monto_usd=m) for t, d, m in lineas_cargo]
    if credito_usado > CERO:
        items_orm.append(
            ReciboItem(
                recibo_id=0,
                tipo_item="ABONO_CREDITO_PREVIO",
                descripcion="Abono automático de saldo a favor disponible",
                monto_usd=-credito_usado,
            )
        )
    return recibo, items_orm, cargo_bruto, credito_usado


async def cargar_contexto_facturacion(
    db: AsyncSession,
    datos: FacturarPeriodoRequest,
) -> tuple[list[Unidad], Decimal, FondoCondominio | None, Decimal]:
    """Carga unidades, egresos comunes y fondo patrimonial para facturar el periodo."""
    uni_res = await db.execute(select(Unidad).order_by(Unidad.id.asc()))
    unidades = list(uni_res.scalars().all())
    if not unidades:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No existen unidades registradas para emitir la facturación.",
        )

    egr_res = await db.execute(select(Egreso).where(Egreso.periodo == datos.periodo))
    egresos_comunes = [e for e in egr_res.scalars().all() if getattr(e, "es_gasto_comun", True) is not False]
    total_egresos = cuantizar(sum((e.monto_usd for e in egresos_comunes), CERO))

    fondo_res = await db.execute(
        select(FondoCondominio).where(
            FondoCondominio.es_activo.is_(True),
            FondoCondominio.tipo == "RESERVA_LEGAL",
        )
    )
    fondo_reserva = fondo_res.scalars().first()
    porcentaje_reserva = fondo_reserva.porcentaje_recargo if fondo_reserva is not None else Decimal("10.00")
    aplica_reserva = datos.incluir_fondo_reserva and datos.modalidad != "CUOTA_FIJA"
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
) -> tuple[Decimal, Decimal, Decimal]:
    """Persiste recibos, ítems y actualización de fondos en bloque transaccional."""
    total_bruto = CERO
    total_credito = CERO
    total_neto = CERO
    pares_recibo_items: list[tuple[Recibo, list[ReciboItem]]] = []

    for u in unidades:
        recibo, items_orm, bruto_u, credito_u = _crear_recibo_e_items_unidad(u, periodo, items_por_unidad[u.id])
        db.add(recibo)
        pares_recibo_items.append((recibo, items_orm))
        total_bruto += bruto_u
        total_credito += credito_u
        total_neto += cuantizar(bruto_u - credito_u)

    if fondo_reserva is not None:
        incremento_fondo = superavit_fondo if modalidad == "CUOTA_FIJA" else recargo_reserva
        fondo_reserva.saldo_actual_usd = cuantizar((fondo_reserva.saldo_actual_usd or CERO) + incremento_fondo)

    await db.flush()
    for idx, (recibo, items_orm) in enumerate(pares_recibo_items, start=1):
        rid = recibo.id or idx
        for item in items_orm:
            item.recibo_id = rid
            db.add(item)

    await db.commit()
    return cuantizar(total_bruto), cuantizar(total_credito), cuantizar(total_neto)
