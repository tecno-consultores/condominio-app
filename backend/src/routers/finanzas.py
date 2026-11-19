"""Endpoints de tesorería: tasa del día, resumen financiero, fondos, facturación LPH, solvencia y cierre de mes."""

import calendar
import hmac
import secrets
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import DEFAULT_CONDOMINIO_ID, bind_rls_tenant, get_db
from src.dependencies import (
    IdempotentAPIRoute,
    exigir_idempotencia,
    get_current_user,
    verificar_roles,
    verificar_usuario_activo,
)
from src.facturacion_lph import (
    calcular_cargos_modalidad,
    cargar_contexto_facturacion,
    persistir_lote_facturacion,
    verificar_periodo_facturable,
)
from src.finanzas import (
    CERO,
    ErrorFinanciero,
    calcular_deuda_total,
    calcular_saldo_pendiente,
    construir_qr_token_solvencia,
    convertir_a_usd,
    cuantizar,
    generar_firma_solvencia,
    verificar_firma_solvencia,
)
from src.models import (
    CertificadoSolvencia,
    ContratoOcupacion,
    Egreso,
    FondoCondominio,
    PagoReportado,
    Recibo,
    ReciboItem,
    ReporteMensual,
    TasaCambio,
    Unidad,
    Usuario,
)
from src.schemas import (
    CertificadoSolvenciaResponse,
    CierreMensualRequest,
    CierreMensualResponse,
    EgresoCreate,
    EgresoCreatedResponse,
    EstadoCobranzaItemResponse,
    FacturarPeriodoRequest,
    FacturarPeriodoResponse,
    FondoCondominioCreate,
    FondoCondominioResponse,
    ReciboDesgloseResponse,
    ReciboItemResponse,
    ResumenFinancieroResponse,
    TasaCambioCreate,
    TasaCambioResponse,
    VerificarSolvenciaResponse,
)
from src.security import get_solvency_signing_key

router = APIRouter(prefix="/api/finanzas", tags=["Finanzas"], route_class=IdempotentAPIRoute)

_ROLES_TESORERIA = ("TESORERO", "PRESIDENTE")
_ROLES_JUNTA = ("PRESIDENTE", "VICEPRESIDENTE", "TESORERO", "SECRETARIO", "VOCERO")


def _resolver_condominio_id(usuario: Usuario) -> int:
    raw = getattr(usuario, "condominio_id", None)
    return int(DEFAULT_CONDOMINIO_ID if raw is None else raw)


async def _buscar_tasa_fecha(db: AsyncSession, fecha: date | None = None) -> TasaCambio | None:
    objetivo = fecha or date.today()
    result = await db.execute(select(TasaCambio).where(TasaCambio.fecha == objetivo))
    return result.scalars().first()


@router.post(
    "/tasa",
    response_model=TasaCambioResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_idempotencia("tasa", roles=_ROLES_TESORERIA))],
    responses={
        400: {"description": "Cuerpo JSON malformado"},
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes o usuario fantasma"},
        409: {"description": "Petición duplicada (Idempotency-Key ya procesada)"},
    },
)
async def registrar_tasa(
    datos: TasaCambioCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Any:
    verificar_roles(usuario, _ROLES_TESORERIA)
    fecha_objetivo = datos.fecha or date.today()
    tasa = await _buscar_tasa_fecha(db, fecha_objetivo)
    if tasa:
        tasa.tasa_usd_ves = datos.tasa_usd_ves
    else:
        tasa = TasaCambio(fecha=fecha_objetivo, tasa_usd_ves=datos.tasa_usd_ves)
        db.add(tasa)
    await db.commit()
    await db.refresh(tasa)
    return tasa


@router.get(
    "/tasa",
    response_model=TasaCambioResponse,
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Usuario fantasma sin activar"},
        404: {"description": "Tasa del día no registrada"},
    },
)
async def obtener_tasa(
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Any:
    verificar_usuario_activo(usuario)
    tasa = await _buscar_tasa_fecha(db)
    if not tasa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La tasa de cambio del día no ha sido registrada",
        )
    return tasa


async def _validar_egreso_periodo_abierto(db: AsyncSession, periodo: str) -> None:
    rep_res = await db.execute(select(ReporteMensual).where(ReporteMensual.periodo == periodo))
    reporte = rep_res.scalars().first()
    if reporte is not None and (reporte.estado == "CERRADO" or getattr(reporte, "bloqueado", False)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El periodo está cerrado por Candado Contable; no se admiten nuevos egresos",
        )


