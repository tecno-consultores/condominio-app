"""Endpoints de tesorería: tasa del día, resumen financiero, fondos, facturación LPH, solvencia y cierre de mes."""

import calendar
import secrets
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import get_db
from src.dependencies import get_current_user, verificar_roles, verificar_usuario_activo
from src.finanzas import (
    CERO,
    ESTADO_PAGADO,
    ESTADO_PENDIENTE,
    ErrorFinanciero,
    aplicar_credito_disponible,
    calcular_deuda_total,
    calcular_saldo_pendiente,
    construir_qr_token_solvencia,
    convertir_a_usd,
    cuantizar,
    generar_firma_solvencia,
    prorratear_partes_iguales,
    prorratear_por_alicuotas,
    verificar_firma_solvencia,
)
from src.models import (
    CertificadoSolvencia,
    ContratoOcupacion,
    Egreso,
    FondoCondominio,
    Recibo,
    ReciboItem,
    ReporteMensual,
    TasaCambio,
    Unidad,
    Usuario,
)
from src.redis_client import check_and_set_idempotency_key, get_redis_client
from src.schemas import (
    CertificadoSolvenciaResponse,
    CierreMensualRequest,
    EgresoCreate,
    FacturarPeriodoRequest,
    FacturarPeriodoResponse,
    FondoCondominioCreate,
    FondoCondominioResponse,
    ReciboDesgloseResponse,
    ReciboItemResponse,
    TasaCambioCreate,
    TasaCambioResponse,
    VerificarSolvenciaResponse,
)
from src.security import SECRET_KEY

router = APIRouter(prefix="/api/finanzas", tags=["Finanzas"])

_ROLES_TESORERIA = ("TESORERO", "PRESIDENTE")
_ROLES_JUNTA = ("PRESIDENTE", "VICEPRESIDENTE", "TESORERO", "SECRETARIO", "VOCERO")


@router.post(
    "/tasa",
    response_model=TasaCambioResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Cuerpo JSON malformado"},
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes o usuario fantasma"},
    },
)
async def registrar_tasa(
    datos: TasaCambioCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Any:
    verificar_roles(usuario, _ROLES_TESORERIA)
    fecha_objetivo = datos.fecha or date.today()
    result = await db.execute(select(TasaCambio).where(TasaCambio.fecha == fecha_objetivo))
    tasa = result.scalars().first()
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
    result = await db.execute(select(TasaCambio).where(TasaCambio.fecha == date.today()))
    tasa = result.scalars().first()
    if not tasa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La tasa de cambio del día no ha sido registrada",
        )
    return tasa


