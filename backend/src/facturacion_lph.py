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


def _obtener_pesos_alicuota_validados(unidades: list[Unidad]) -> list[tuple[int, Decimal]]:
    """Extrae pares (unidad_id, alícuota) y exige suma válida de 100.0000%."""
    pesos_alicuota = [(u.id, _decimal_or_default(getattr(u, "alicuota", None), Decimal("0.0000"))) for u in unidades]
    if not validar_suma_alicuotas([peso for _, peso in pesos_alicuota]):
        raise ErrorFinanciero("La suma de alícuotas de las unidades debe equivaler a 100.0000% antes de facturar")
    return pesos_alicuota


def _prorratear_por_modalidad(
    modalidad: str,
    monto: Decimal,
    unidades: list[Unidad],
) -> dict[int, Decimal]:
    """Prorratea un monto por alícuotas o partes iguales según la modalidad del lote."""
    if modalidad == "ALICUOTA":
        return prorratear_por_alicuotas(monto, _obtener_pesos_alicuota_validados(unidades))
    return prorratear_partes_iguales(monto, [u.id for u in unidades])


def _lineas_cargo_variable(
    periodo: str,
    gasto_comun: Decimal,
    reserva: Decimal,
) -> list[tuple[str, str, Decimal]]:
    """Arma las líneas de gasto común y aporte al fondo de reserva para una unidad."""
    lineas: list[tuple[str, str, Decimal]] = [
        ("GASTO_COMUN", f"Cuota parte de gastos comunes ({periodo})", gasto_comun)
    ]
    if reserva > CERO:
        lineas.append(("FONDO_RESERVA", "Aporte al Fondo de Reserva Legal", reserva))
    return lineas


def _cargos_variables(
    datos: FacturarPeriodoRequest,
    unidades: list[Unidad],
    total_egresos_comunes: Decimal,
    recargo_reserva_total: Decimal,
) -> dict[int, list[tuple[str, str, Decimal]]]:
    mapa_gastos = _prorratear_por_modalidad(datos.modalidad, total_egresos_comunes, unidades)
    mapa_reserva = _prorratear_por_modalidad(datos.modalidad, recargo_reserva_total, unidades)
    return {u.id: _lineas_cargo_variable(datos.periodo, mapa_gastos[u.id], mapa_reserva[u.id]) for u in unidades}


def _anexar_cuota_extraordinaria(
    datos: FacturarPeriodoRequest,
    unidades: list[Unidad],
    items_por_unidad: dict[int, list[tuple[str, str, Decimal]]],
) -> None:
    if datos.cuota_extraordinaria_total_usd <= CERO:
        return
    mapa_extra = _prorratear_por_modalidad(datos.modalidad, datos.cuota_extraordinaria_total_usd, unidades)
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


def _validar_fondo_ausente(modalidad: str, superavit_fondo: Decimal) -> None:
    """Rechaza conciliación de cuota fija con superávit/déficit si no hay fondo de reserva activo."""
    if modalidad == "CUOTA_FIJA" and superavit_fondo != CERO:
        raise ErrorFinanciero("No existe un Fondo de Reserva Legal activo para conciliar la cuota fija.")


def _actualizar_fondo_reserva(
    fondo_reserva: FondoCondominio | None,
    modalidad: str,
    recargo_reserva: Decimal,
    superavit_fondo: Decimal,
) -> None:
    if fondo_reserva is None:
        _validar_fondo_ausente(modalidad, superavit_fondo)
        return
    incremento = superavit_fondo if modalidad == "CUOTA_FIJA" else recargo_reserva
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


@dataclass(frozen=True)
class _ContextoAuditoriaLote:
    """Metadatos del lote necesarios para registrar la auditoría WORM de recibos."""

    periodo: str
    condominio_id: int
    usuario_id: int | None


def _obtener_id_recibo(recibo: Recibo) -> int:
    """Verifica y retorna la clave primaria del recibo tras el flush transaccional."""
    if recibo.id is None:
        raise RuntimeError("El recibo no obtuvo ID primario tras flush transaccional")
    return recibo.id