async def _descontar_fondo_para_egreso(db: AsyncSession, condominio_id: int, monto_usd: Decimal) -> None:
    res = await db.execute(
        select(FondoCondominio)
        .where(
            FondoCondominio.condominio_id == condominio_id,
            FondoCondominio.es_activo.is_(True),
            FondoCondominio.tipo == "RESERVA_LEGAL",
        )
        .with_for_update()
    )
    fondo = res.scalars().first()
    if fondo is None:
        raise ErrorFinanciero("No existe un Fondo de Reserva Legal activo para imputar el egreso patrimonial")
    saldo_actual = cuantizar(fondo.saldo_actual_usd)
    if saldo_actual < monto_usd:
        raise ErrorFinanciero("Saldo insuficiente en el Fondo de Reserva Legal para cubrir el egreso")
    fondo.saldo_actual_usd = cuantizar(saldo_actual - monto_usd)


async def _crear_y_persistir_egreso(db: AsyncSession, datos: EgresoCreate, condo_id: int) -> Egreso:
    """Valida periodo abierto, tasa y fondo patrimonial antes de persistir el egreso."""
    await _validar_egreso_periodo_abierto(db, datos.periodo)
    tasa = await _buscar_tasa_fecha(db)
    if not tasa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La tasa de cambio del día no ha sido registrada",
        )
    monto_usd = convertir_a_usd(datos.monto, datos.moneda, tasa.tasa_usd_ves)
    # Los egresos no comunes descuentan directamente del Fondo de Reserva Legal con FOR UPDATE
    if not datos.es_gasto_comun:
        await _descontar_fondo_para_egreso(db, condo_id, monto_usd)
    egreso = Egreso(
        condominio_id=condo_id,
        periodo=datos.periodo,
        categoria=datos.categoria,
        descripcion=datos.descripcion,
        monto=datos.monto,
        moneda=datos.moneda,
        monto_usd=monto_usd,
        tasa_cambio=tasa.tasa_usd_ves,
        url_factura=datos.url_factura,
        incidencia_id=datos.incidencia_id,
        es_gasto_comun=datos.es_gasto_comun,
    )
    db.add(egreso)
    await db.commit()
    await db.refresh(egreso)
    return egreso


@router.post(
    "/egresos",
    response_model=EgresoCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_idempotencia("egreso", roles=_ROLES_TESORERIA))],
    responses={
        400: {"description": "Tasa del día no registrada, fondo insuficiente o monto inválido"},
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes o usuario fantasma"},
        409: {"description": "Periodo cerrado (Candado Contable) o Idempotency-Key repetida"},
    },
)
async def registrar_egreso(
    datos: EgresoCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> EgresoCreatedResponse:
    verificar_roles(usuario, _ROLES_TESORERIA)
    condo_id = _resolver_condominio_id(usuario)
    try:
        egreso = await _crear_y_persistir_egreso(db, datos, condo_id)
        return EgresoCreatedResponse(id=egreso.id, monto_usd=str(egreso.monto_usd))
    except HTTPException:
        raise
    except ErrorFinanciero as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en base de datos al registrar egreso",
        ) from exc


async def _obtener_recibos_resumen(
    db: AsyncSession,
    usuario: Usuario,
    periodo: str | None,
) -> list[Recibo]:
    recibo_stmt = select(Recibo).order_by(Recibo.id.asc())
    if periodo is not None:
        recibo_stmt = recibo_stmt.where(Recibo.periodo == periodo)
    rol = getattr(usuario, "rol", "")
    if rol in _ROLES_JUNTA:
        recibos_result = await db.execute(recibo_stmt)
        return list(recibos_result.scalars().all())
    if rol not in ("PROPIETARIO", "INQUILINO"):
        return []
    contratos_res = await db.execute(
        select(ContratoOcupacion.unidad_id).where(
            ContratoOcupacion.usuario_id == usuario.id,
            ContratoOcupacion.es_activo.is_(True),
            ContratoOcupacion.fecha_fin.is_(None),
        )
    )
    unidades_propias = list(contratos_res.scalars().all())
    if not unidades_propias:
        return []
    recibos_result = await db.execute(recibo_stmt.where(Recibo.unidad_id.in_(unidades_propias)))
    return list(recibos_result.scalars().all())