@router.post(
    "/egresos",
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Tasa del día no registrada o monto inválido"},
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes o usuario fantasma"},
    },
)
async def registrar_egreso(
    datos: EgresoCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> dict[str, Any]:
    verificar_roles(usuario, _ROLES_TESORERIA)
    try:
        tasa_result = await db.execute(select(TasaCambio).where(TasaCambio.fecha == date.today()))
        tasa = tasa_result.scalars().first()
        if not tasa:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La tasa de cambio del día no ha sido registrada",
            )
        monto_usd = convertir_a_usd(datos.monto, datos.moneda, tasa.tasa_usd_ves)
        egreso = Egreso(
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
        return {"id": egreso.id, "monto_usd": str(egreso.monto_usd)}
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


@router.get(
    "/resumen",
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Usuario fantasma sin activar"},
    },
)
async def resumen_financiero(
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> dict[str, Any]:
    verificar_usuario_activo(usuario)
    recibos_result = await db.execute(select(Recibo))
    recibos = list(recibos_result.scalars().all())
    deuda_total = calcular_deuda_total([(r.monto_usd, r.monto_pagado_usd) for r in recibos])

    egresos_result = await db.execute(select(Egreso))
    egresos = list(egresos_result.scalars().all())
    total_egresos = Decimal("0.00")
    gastos_por_categoria: dict[str, Decimal] = {}
    for egreso in egresos:
        total_egresos += egreso.monto_usd
        gastos_por_categoria[egreso.categoria] = (
            gastos_por_categoria.get(egreso.categoria, Decimal("0.00")) + egreso.monto_usd
        )

    return {
        "deuda_total_usd": str(cuantizar(deuda_total)),
        "total_egresos_usd": str(cuantizar(total_egresos)),
        "gastos_por_categoria": {clave: str(cuantizar(valor)) for clave, valor in gastos_por_categoria.items()},
        "estado_cobranza": [
            {
                "recibo_id": r.id,
                "unidad_id": r.unidad_id,
                "periodo": r.periodo,
                "monto_usd": str(cuantizar(r.monto_usd)),
                "estado": r.estado,
                "saldo_usd": str(calcular_saldo_pendiente(r.monto_usd, r.monto_pagado_usd)),
            }
            for r in recibos
        ],
    }


@router.post(
    "/cierre-mensual",
    responses={
        400: {"description": "Cuerpo JSON malformado"},
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes o usuario fantasma"},
        409: {"description": "El mes ya fue cerrado (acción inmutable)"},
    },
)
async def cierre_mensual(
    datos: CierreMensualRequest,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> dict[str, Any]:
    verificar_roles(usuario, _ROLES_TESORERIA)
    result = await db.execute(select(ReporteMensual).where(ReporteMensual.periodo == datos.periodo))
    reporte = result.scalars().first()
    if reporte and reporte.estado == "CERRADO":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El mes ya fue cerrado (acción inmutable)",
        )
    if reporte is None:
        reporte = ReporteMensual(periodo=datos.periodo, estado="PRELIMINAR")
        db.add(reporte)

    recibos_result = await db.execute(select(Recibo).where(Recibo.periodo == datos.periodo))
    for recibo in recibos_result.scalars().all():
        recibo.bloqueado = True

    egresos_result = await db.execute(select(Egreso).where(Egreso.periodo == datos.periodo))
    for egreso in egresos_result.scalars().all():
        egreso.bloqueado = True

    reporte.estado = "CERRADO"
    reporte.cerrado_en = datetime.now(UTC)
    await db.commit()
    return {"periodo": datos.periodo, "estado": "CERRADO"}


@router.post(
    "/fondos",
    response_model=FondoCondominioResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"description": "Permisos insuficientes"},
        409: {"description": "Fondo duplicado o Idempotency-Key repetida"},
    },
)
async def crear_fondo_condominio(
    datos: FondoCondominioCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1),
    db: AsyncSession = Depends(get_db),
    redis_client: Any = Depends(get_redis_client),
    usuario: Usuario = Depends(get_current_user),
) -> FondoCondominio:
    """Registra un fondo patrimonial del condominio (Reserva Legal, Caja Chica o Especial)."""
    verificar_roles(usuario, _ROLES_TESORERIA)

    es_nueva = await check_and_set_idempotency_key(
        redis_client,
        idempotency_key,
        scope=f"crear_fondo:{usuario.id}",
    )
    if not es_nueva:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta creación de fondo ya fue procesada.",
        )

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
    responses={403: {"description": "Usuario fantasma sin activar"}},
)
async def listar_fondos_condominio(
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> list[FondoCondominio]:
    """Lista los fondos patrimoniales activos del condominio y sus saldos en USD."""
    verificar_usuario_activo(usuario)
    res = await db.execute(
        select(FondoCondominio).where(FondoCondominio.es_activo.is_(True)).order_by(FondoCondominio.id.asc())
    )
    return list(res.scalars().all())


async def _verificar_periodo_facturable(db: AsyncSession, periodo: str) -> None:
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
    unidad_ids: list[int],
    items_por_unidad: dict[int, list[tuple[str, str, Decimal]]],
) -> None:
    if datos.cuota_extraordinaria_total_usd <= CERO:
        return
    mapa_extra = prorratear_partes_iguales(datos.cuota_extraordinaria_total_usd, unidad_ids)
    desc_extra = datos.descripcion_cuota_extraordinaria or "Cuota extraordinaria aprobada"
    for uid, monto_extra in mapa_extra.items():
        items_por_unidad[uid].append(("CUOTA_EXTRAORDINARIA", desc_extra, monto_extra))


