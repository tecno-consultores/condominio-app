"""Endpoints de tesorería: tasa del día, resumen financiero y cierre de mes."""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import get_db
from src.dependencies import get_current_user
from src.finanzas import ErrorFinanciero, calcular_deuda_total, calcular_saldo_pendiente, convertir_a_usd, cuantizar
from src.models import Egreso, Recibo, ReporteMensual, TasaCambio, Usuario
from src.schemas import CierreMensualRequest, EgresoCreate, TasaCambioCreate, TasaCambioResponse

router = APIRouter(prefix="/api/finanzas", tags=["Finanzas"])


@router.post(
    "/tasa",
    response_model=TasaCambioResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Cuerpo JSON malformado"},
        401: {"description": "No autenticado"},
    },
)
async def registrar_tasa(
    datos: TasaCambioCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Any:
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
        404: {"description": "Tasa del día no registrada"},
    },
)
async def obtener_tasa(
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Any:
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
    },
)
async def registrar_egreso(
    datos: EgresoCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> dict[str, Any]:
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
        )
        db.add(egreso)
        await db.commit()
        await db.refresh(egreso)
        return {"id": egreso.id, "monto_usd": str(egreso.monto_usd)}
    except HTTPException:
        raise
    except ErrorFinanciero as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en base de datos al registrar egreso",
        )


@router.get("/resumen", responses={401: {"description": "No autenticado"}})
async def resumen_financiero(
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> dict[str, Any]:
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
                "unidad_id": r.unidad_id,
                "periodo": r.periodo,
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
        409: {"description": "El mes ya fue cerrado (acción inmutable)"},
    },
)
async def cierre_mensual(
    datos: CierreMensualRequest,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> dict[str, Any]:
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
    reporte.cerrado_en = datetime.now(timezone.utc)
    await db.commit()
    return {"periodo": datos.periodo, "estado": "CERRADO"}