async def _resumir_egresos_por_categoria(db: AsyncSession, periodo: str | None) -> tuple[Decimal, dict[str, str]]:
    stmt = select(Egreso.categoria, func.coalesce(func.sum(Egreso.monto_usd), CERO)).group_by(Egreso.categoria)
    if periodo is not None:
        stmt = stmt.where(Egreso.periodo == periodo)
    egresos_result = await db.execute(stmt)
    total_egresos = Decimal("0.00")
    gastos_por_categoria: dict[str, str] = {}
    for categoria, monto_sumado in egresos_result.all():
        monto_q = cuantizar(Decimal(str(CERO if monto_sumado is None else monto_sumado)))
        total_egresos += monto_q
        gastos_por_categoria[str(categoria)] = str(monto_q)
    return cuantizar(total_egresos), gastos_por_categoria


def _construir_item_cobranza(recibo: Recibo) -> EstadoCobranzaItemResponse:
    return EstadoCobranzaItemResponse(
        recibo_id=recibo.id,
        unidad_id=recibo.unidad_id,
        periodo=recibo.periodo,
        monto_usd=str(cuantizar(recibo.monto_usd)),
        estado=recibo.estado,
        saldo_usd=str(calcular_saldo_pendiente(recibo.monto_usd, recibo.monto_pagado_usd)),
    )


@router.get(
    "/resumen",
    response_model=ResumenFinancieroResponse,
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Usuario fantasma sin activar"},
    },
)
async def resumen_financiero(
    periodo: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ResumenFinancieroResponse:
    verificar_usuario_activo(usuario)
    # Se consultan recibos antes que egresos para respetar el aislamiento por rol y el orden de sesión
    recibos = await _obtener_recibos_resumen(db, usuario, periodo)
    deuda_total = calcular_deuda_total([(r.monto_usd, r.monto_pagado_usd) for r in recibos])
    total_egresos, gastos_por_categoria = await _resumir_egresos_por_categoria(db, periodo)

    return ResumenFinancieroResponse(
        deuda_total_usd=str(cuantizar(deuda_total)),
        total_egresos_usd=str(total_egresos),
        gastos_por_categoria=gastos_por_categoria,
        estado_cobranza=[_construir_item_cobranza(r) for r in recibos],
    )


async def _validar_cierre_disponible(
    db: AsyncSession,
    condo_id: int,
    periodo: str,
) -> ReporteMensual | None:
    """Verifica que el periodo no esté cerrado ni tenga pagos en revisión pendientes en ese mismo periodo."""
    result = await db.execute(
        select(ReporteMensual)
        .where(ReporteMensual.condominio_id == condo_id, ReporteMensual.periodo == periodo)
        .with_for_update()
    )
    reporte = result.scalars().first()
    if reporte and reporte.estado == "CERRADO":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El mes ya fue cerrado (acción inmutable)",
        )

    # Aísla la validación por periodo mediante JOIN con Recibo para no bloquear otros meses
    pagos_rev = await db.execute(
        select(PagoReportado.id)
        .join(Recibo, PagoReportado.recibo_id == Recibo.id)
        .where(
            PagoReportado.condominio_id == condo_id,
            PagoReportado.estado == "EN_REVISION",
            Recibo.periodo == periodo,
        )
        .limit(1)
    )
    if pagos_rev.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede ejecutar el cierre mensual mientras existan pagos en revisión.",
        )
    return reporte


_BloqueableT = TypeVar("_BloqueableT", Recibo, Egreso)


async def _bloquear_periodo_modelo(
    db: AsyncSession,
    modelo: type[_BloqueableT],
    condo_id: int,
    periodo: str,
) -> None:
    res = await db.execute(
        select(modelo).where(modelo.condominio_id == condo_id, modelo.periodo == periodo).with_for_update()
    )
    for fila in res.scalars().all():
        fila.bloqueado = True