def _calcular_cargos_modalidad(
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

    _anexar_cuota_extraordinaria(datos, [u.id for u in unidades], items_por_unidad)
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
    items_orm = [
        ReciboItem(recibo_id=0, tipo_item=t, descripcion=d, monto_usd=m) for t, d, m in lineas_cargo
    ]
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


async def _cargar_contexto_facturacion(
    db: AsyncSession,
    datos: FacturarPeriodoRequest,
) -> tuple[list[Unidad], Decimal, FondoCondominio | None, Decimal]:
    uni_res = await db.execute(select(Unidad).order_by(Unidad.id.asc()))
    unidades = list(uni_res.scalars().all())
    if not unidades:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No existen unidades registradas para emitir la facturación.",
        )

    egr_res = await db.execute(select(Egreso).where(Egreso.periodo == datos.periodo))
    egresos_comunes = [
        e for e in egr_res.scalars().all() if getattr(e, "es_gasto_comun", True) is not False
    ]
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


async def _persistir_lote_facturacion(
    db: AsyncSession,
    unidades: list[Unidad],
    periodo: str,
    modalidad: str,
    items_por_unidad: dict[int, list[tuple[str, str, Decimal]]],
    fondo_reserva: FondoCondominio | None,
    recargo_reserva: Decimal,
    superavit_fondo: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    total_bruto = CERO
    total_credito = CERO
    total_neto = CERO
    pares_recibo_items: list[tuple[Recibo, list[ReciboItem]]] = []

    for u in unidades:
        recibo, items_orm, bruto_u, credito_u = _crear_recibo_e_items_unidad(
            u, periodo, items_por_unidad[u.id]
        )
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


@router.post(
    "/facturar-periodo",
    response_model=FacturarPeriodoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Sin unidades o configuración de alícuotas/cuota fija inválida"},
        403: {"description": "Permisos insuficientes"},
        409: {"description": "Periodo ya facturado, bloqueado por Candado Contable o Idempotency-Key repetida"},
    },
)
async def facturar_periodo(
    datos: FacturarPeriodoRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1),
    db: AsyncSession = Depends(get_db),
    redis_client: Any = Depends(get_redis_client),
    usuario: Usuario = Depends(get_current_user),
) -> FacturarPeriodoResponse:
    """Emite atómicamente los recibos del periodo (ALICUOTA, CUOTA_FIJA o PARTES_IGUALES) y su desglose LPH."""
    verificar_roles(usuario, _ROLES_TESORERIA)

    es_nueva = await check_and_set_idempotency_key(
        redis_client,
        idempotency_key,
        scope=f"facturar:{datos.periodo}",
    )
    if not es_nueva:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta facturación mensual ya fue procesada.",
        )

    await _verificar_periodo_facturable(db, datos.periodo)
    unidades, total_egresos, fondo_reserva, recargo_reserva = await _cargar_contexto_facturacion(db, datos)

    try:
        items_por_unidad, superavit_fondo = _calcular_cargos_modalidad(
            datos, unidades, total_egresos, recargo_reserva
        )
    except ErrorFinanciero as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    total_bruto, total_credito, total_neto = await _persistir_lote_facturacion(
        db,
        unidades,
        datos.periodo,
        datos.modalidad,
        items_por_unidad,
        fondo_reserva,
        recargo_reserva,
        superavit_fondo,
    )

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
        )
    )
    if res.scalars().first() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene autorización para consultar o emitir documentos de esta unidad.",
        )


