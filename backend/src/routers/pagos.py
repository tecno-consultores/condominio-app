"""Endpoints del flujo de reporte, revisión y aprobación de pagos."""

from datetime import date
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import get_db
from src.dependencies import get_current_user
from src.finanzas import ErrorFinanciero, aplicar_pago, convertir_a_usd, validar_referencia
from src.models import AuditoriaRecibo, PagoReportado, Recibo, TasaCambio, Usuario
from src.redis_client import check_and_set_idempotency_key, get_redis_client
from src.schemas import PagoRechazo, PagoReportar, PagoResponse

router = APIRouter(prefix="/api/pagos", tags=["Pagos"])


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


@router.post("/reportar", response_model=PagoResponse, status_code=status.HTTP_201_CREATED)
async def reportar_pago(
    pago: PagoReportar,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    redis_conn: aioredis.Redis = Depends(get_redis_client),
    usuario: Usuario = Depends(get_current_user),
) -> Any:
    try:
        is_unique = await check_and_set_idempotency_key(redis_conn, idempotency_key)
        if not is_unique:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Petición duplicada detectada (Idempotency-Key ya procesada)",
            )

        validar_referencia(pago.metodo_pago, pago.numero_referencia)
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en base de datos al reportar pago",
        )


@router.get("/revision", response_model=list[PagoResponse])
async def listar_pagos_en_revision(
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Any:
    result = await db.execute(select(PagoReportado).where(PagoReportado.estado == "EN_REVISION"))
    return list(result.scalars().all())


@router.put("/{pago_id}/aprobar", response_model=PagoResponse)
async def aprobar_pago(
    pago_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Any:
    pago = await _obtener_pago(db, pago_id)
    if pago.estado != "EN_REVISION":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El pago no está en revisión")

    recibo = await _obtener_recibo(db, pago.recibo_id)
    if recibo.bloqueado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El periodo está cerrado (Candado Contable)",
        )

    nuevo_pagado, nuevo_estado = aplicar_pago(recibo.monto_usd, recibo.monto_pagado_usd, pago.monto_usd)
    recibo.monto_pagado_usd = nuevo_pagado
    recibo.estado = nuevo_estado
    pago.estado = "APROBADO"
    db.add(
        AuditoriaRecibo(
            recibo_id=recibo.id,
            pago_id=pago.id,
            usuario_id=usuario.id,
            estado_viejo="EN_REVISION",
            estado_nuevo="APROBADO",
            motivo=None,
        )
    )
    await db.commit()
    await db.refresh(pago)
    return pago


@router.put("/{pago_id}/rechazar", response_model=PagoResponse)
async def rechazar_pago(
    pago_id: int,
    body: PagoRechazo,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Any:
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