@router.post(
    "/cierre-mensual",
    response_model=CierreMensualResponse,
    dependencies=[Depends(exigir_idempotencia("cierre_mensual", roles=_ROLES_TESORERIA))],
    responses={
        400: {"description": "Cuerpo JSON malformado"},
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes o usuario fantasma"},
        409: {"description": "El mes ya fue cerrado o existen pagos en revisión"},
    },
)
async def cierre_mensual(
    datos: CierreMensualRequest,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> CierreMensualResponse:
    verificar_roles(usuario, _ROLES_TESORERIA)
    condo_id = _resolver_condominio_id(usuario)
    reporte = await _validar_cierre_disponible(db, condo_id, datos.periodo)
    if reporte is None:
        reporte = ReporteMensual(condominio_id=condo_id, periodo=datos.periodo, estado="PRELIMINAR")
        db.add(reporte)

    await _bloquear_periodo_modelo(db, Recibo, condo_id, datos.periodo)
    await _bloquear_periodo_modelo(db, Egreso, condo_id, datos.periodo)

    reporte.estado = "CERRADO"
    reporte.cerrado_en = datetime.now(UTC)
    await db.commit()
    return CierreMensualResponse(periodo=datos.periodo, estado="CERRADO")


@router.post(
    "/fondos",
    response_model=FondoCondominioResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_idempotencia("crear_fondo", roles=_ROLES_TESORERIA))],
    responses={
        400: {"description": "Cuerpo JSON malformado"},
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes"},
        409: {"description": "Fondo duplicado o Idempotency-Key repetida"},
    },
)
async def crear_fondo_condominio(
    datos: FondoCondominioCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> FondoCondominio:
    """Registra un fondo patrimonial del condominio (Reserva Legal, Caja Chica o Especial)."""
    verificar_roles(usuario, _ROLES_TESORERIA)

    existente = await db.execute(select(FondoCondominio).where(FondoCondominio.nombre == datos.nombre.strip()))
    if existente.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un fondo patrimonial con ese nombre.",
        )

    fondo = FondoCondominio(
        nombre=datos.nombre.strip(),
        tipo=datos.tipo,
        porcentaje_recargo=cuantizar(datos.porcentaje_recargo),
        saldo_actual_usd=CERO,
        es_activo=True,
    )
    db.add(fondo)
    await db.commit()
    await db.refresh(fondo)
    return fondo


@router.get(
    "/fondos",
    response_model=list[FondoCondominioResponse],
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Usuario fantasma sin activar"},
    },
)
async def listar_fondos_condominio(
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> list[FondoCondominio]:
    """Lista los fondos patrimoniales activos del condominio y sus saldos en USD."""
    verificar_usuario_activo(usuario)
    res = await db.execute(
        select(FondoCondominio)
        .where(FondoCondominio.es_activo.is_(True))
        .order_by(FondoCondominio.id.asc())
        .limit(limit)
        .offset(offset)
    )
    return list(res.scalars().all())


@router.post(
    "/facturar-periodo",
    response_model=FacturarPeriodoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_idempotencia("facturar", roles=_ROLES_TESORERIA))],
    responses={
        400: {"description": "Sin unidades o configuración de alícuotas/cuota fija/fondo inválida"},
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes"},
        409: {"description": "Periodo ya facturado, bloqueado por Candado Contable o Idempotency-Key repetida"},
    },
)
async def facturar_periodo(
    datos: FacturarPeriodoRequest,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> FacturarPeriodoResponse:
    """Emite atómicamente los recibos del periodo (ALICUOTA, CUOTA_FIJA o PARTES_IGUALES) y su desglose LPH."""
    verificar_roles(usuario, _ROLES_TESORERIA)

    condo_id = _resolver_condominio_id(usuario)
    await verificar_periodo_facturable(db, datos.periodo, condominio_id=condo_id)

    try:
        unidades, total_egresos, fondo_reserva, recargo_reserva = await cargar_contexto_facturacion(
            db, datos, condominio_id=condo_id
        )
        items_por_unidad, superavit_fondo = calcular_cargos_modalidad(datos, unidades, total_egresos, recargo_reserva)
        total_bruto, total_credito, total_neto = await persistir_lote_facturacion(
            db,
            unidades,
            datos.periodo,
            datos.modalidad,
            items_por_unidad,
            fondo_reserva,
            recargo_reserva,
            superavit_fondo,
            condominio_id=condo_id,
            usuario_id=usuario.id,
        )
    except ErrorFinanciero as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El periodo {datos.periodo} ya posee recibos emitidos",
        ) from exc

    return FacturarPeriodoResponse(
        periodo=datos.periodo,
        modalidad=datos.modalidad,
        recibos_emitidos=len(unidades),
        total_egresos_comunes_usd=total_egresos,
        recargo_fondo_reserva_usd=recargo_reserva,
        cuota_extraordinaria_total_usd=cuantizar(datos.cuota_extraordinaria_total_usd),
        total_facturado_bruto_usd=total_bruto,
        total_credito_descontado_usd=total_credito,
        total_facturado_neto_usd=total_neto,
        superavit_conciliado_fondo_usd=superavit_fondo,
    )


