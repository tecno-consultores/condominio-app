"""Endpoints de tesorería: tasa del día, resumen financiero, fondos, facturación LPH, solvencia y cierre de mes."""

import calendar
import secrets
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import get_db
from src.dependencies import get_current_user, verificar_roles, verificar_usuario_activo
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


async def _validar_egreso_periodo_abierto(db: AsyncSession, periodo: str) -> None:
    rep_res = await db.execute(select(ReporteMensual).where(ReporteMensual.periodo == periodo))
    reporte = rep_res.scalars().first()
    if reporte is not None and (reporte.estado == "CERRADO" or getattr(reporte, "bloqueado", False)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El periodo está cerrado por Candado Contable; no se admiten nuevos egresos",
        )


@router.post(
    "/egresos",
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Tasa del día no registrada o monto inválido"},
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes o usuario fantasma"},
        409: {"description": "Periodo cerrado (Candado Contable) o Idempotency-Key repetida"},
    },
)
async def registrar_egreso(
    datos: EgresoCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    db: AsyncSession = Depends(get_db),
    redis_conn: aioredis.Redis = Depends(get_redis_client),
    usuario: Usuario = Depends(get_current_user),
) -> dict[str, Any]:
    verificar_roles(usuario, _ROLES_TESORERIA)
    es_unica = await check_and_set_idempotency_key(redis_conn, idempotency_key, scope=f"egreso:{usuario.id}")
    if not es_unica:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Petición duplicada detectada (Idempotency-Key ya procesada)",
        )
    try:
        await _validar_egreso_periodo_abierto(db, datos.periodo)
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
    periodo: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> dict[str, Any]:
    verificar_usuario_activo(usuario)
    recibo_stmt = select(Recibo).order_by(Recibo.id.asc())
    egreso_stmt = select(
        Egreso.categoria,
        func.coalesce(func.sum(Egreso.monto_usd), CERO),
    ).group_by(Egreso.categoria)
    if periodo is not None:
        recibo_stmt = recibo_stmt.where(Recibo.periodo == periodo)
        egreso_stmt = egreso_stmt.where(Egreso.periodo == periodo)

    recibos_result = await db.execute(recibo_stmt)
    recibos = list(recibos_result.scalars().all())
    deuda_total = calcular_deuda_total([(r.monto_usd, r.monto_pagado_usd) for r in recibos])

    egresos_result = await db.execute(egreso_stmt)
    total_egresos = Decimal("0.00")
    gastos_por_categoria: dict[str, Decimal] = {}
    for categoria, monto_sumado in egresos_result.all():
        monto_q = cuantizar(Decimal(str(monto_sumado or CERO)))
        total_egresos += monto_q
        gastos_por_categoria[str(categoria)] = monto_q

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
        400: {"description": "Cuerpo JSON malformado"},
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes"},
        409: {"description": "Fondo duplicado o Idempotency-Key repetida"},
    },
)
async def crear_fondo_condominio(
    datos: FondoCondominioCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
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
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Usuario fantasma sin activar"},
    },
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


@router.post(
    "/facturar-periodo",
    response_model=FacturarPeriodoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Sin unidades o configuración de alícuotas/cuota fija inválida"},
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes"},
        409: {"description": "Periodo ya facturado, bloqueado por Candado Contable o Idempotency-Key repetida"},
    },
)
async def facturar_periodo(
    datos: FacturarPeriodoRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
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

    await verificar_periodo_facturable(db, datos.periodo)
    unidades, total_egresos, fondo_reserva, recargo_reserva = await cargar_contexto_facturacion(db, datos)

    try:
        items_por_unidad, superavit_fondo = calcular_cargos_modalidad(datos, unidades, total_egresos, recargo_reserva)
    except ErrorFinanciero as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        total_bruto, total_credito, total_neto = await persistir_lote_facturacion(
            db,
            unidades,
            datos.periodo,
            datos.modalidad,
            items_por_unidad,
            fondo_reserva,
            recargo_reserva,
            superavit_fondo,
        )
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
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "No autorizado para esta unidad"},
        404: {"description": "Unidad no encontrada"},
        409: {"description": "La unidad presenta deuda pendiente o Idempotency-Key repetida"},
    },
)
async def emitir_certificado_solvencia(
    unidad_id: int,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    db: AsyncSession = Depends(get_db),
    redis_client: Any = Depends(get_redis_client),
    usuario: Usuario = Depends(get_current_user),
) -> CertificadoSolvenciaResponse:
    """Verifica deuda cero ($0.00 USD) y emite un Certificado de Solvencia firmado con HMAC-SHA256 y JTI."""
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
    firma = generar_firma_solvencia(folio, unidad.identificador, vencimiento.isoformat(), SECRET_KEY, jti=cert_jti)
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

    cert_jti = getattr(cert, "jti", None) or ""
    es_valida = verificar_firma_solvencia(
        cert.folio,
        identificador,
        cert.fecha_vencimiento.isoformat(),
        sig,
        SECRET_KEY,
        jti=cert_jti or None,
    )
    if not es_valida or sig.strip() != cert.firma_hmac:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Firma criptográfica de solvencia inválida o adulterada.",
        )

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
