"""Endpoints del flujo de reporte, revisión y aprobación de pagos."""

from datetime import date
from decimal import Decimal
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import get_db
from src.dependencies import get_current_user, verificar_roles, verificar_usuario_activo
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
    PagoReportado,
    Recibo,
    TasaCambio,
    Unidad,
    Usuario,
)
from src.redis_client import check_and_set_idempotency_key, get_redis_client
from src.schemas import PagoRechazo, PagoReportar, PagoResponse

router = APIRouter(prefix="/api/pagos", tags=["Pagos"])

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


async def _obtener_pago(db: AsyncSession, pago_id: int) -> PagoReportado:
    result = await db.execute(select(PagoReportado).where(PagoReportado.id == pago_id))
    pago = result.scalars().first()
    if not pago:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado")
    return pago


async def _obtener_recibo(db: AsyncSession, recibo_id: int) -> Recibo:
    result = await db.execute(select(Recibo).where(Recibo.id == recibo_id))
    recibo = result.scalars().first()
    if not recibo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recibo no encontrado")
    return recibo


@router.post(
    "/reportar",
    response_model=PagoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Tasa del día no registrada o referencia inválida"},
        401: {"description": "No autenticado"},
        403: {"description": "Usuario fantasma sin activar"},
        404: {"description": "Recibo no encontrado"},
        409: {"description": "Petición duplicada o periodo cerrado (Candado Contable)"},
    },
)
async def reportar_pago(
    pago: PagoReportar,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    redis_conn: aioredis.Redis = Depends(get_redis_client),
    usuario: Usuario = Depends(get_current_user),
) -> Any:
    verificar_usuario_activo(usuario)
    try:
        is_unique = await check_and_set_idempotency_key(redis_conn, idempotency_key, scope=f"user:{usuario.id}")
        if not is_unique:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Petición duplicada detectada (Idempotency-Key ya procesada)",
            )

        validar_referencia(pago.metodo_pago, pago.numero_referencia)
        metodo_norm = pago.metodo_pago.strip().upper()
        ref_limpia = pago.numero_referencia.strip() if pago.numero_referencia else None
        if metodo_norm != "EFECTIVO" and ref_limpia:
            dup_res = await db.execute(
                select(PagoReportado).where(
                    PagoReportado.metodo_pago == pago.metodo_pago,
                    PagoReportado.numero_referencia == ref_limpia,
                    PagoReportado.estado != "RECHAZADO",
                )
            )
            if dup_res.scalars().first() is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El número de referencia bancaria ya fue registrado previamente",
                )

        tasa = await obtener_tasa_del_dia(db)
        recibo = await _obtener_recibo(db, pago.recibo_id)
        if recibo.bloqueado:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El periodo está cerrado (Candado Contable)",
            )

        monto_usd = convertir_a_usd(pago.monto, pago.moneda, tasa.tasa_usd_ves)
        nuevo_pago = PagoReportado(
            recibo_id=recibo.id,
            usuario_id=usuario.id,
            monto=pago.monto,
            moneda=pago.moneda,
            monto_usd=monto_usd,
            tasa_cambio=tasa.tasa_usd_ves,
            metodo_pago=pago.metodo_pago,
            numero_referencia=pago.numero_referencia,
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
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Any:
    verificar_roles(usuario, _ROLES_TESORERIA)
    result = await db.execute(select(PagoReportado).where(PagoReportado.estado == "EN_REVISION"))
    return list(result.scalars().all())


@router.put(
    "/{pago_id}/aprobar",
    response_model=PagoResponse,
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes o usuario fantasma"},
        404: {"description": "Pago o recibo no encontrado"},
        409: {"description": "El pago no está en revisión o periodo cerrado"},
    },
)
async def aprobar_pago(
    pago_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Any:
    verificar_roles(usuario, _ROLES_TESORERIA)
    pago = await _obtener_pago(db, pago_id)
    if pago.estado != "EN_REVISION":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El pago no está en revisión")

    recibo = await _obtener_recibo(db, pago.recibo_id)
    if recibo.bloqueado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El periodo está cerrado (Candado Contable)",
        )

    excedente = calcular_excedente_pago(recibo.monto_usd, recibo.monto_pagado_usd, pago.monto_usd)
    nuevo_pagado, nuevo_estado = aplicar_pago(recibo.monto_usd, recibo.monto_pagado_usd, pago.monto_usd)
    recibo.monto_pagado_usd = recibo.monto_usd if excedente > Decimal("0.00") else nuevo_pagado
    recibo.estado = nuevo_estado
    pago.estado = "APROBADO"
    motivo_auditoria: str | None = None
    if excedente > Decimal("0.00"):
        res_unidad = await db.execute(select(Unidad).where(Unidad.id == recibo.unidad_id))
        unidad = res_unidad.scalars().first()
        if unidad is not None:
            credito_previo = getattr(unidad, "credito_disponible_usd", None) or Decimal("0.00")
            unidad.credito_disponible_usd = cuantizar(credito_previo + excedente)
        motivo_auditoria = f"Sobrepago acreditado a saldo a favor: +{excedente} USD"

    db.add(
        AuditoriaRecibo(
            recibo_id=recibo.id,
            pago_id=pago.id,
            usuario_id=usuario.id,
            estado_viejo="EN_REVISION",
            estado_nuevo="APROBADO",
            motivo=motivo_auditoria,
        )
    )
    await db.commit()
    await db.refresh(pago)
    return pago


@router.put(
    "/{pago_id}/rechazar",
    response_model=PagoResponse,
    responses={
        400: {"description": "Cuerpo JSON malformado"},
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes o usuario fantasma"},
        404: {"description": "Pago o recibo no encontrado"},
        409: {"description": "El pago no está en revisión o periodo cerrado"},
    },
)
async def rechazar_pago(
    pago_id: int,
    body: PagoRechazo,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Any:
    verificar_roles(usuario, _ROLES_TESORERIA)
    pago = await _obtener_pago(db, pago_id)
    if pago.estado != "EN_REVISION":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El pago no está en revisión")

    recibo = await _obtener_recibo(db, pago.recibo_id)
    if recibo.bloqueado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El periodo está cerrado (Candado Contable)",
        )

    pago.estado = "RECHAZADO"
    db.add(
        AuditoriaRecibo(
            recibo_id=recibo.id,
            pago_id=pago.id,
            usuario_id=usuario.id,
            estado_viejo="EN_REVISION",
            estado_nuevo="RECHAZADO",
            motivo=body.motivo,
        )
    )
    await db.commit()
    await db.refresh(pago)
    return pago
