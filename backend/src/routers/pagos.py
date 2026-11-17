"""Endpoints del flujo de reporte, revisión y aprobación de pagos."""

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import DEFAULT_CONDOMINIO_ID, get_db, sellar_cadena_worm
from src.dependencies import (
    IdempotentAPIRoute,
    exigir_idempotencia,
    get_current_user,
    verificar_roles,
    verificar_usuario_activo,
)
from src.finanzas import (
    ErrorFinanciero,
    aplicar_pago,
    calcular_excedente_pago,
    convertir_a_usd,
    cuantizar,
    validar_referencia,
)
from src.models import (
    AuditoriaRecibo,
    ContratoOcupacion,
    PagoReportado,
    Recibo,
    TasaCambio,
    Unidad,
    Usuario,
)
from src.schemas import PagoRechazo, PagoReportar, PagoResponse

router = APIRouter(prefix="/api/pagos", tags=["Pagos"], route_class=IdempotentAPIRoute)

_ROLES_TESORERIA = ("TESORERO", "PRESIDENTE")


async def obtener_tasa_del_dia(db: AsyncSession, fecha: date | None = None) -> TasaCambio:
    """Obtiene la tasa de cambio registrada para el día exacto (por defecto hoy)."""
    fecha_objetivo = fecha or date.today()
    result = await db.execute(select(TasaCambio).where(TasaCambio.fecha == fecha_objetivo))
    tasa = result.scalars().first()
    if not tasa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La tasa de cambio del día no ha sido registrada",
        )
    return tasa


async def _obtener_pago(db: AsyncSession, pago_id: int, *, for_update: bool = False) -> PagoReportado:
    stmt = select(PagoReportado).where(PagoReportado.id == pago_id)
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    pago = result.scalars().first()
    if not pago:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado")
    return pago


async def _obtener_recibo(db: AsyncSession, recibo_id: int, *, for_update: bool = False) -> Recibo:
    stmt = select(Recibo).where(Recibo.id == recibo_id)
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    recibo = result.scalars().first()
    if not recibo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recibo no encontrado")
    return recibo


async def _obtener_unidad_bloqueada(db: AsyncSession, unidad_id: int) -> Unidad:
    res_unidad = await db.execute(select(Unidad).where(Unidad.id == unidad_id).with_for_update())
    unidad = res_unidad.scalars().first()
    if unidad is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidad asociada al recibo no encontrada")
    return unidad


async def _verificar_titularidad_recibo(db: AsyncSession, usuario: Usuario, unidad_id: int) -> None:
    """Impide IDOR verificando contrato activo en la unidad o pertenencia a Tesorería/Presidencia."""
    if getattr(usuario, "rol", "") in _ROLES_TESORERIA:
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
            detail="No tiene autorización para reportar pagos sobre esta unidad",
        )


async def _verificar_referencia_no_duplicada(
    db: AsyncSession,
    metodo_norm: str,
    ref_limpia: str | None,
) -> None:
    if metodo_norm == "EFECTIVO" or not ref_limpia:
        return
    dup_res = await db.execute(
        select(PagoReportado).where(
            PagoReportado.metodo_pago == metodo_norm,
            PagoReportado.numero_referencia == ref_limpia,
            PagoReportado.estado != "RECHAZADO",
        )
    )
    if dup_res.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El número de referencia bancaria ya fue registrado previamente",
        )


def _normalizar_referencia_pago(pago: PagoReportar) -> tuple[str, str | None]:
    validar_referencia(pago.metodo_pago, pago.numero_referencia)
    metodo_norm = pago.metodo_pago.strip().upper()
    ref_limpia = pago.numero_referencia.strip() if pago.numero_referencia and pago.numero_referencia.strip() else None
    return metodo_norm, ref_limpia


@router.post(
    "/reportar",
    response_model=PagoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_idempotencia("reportar_pago"))],
    responses={
        400: {"description": "Tasa del día no registrada o referencia inválida"},
        401: {"description": "No autenticado"},
        403: {"description": "Usuario fantasma sin activar o unidad ajena (anti-IDOR)"},
        404: {"description": "Recibo no encontrado"},
        409: {"description": "Petición duplicada o periodo cerrado (Candado Contable)"},
    },
)
async def reportar_pago(
    pago: PagoReportar,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Any:
    verificar_usuario_activo(usuario)
    try:
        metodo_norm, ref_limpia = _normalizar_referencia_pago(pago)
        await _verificar_referencia_no_duplicada(db, metodo_norm, ref_limpia)

        tasa = await obtener_tasa_del_dia(db)
        recibo = await _obtener_recibo(db, pago.recibo_id)
        await _verificar_titularidad_recibo(db, usuario, recibo.unidad_id)
        if recibo.bloqueado:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El periodo está cerrado (Candado Contable)",
            )

        monto_usd = convertir_a_usd(pago.monto, pago.moneda, tasa.tasa_usd_ves)
        condo_raw = getattr(recibo, "condominio_id", None)
        condo_id = int(DEFAULT_CONDOMINIO_ID if condo_raw is None else condo_raw)
        nuevo_pago = PagoReportado(
            condominio_id=condo_id,
            recibo_id=recibo.id,
            usuario_id=usuario.id,
            monto=pago.monto,
            moneda=pago.moneda,
            monto_usd=monto_usd,
            tasa_cambio=tasa.tasa_usd_ves,
            metodo_pago=metodo_norm,
            numero_referencia=ref_limpia,
            url_comprobante=pago.url_comprobante,
            estado="EN_REVISION",
        )
        db.add(nuevo_pago)
        await db.commit()
        await db.refresh(nuevo_pago)
        return nuevo_pago
    except HTTPException:
        raise
    except ErrorFinanciero as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El número de referencia bancaria ya fue registrado previamente",
        ) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en base de datos al reportar pago",
        ) from exc