@router.get(
    "/recibos/{recibo_id}/desglose",
    response_model=ReciboDesgloseResponse,
    responses={
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

    uni_res = await db.execute(select(Unidad).where(Unidad.id == recibo.unidad_id))
    unidad = uni_res.scalars().first()
    identificador = unidad.identificador if unidad else f"UNIDAD-{recibo.unidad_id}"
    alicuota = (getattr(unidad, "alicuota", None) or Decimal("0.0000")) if unidad else Decimal("0.0000")

    items_res = await db.execute(
        select(ReciboItem).where(ReciboItem.recibo_id == recibo.id).order_by(ReciboItem.id.asc())
    )
    items = list(items_res.scalars().all())
    credito_desc = cuantizar(
        sum((-it.monto_usd for it in items if it.tipo_item == "ABONO_CREDITO_PREVIO" and it.monto_usd < CERO), CERO)
    )

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


@router.post(
    "/solvencia/{unidad_id}",
    response_model=CertificadoSolvenciaResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"description": "No autorizado para esta unidad"},
        404: {"description": "Unidad no encontrada"},
        409: {"description": "La unidad presenta deuda pendiente o Idempotency-Key repetida"},
    },
)
async def emitir_certificado_solvencia(
    unidad_id: int,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1),
    db: AsyncSession = Depends(get_db),
    redis_client: Any = Depends(get_redis_client),
    usuario: Usuario = Depends(get_current_user),
) -> CertificadoSolvenciaResponse:
    """Verifica deuda cero ($0.00 USD) y emite un Certificado de Solvencia firmado con HMAC-SHA256."""
    verificar_usuario_activo(usuario)
    await _verificar_acceso_unidad(db, usuario, unidad_id)

    es_nueva = await check_and_set_idempotency_key(
        redis_client,
        idempotency_key,
        scope=f"solvencia:{unidad_id}",
    )
    if not es_nueva:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta solicitud de certificado de solvencia ya fue procesada.",
        )

    uni_res = await db.execute(select(Unidad).where(Unidad.id == unidad_id))
    unidad = uni_res.scalars().first()
    if not unidad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidad no encontrada.")

    rec_res = await db.execute(select(Recibo).where(Recibo.unidad_id == unidad_id))
    recibos = list(rec_res.scalars().all())
    deuda = calcular_deuda_total([(r.monto_usd, r.monto_pagado_usd) for r in recibos])
    if deuda > CERO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La unidad presenta deuda pendiente de {deuda} USD y no puede emitir Certificado de Solvencia.",
        )

    hoy = date.today()
    vencimiento = _fin_de_mes(hoy)
    sufijo = secrets.token_hex(2).upper()
    folio = f"SOLV-{hoy.strftime('%Y%m')}-{unidad.id:04d}-{sufijo}"
    firma = generar_firma_solvencia(folio, unidad.identificador, vencimiento.isoformat(), SECRET_KEY)
    ahora = datetime.now(UTC)

    cert = CertificadoSolvencia(
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

    qr_token = construir_qr_token_solvencia(folio, unidad.identificador, vencimiento.isoformat(), firma)
    return CertificadoSolvenciaResponse(
        id=cert.id or 1,
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
    """Verifica públicamente en tiempo constante la autenticidad y vigencia de un Certificado de Solvencia."""
    cert_res = await db.execute(select(CertificadoSolvencia).where(CertificadoSolvencia.folio == folio.strip()))
    cert = cert_res.scalars().first()
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado de solvencia no encontrado.",
        )

    uni_res = await db.execute(select(Unidad).where(Unidad.id == cert.unidad_id))
    unidad = uni_res.scalars().first()
    identificador = unidad.identificador if unidad else f"UNIDAD-{cert.unidad_id}"

    es_valida = verificar_firma_solvencia(
        cert.folio,
        identificador,
        cert.fecha_vencimiento.isoformat(),
        sig,
        SECRET_KEY,
    )
    if not es_valida or sig.strip() != cert.firma_hmac:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Firma criptográfica de solvencia inválida o adulterada.",
        )

    return VerificarSolvenciaResponse(
        valido=True,
        folio=cert.folio,
        unidad_id=cert.unidad_id,
        identificador_unidad=identificador,
        fecha_vencimiento=cert.fecha_vencimiento,
        vigente=cert.fecha_vencimiento >= date.today(),
        deuda_verificada_usd=cuantizar(cert.deuda_verificada_usd),
        firma_hmac=cert.firma_hmac,
    )