async def _verificar_acceso_unidad(db: AsyncSession, usuario: Usuario, unidad_id: int) -> None:
    if getattr(usuario, "rol", "") in _ROLES_JUNTA:
        return
    res = await db.execute(
        select(ContratoOcupacion).where(
            ContratoOcupacion.usuario_id == usuario.id,
            ContratoOcupacion.unidad_id == unidad_id,
            ContratoOcupacion.es_activo.is_(True),
            ContratoOcupacion.fecha_fin.is_(None),
        )
    )
    if res.scalars().first() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene autorización para consultar o emitir documentos de esta unidad.",
        )


async def _cargar_info_unidad(db: AsyncSession, unidad_id: int) -> tuple[str, Decimal]:
    uni_res = await db.execute(select(Unidad).where(Unidad.id == unidad_id))
    unidad = uni_res.scalars().first()
    if unidad is None:
        return f"UNIDAD-{unidad_id}", Decimal("0.0000")
    alicuota_raw = getattr(unidad, "alicuota", None)
    return unidad.identificador, Decimal("0.0000") if alicuota_raw is None else alicuota_raw


def _calcular_credito_descontado(items: list[ReciboItem]) -> Decimal:
    total = CERO
    for it in items:
        if it.tipo_item == "ABONO_CREDITO_PREVIO" and it.monto_usd < CERO:
            total -= it.monto_usd
    return cuantizar(total)


@router.get(
    "/recibos/{recibo_id}/desglose",
    response_model=ReciboDesgloseResponse,
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "No autorizado para esta unidad"},
        404: {"description": "Recibo o unidad no encontrada"},
    },
)
async def obtener_desglose_recibo(
    recibo_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ReciboDesgloseResponse:
    """Devuelve el desglose línea por línea (ReciboItem) de un recibo de condominio."""
    verificar_usuario_activo(usuario)

    rec_res = await db.execute(select(Recibo).where(Recibo.id == recibo_id))
    recibo = rec_res.scalars().first()
    if not recibo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recibo no encontrado.")

    await _verificar_acceso_unidad(db, usuario, recibo.unidad_id)
    identificador, alicuota = await _cargar_info_unidad(db, recibo.unidad_id)

    items_res = await db.execute(
        select(ReciboItem).where(ReciboItem.recibo_id == recibo.id).order_by(ReciboItem.id.asc())
    )
    items = list(items_res.scalars().all())
    credito_desc = _calcular_credito_descontado(items)

    return ReciboDesgloseResponse(
        recibo_id=recibo.id,
        unidad_id=recibo.unidad_id,
        identificador_unidad=identificador,
        alicuota_aplicada=alicuota,
        periodo=recibo.periodo,
        monto_usd=cuantizar(recibo.monto_usd),
        monto_pagado_usd=cuantizar(recibo.monto_pagado_usd),
        saldo_pendiente_usd=calcular_saldo_pendiente(recibo.monto_usd, recibo.monto_pagado_usd),
        credito_descontado_usd=credito_desc,
        estado=recibo.estado,
        bloqueado=recibo.bloqueado,
        items=[ReciboItemResponse.model_validate(it) for it in items],
    )


def _fin_de_mes(fecha_base: date) -> date:
    ultimo_dia = calendar.monthrange(fecha_base.year, fecha_base.month)[1]
    return date(fecha_base.year, fecha_base.month, ultimo_dia)


async def _obtener_deuda_viva_unidad(db: AsyncSession, unidad_id: int) -> Decimal:
    """Calcula en SQL la deuda viva total (> 0.00) de una unidad sobre recibos no pagados."""
    stmt = select(
        func.coalesce(func.sum(Recibo.monto_usd - Recibo.monto_pagado_usd), CERO),
    ).where(Recibo.unidad_id == unidad_id, Recibo.estado != "PAGADO")
    res = await db.execute(stmt)
    raw = res.scalars().first()
    deuda = cuantizar(Decimal(str(raw if raw is not None else CERO)))
    return max(CERO, deuda)


@router.post(
    "/solvencia/{unidad_id}",
    response_model=CertificadoSolvenciaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_idempotencia("solvencia:{unidad_id}"))],
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "No autorizado para esta unidad"},
        404: {"description": "Unidad no encontrada"},
        409: {"description": "La unidad presenta deuda pendiente o Idempotency-Key repetida"},
    },
)
async def emitir_certificado_solvencia(
    unidad_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> CertificadoSolvenciaResponse:
    """Verifica deuda cero ($0.00 USD) y emite un Certificado de Solvencia firmado con HMAC-SHA256 y JTI."""
    verificar_usuario_activo(usuario)
    await _verificar_acceso_unidad(db, usuario, unidad_id)

    uni_res = await db.execute(select(Unidad).where(Unidad.id == unidad_id))
    unidad = uni_res.scalars().first()
    if not unidad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidad no encontrada.")

    deuda = await _obtener_deuda_viva_unidad(db, unidad_id)
    if deuda > CERO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La unidad presenta deuda pendiente de {deuda} USD y no puede emitir Certificado de Solvencia.",
        )

    hoy = date.today()
    vencimiento = _fin_de_mes(hoy)
    sufijo = secrets.token_hex(2).upper()
    folio = f"SOLV-{hoy.strftime('%Y%m')}-{unidad.id:04d}-{sufijo}"
    cert_jti = str(uuid.uuid4())
    firma = generar_firma_solvencia(
        folio,
        unidad.identificador,
        vencimiento.isoformat(),
        get_solvency_signing_key(),
        jti=cert_jti,
    )
    ahora = datetime.now(UTC)

    cert = CertificadoSolvencia(
        jti=cert_jti,
        folio=folio,
        unidad_id=unidad.id,
        emitido_por_id=usuario.id,
        fecha_emision=ahora,
        fecha_vencimiento=vencimiento,
        deuda_verificada_usd=CERO,
        firma_hmac=firma,
    )
    db.add(cert)
    await db.commit()
    await db.refresh(cert)

    qr_token = construir_qr_token_solvencia(folio, unidad.identificador, vencimiento.isoformat(), firma, jti=cert_jti)
    return CertificadoSolvenciaResponse(
        id=cert.id or 1,
        jti=cert.jti,
        folio=cert.folio,
        unidad_id=cert.unidad_id,
        identificador_unidad=unidad.identificador,
        emitido_por_id=cert.emitido_por_id,
        fecha_emision=cert.fecha_emision or ahora,
        fecha_vencimiento=cert.fecha_vencimiento,
        deuda_verificada_usd=CERO,
        firma_hmac=cert.firma_hmac,
        qr_token=qr_token,
    )