@router.get(
    "/revision",
    response_model=list[PagoResponse],
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes o usuario fantasma"},
    },
)
async def listar_pagos_en_revision(
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Any:
    verificar_roles(usuario, _ROLES_TESORERIA)
    result = await db.execute(
        select(PagoReportado)
        .where(PagoReportado.estado == "EN_REVISION")
        .order_by(PagoReportado.id.asc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


@router.put(
    "/{pago_id}/aprobar",
    response_model=PagoResponse,
    dependencies=[Depends(exigir_idempotencia("aprobar_pago:{pago_id}", roles=_ROLES_TESORERIA))],
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes o usuario fantasma"},
        404: {"description": "Pago, recibo o unidad no encontrada"},
        409: {"description": "Petición duplicada, el pago no está en revisión o periodo cerrado"},
    },
)
async def aprobar_pago(
    pago_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Any:
    verificar_roles(usuario, _ROLES_TESORERIA)

    pago = await _obtener_pago(db, pago_id, for_update=True)
    if pago.estado != "EN_REVISION":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El pago no está en revisión")

    recibo = await _obtener_recibo(db, pago.recibo_id, for_update=True)
    if recibo.bloqueado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El periodo está cerrado (Candado Contable)",
        )

    unidad = await _obtener_unidad_bloqueada(db, recibo.unidad_id)
    estado_previo_recibo = recibo.estado
    excedente = calcular_excedente_pago(recibo.monto_usd, recibo.monto_pagado_usd, pago.monto_usd)
    nuevo_pagado, nuevo_estado = aplicar_pago(recibo.monto_usd, recibo.monto_pagado_usd, pago.monto_usd)
    recibo.monto_pagado_usd = recibo.monto_usd if excedente > Decimal("0.00") else nuevo_pagado
    recibo.estado = nuevo_estado
    pago.estado = "APROBADO"
    motivo_auditoria = f"Pago #{pago.id} aprobado ({pago.monto_usd} USD)"
    if excedente > Decimal("0.00"):
        credito_raw = getattr(unidad, "credito_disponible_usd", None)
        credito_previo = Decimal("0.00") if credito_raw is None else credito_raw
        unidad.credito_disponible_usd = cuantizar(credito_previo + excedente)
        motivo_auditoria = f"Sobrepago acreditado a saldo a favor: +{excedente} USD"

    condo_raw = getattr(recibo, "condominio_id", None)
    condo_id = int(DEFAULT_CONDOMINIO_ID if condo_raw is None else condo_raw)
    prev_hash, rec_hash = await sellar_cadena_worm(
        db,
        "auditoria_recibos",
        condo_id,
        f"{recibo.id}|{pago.id}|{usuario.id}|{estado_previo_recibo}->{recibo.estado}|{motivo_auditoria}",
    )
    db.add(
        AuditoriaRecibo(
            condominio_id=condo_id,
            recibo_id=recibo.id,
            pago_id=pago.id,
            usuario_id=usuario.id,
            estado_viejo=estado_previo_recibo,
            estado_nuevo=recibo.estado,
            motivo=motivo_auditoria,
            prev_hash=prev_hash,
            record_hash=rec_hash,
        )
    )
    await db.commit()
    await db.refresh(pago)
    return pago


@router.put(
    "/{pago_id}/rechazar",
    response_model=PagoResponse,
    dependencies=[Depends(exigir_idempotencia("rechazar_pago:{pago_id}", roles=_ROLES_TESORERIA))],
    responses={
        400: {"description": "Cuerpo JSON malformado"},
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes o usuario fantasma"},
        404: {"description": "Pago o recibo no encontrado"},
        409: {"description": "El pago no está en revisión, periodo cerrado o Idempotency-Key repetida"},
    },
)
async def rechazar_pago(
    pago_id: int,
    body: PagoRechazo,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Any:
    verificar_roles(usuario, _ROLES_TESORERIA)
    pago = await _obtener_pago(db, pago_id, for_update=True)
    if pago.estado != "EN_REVISION":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El pago no está en revisión")

    recibo = await _obtener_recibo(db, pago.recibo_id, for_update=True)
    if recibo.bloqueado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El periodo está cerrado (Candado Contable)",
        )

    pago.estado = "RECHAZADO"
    condo_raw = getattr(recibo, "condominio_id", None)
    condo_id = int(DEFAULT_CONDOMINIO_ID if condo_raw is None else condo_raw)
    prev_hash, rec_hash = await sellar_cadena_worm(
        db,
        "auditoria_recibos",
        condo_id,
        f"{recibo.id}|{pago.id}|{usuario.id}|{recibo.estado}->{recibo.estado}|{body.motivo}",
    )
    db.add(
        AuditoriaRecibo(
            condominio_id=condo_id,
            recibo_id=recibo.id,
            pago_id=pago.id,
            usuario_id=usuario.id,
            estado_viejo=recibo.estado,
            estado_nuevo=recibo.estado,
            motivo=body.motivo,
            prev_hash=prev_hash,
            record_hash=rec_hash,
        )
    )
    await db.commit()
    await db.refresh(pago)
    return pago