def _anexar_items_recibo(db: AsyncSession, recibo_id: int, items: list[ReciboItem]) -> None:
    """Asocia el recibo_id persistido a cada ítem y los encola en la sesión."""
    for item in items:
        item.recibo_id = recibo_id
        db.add(item)


async def _registrar_auditoria_entrada(
    db: AsyncSession,
    entrada: _EntradaLoteUnidad,
    ctx: _ContextoAuditoriaLote,
) -> None:
    """Sella en cadena WORM las entradas de lote con fusión UPSERT o crédito aplicado."""
    if not entrada.es_upsert and entrada.credito_usado <= CERO:
        return
    recibo = entrada.recibo
    recibo_id = _obtener_id_recibo(recibo)
    motivo = _motivo_auditoria_lote(ctx.periodo, entrada.credito_usado, entrada.es_upsert)
    prev_hash, rec_hash = await sellar_cadena_worm(
        db,
        "auditoria_recibos",
        ctx.condominio_id,
        f"{recibo_id}|None|{ctx.usuario_id}|{entrada.estado_viejo}->{recibo.estado}|{motivo}",
    )
    db.add(
        AuditoriaRecibo(
            condominio_id=ctx.condominio_id,
            recibo_id=recibo_id,
            usuario_id=ctx.usuario_id,
            estado_viejo=entrada.estado_viejo,
            estado_nuevo=recibo.estado,
            motivo=motivo,
            prev_hash=prev_hash,
            record_hash=rec_hash,
        )
    )


async def _registrar_items_y_auditoria(
    db: AsyncSession,
    entradas: list[_EntradaLoteUnidad],
    periodo: str,
    condominio_id: int,
    usuario_id: int | None,
) -> None:
    ctx = _ContextoAuditoriaLote(periodo=periodo, condominio_id=condominio_id, usuario_id=usuario_id)
    for entrada in entradas:
        recibo_id = _obtener_id_recibo(entrada.recibo)
        _anexar_items_recibo(db, recibo_id, entrada.items)
        await _registrar_auditoria_entrada(db, entrada, ctx)


async def _cargar_unidades_y_egresos(
    db: AsyncSession,
    periodo: str,
    condominio_id: int,
) -> tuple[list[Unidad], Decimal]:
    """Carga con bloqueo las unidades del condominio y suma los egresos comunes del periodo."""
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
            Egreso.periodo == periodo,
            Egreso.es_gasto_comun.is_(True),
        )
    )
    total_egresos = cuantizar(sum((e.monto_usd for e in egr_res.scalars().all()), CERO))
    return unidades, total_egresos


async def _cargar_fondo_y_recargo(
    db: AsyncSession,
    datos: FacturarPeriodoRequest,
    total_egresos: Decimal,
    condominio_id: int,
) -> tuple[FondoCondominio | None, Decimal]:
    """Consulta el fondo de reserva legal activo y calcula el recargo aplicable."""
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
    if not aplica_reserva:
        return fondo_reserva, CERO
    if fondo_reserva is None:
        raise ErrorFinanciero("No existe un Fondo de Reserva Legal activo configurado para aplicar el recargo.")
    recargo_reserva = cuantizar(total_egresos * (fondo_reserva.porcentaje_recargo / Decimal("100.00")))
    return fondo_reserva, recargo_reserva


async def cargar_contexto_facturacion(
    db: AsyncSession,
    datos: FacturarPeriodoRequest,
    condominio_id: int = DEFAULT_CONDOMINIO_ID,
) -> tuple[list[Unidad], Decimal, FondoCondominio | None, Decimal]:
    """Carga unidades, egresos comunes y fondo patrimonial del condominio para facturar el periodo."""
    unidades, total_egresos = await _cargar_unidades_y_egresos(db, datos.periodo, condominio_id)
    fondo_reserva, recargo_reserva = await _cargar_fondo_y_recargo(db, datos, total_egresos, condominio_id)
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