def _validar_firma_certificado(
    cert: CertificadoSolvencia,
    identificador: str,
    sig: str,
    cert_jti: str,
) -> None:
    """Compara la firma HMAC-SHA256 en tiempo constante para rechazar adulteraciones."""
    es_valida = verificar_firma_solvencia(
        cert.folio,
        identificador,
        cert.fecha_vencimiento.isoformat(),
        sig,
        get_solvency_signing_key(),
        jti=cert_jti or None,
    )
    if not es_valida or not hmac.compare_digest(sig.strip(), cert.firma_hmac):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Firma criptográfica de solvencia inválida o adulterada.",
        )


@router.get(
    "/solvencia/verificar/{folio}",
    response_model=VerificarSolvenciaResponse,
    responses={
        400: {"description": "Firma criptográfica inválida"},
        404: {"description": "Folio de solvencia no encontrado"},
    },
)
async def verificar_certificado_solvencia(
    folio: str,
    sig: str = Query(..., min_length=1, description="Firma HMAC-SHA256 del certificado"),
    db: AsyncSession = Depends(get_db),
) -> VerificarSolvenciaResponse:
    """Verifica públicamente la autenticidad criptográfica y la vigencia viva sin deuda del Certificado."""
    # Endpoint público sin JWT: fija contexto RLS por defecto para consultar certificados
    await bind_rls_tenant(db, DEFAULT_CONDOMINIO_ID)
    cert_res = await db.execute(select(CertificadoSolvencia).where(CertificadoSolvencia.folio == folio.strip()))
    cert = cert_res.scalars().first()
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado de solvencia no encontrado.",
        )

    identificador, _ = await _cargar_info_unidad(db, cert.unidad_id)
    cert_jti = getattr(cert, "jti", None) or ""
    _validar_firma_certificado(cert, identificador, sig, cert_jti)

    deuda_viva = await _obtener_deuda_viva_unidad(db, cert.unidad_id)
    vigente = cert.fecha_vencimiento >= date.today() and deuda_viva == CERO

    return VerificarSolvenciaResponse(
        valido=True,
        jti=cert_jti,
        folio=cert.folio,
        unidad_id=cert.unidad_id,
        identificador_unidad=identificador,
        fecha_vencimiento=cert.fecha_vencimiento,
        vigente=vigente,
        deuda_verificada_usd=deuda_viva,
        firma_hmac=cert.firma_hmac,
    )
