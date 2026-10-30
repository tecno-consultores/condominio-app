"""Rutas de Reserva de Áreas Sociales Vinculada a Solvencia Estricta e Inspección Post-Evento (Hito 13)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies import get_current_user, verificar_roles, verificar_usuario_activo
from src.finanzas import calcular_deuda_total, cuantizar
from src.models import (
    AreaSocial,
    ContratoOcupacion,
    Recibo,
    ReservaAreaSocial,
    TareaDiaria,
    Unidad,
    Usuario,
)
from src.redis_client import check_and_set_idempotency_key, get_redis_client
from src.schemas import (
    AreaSocialCreate,
    AreaSocialResponse,
    ReservaAreaCreate,
    ReservaAreaResponse,
    ReservaInspeccionarRequest,
)

router = APIRouter(prefix="/api", tags=["Reservas de Áreas Sociales"])

_ROLES_GESTION_AREAS = ("PRESIDENTE", "TESORERO")
_ROLES_INSPECCION = ("CONSERJE", "PRESIDENTE", "TESORERO")
_ROLES_JUNTA_Y_GARITA = ("CONSERJE", "PRESIDENTE", "VICEPRESIDENTE", "SECRETARIO", "TESORERO", "VOCERO")


async def _unidades_activas_usuario(db: AsyncSession, usuario_id: int) -> set[int]:
    res = await db.execute(
        select(ContratoOcupacion.unidad_id).where(
            ContratoOcupacion.usuario_id == usuario_id,
            ContratoOcupacion.es_activo.is_(True),
            ContratoOcupacion.fecha_fin.is_(None),
        )
    )
    return {int(uid) for uid in res.scalars().all()}


async def _obtener_unidad_autorizada(db: AsyncSession, usuario: Usuario, unidad_id: int) -> Unidad:
    res = await db.execute(select(Unidad).where(Unidad.id == unidad_id))
    unidad = res.scalars().first()
    if not unidad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidad inmobiliaria no encontrada.")
    if usuario.rol == "PRESIDENTE":
        return unidad
    unidades_propias = await _unidades_activas_usuario(db, usuario.id)
    if unidad_id not in unidades_propias:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No posee un contrato de ocupación activo sobre la unidad solicitante.",
        )
    return unidad


async def _obtener_area_activa_o_404(db: AsyncSession, area_id: int) -> AreaSocial:
    res = await db.execute(select(AreaSocial).where(AreaSocial.id == area_id, AreaSocial.es_activa.is_(True)))
    area = res.scalars().first()
    if not area:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Área social no encontrada o inactiva.")
    return area


async def _verificar_candado_solvencia_estricta(db: AsyncSession, unidad_id: int, requiere_solvencia: bool) -> None:
    if not requiere_solvencia:
        return
    res_recibos = await db.execute(select(Recibo).where(Recibo.unidad_id == unidad_id))
    recibos = list(res_recibos.scalars().all())
    deuda_total = calcular_deuda_total([(r.monto_usd, r.monto_pagado_usd) for r in recibos])
    if deuda_total > Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Reserva bloqueada por morosidad: La unidad solicitante registra deuda pendiente "
                "y debe estar solvente ($0.00 USD) para reservar áreas sociales."
            ),
        )


async def _verificar_disponibilidad_fecha(db: AsyncSession, area_id: int, fecha_evento: object) -> None:
    res_existente = await db.execute(
        select(ReservaAreaSocial).where(
            ReservaAreaSocial.area_id == area_id,
            ReservaAreaSocial.fecha_evento == fecha_evento,
        )
    )
    existente = res_existente.scalars().first()
    if existente and existente.estado not in ("CANCELADA", "RECHAZADA_MOROSIDAD"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El área social seleccionada ya se encuentra reservada para esa fecha.",
        )


def _serializar_reserva(
    reserva: ReservaAreaSocial,
    nombre_area: str,
    identificador_unidad: str,
) -> ReservaAreaResponse:
    creado_utc = reserva.creado_en or datetime.now(UTC)
    if creado_utc.tzinfo is None:
        creado_utc = creado_utc.replace(tzinfo=UTC)
    return ReservaAreaResponse(
        id=reserva.id,
        area_id=reserva.area_id,
        nombre_area=nombre_area,
        unidad_id=reserva.unidad_id,
        identificador_unidad=identificador_unidad,
        solicitante_id=reserva.solicitante_id,
        fecha_evento=reserva.fecha_evento,
        motivo_evento=reserva.motivo_evento,
        estado=reserva.estado,
        tarea_inspeccion_id=reserva.tarea_inspeccion_id,
        observaciones_inspeccion=reserva.observaciones_inspeccion,
        creado_en=creado_utc,
    )


@router.post(
    "/reservas/areas",
    status_code=status.HTTP_201_CREATED,
    response_model=AreaSocialResponse,
    responses={
        403: {"description": "Solo Presidente o Tesorero pueden configurar áreas sociales"},
        409: {"description": "Nombre de área duplicado o Idempotency-Key repetida"},
    },
)
async def crear_area_social(
    datos: AreaSocialCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
    redis_conn: aioredis.Redis = Depends(get_redis_client),
) -> AreaSocial:
    """Registra una nueva área común reservable con políticas de aforo, depósito y solvencia."""
    verificar_roles(usuario, _ROLES_GESTION_AREAS)
    es_unica = await check_and_set_idempotency_key(
        redis_conn, idempotency_key, ttl_seconds=120, scope=f"crear_area:{usuario.id}"
    )
    if not es_unica:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Petición duplicada detectada (Idempotency-Key ya procesada).",
        )

    nombre_limpio = datos.nombre.strip()
    res_dup = await db.execute(select(AreaSocial).where(AreaSocial.nombre == nombre_limpio))
    if res_dup.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un área social registrada con ese nombre.",
        )

    area = AreaSocial(
        nombre=nombre_limpio,
        aforo_maximo=datos.aforo_maximo,
        costo_uso_usd=cuantizar(datos.costo_uso_usd),
        deposito_garantia_usd=cuantizar(datos.deposito_garantia_usd),
        requiere_solvencia_estricta=datos.requiere_solvencia_estricta,
        es_activa=True,
    )
    db.add(area)
    await db.commit()
    await db.refresh(area)
    return area


@router.get(
    "/reservas/areas",
    response_model=list[AreaSocialResponse],
    responses={403: {"description": "Usuario Fantasma o inactivo"}},
)
async def listar_areas_sociales(
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> list[AreaSocial]:
    """Lista las áreas sociales activas disponibles para reserva en el condominio."""
    verificar_usuario_activo(usuario)
    res = await db.execute(select(AreaSocial).where(AreaSocial.es_activa.is_(True)).order_by(AreaSocial.id.asc()))
    return list(res.scalars().all())


@router.get(
    "/reservas",
    response_model=list[ReservaAreaResponse],
    responses={403: {"description": "Usuario Fantasma o inactivo"}},
)
async def listar_reservas_areas(
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> list[ReservaAreaResponse]:
    """Lista reservas confirmadas o inspeccionadas (todas para Junta/Conserje; propias para residentes)."""
    verificar_usuario_activo(usuario)
    res_reservas = await db.execute(
        select(ReservaAreaSocial).order_by(ReservaAreaSocial.fecha_evento.desc(), ReservaAreaSocial.id.desc())
    )
    reservas = list(res_reservas.scalars().all())

    res_areas = await db.execute(select(AreaSocial))
    mapa_areas = {a.id: a.nombre for a in res_areas.scalars().all()}
    res_unidades = await db.execute(select(Unidad))
    mapa_unidades = {u.id: u.identificador for u in res_unidades.scalars().all()}

    if usuario.rol in _ROLES_JUNTA_Y_GARITA:
        visibles = reservas
    else:
        unidades_propias = await _unidades_activas_usuario(db, usuario.id)
        visibles = [r for r in reservas if r.solicitante_id == usuario.id or r.unidad_id in unidades_propias]

    return [
        _serializar_reserva(
            r,
            mapa_areas.get(r.area_id, f"Área #{r.area_id}"),
            mapa_unidades.get(r.unidad_id, f"U-{r.unidad_id}"),
        )
        for r in visibles
    ]


@router.post(
    "/reservas/solicitar",
    status_code=status.HTTP_201_CREATED,
    response_model=ReservaAreaResponse,
    responses={
        403: {"description": "Unidad morosa (Candado de Solvencia Estricta) o sin contrato activo"},
        404: {"description": "Área social o unidad no encontrada"},
        409: {"description": "Fecha ya reservada para el área social o Idempotency-Key duplicada"},
    },
)
async def solicitar_reserva_area_social(
    datos: ReservaAreaCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
    redis_conn: aioredis.Redis = Depends(get_redis_client),
) -> ReservaAreaResponse:
    """Solicita la reserva exclusiva de un área social verificando solvencia ($0.00 USD) y agenda tarea de conserje."""
    verificar_usuario_activo(usuario)
    es_unica = await check_and_set_idempotency_key(
        redis_conn, idempotency_key, ttl_seconds=120, scope=f"reservar:{datos.unidad_id}"
    )
    if not es_unica:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Petición duplicada detectada (Idempotency-Key ya procesada).",
        )

    unidad = await _obtener_unidad_autorizada(db, usuario, datos.unidad_id)
    area = await _obtener_area_activa_o_404(db, datos.area_id)
    await _verificar_candado_solvencia_estricta(db, unidad.id, area.requiere_solvencia_estricta)
    await _verificar_disponibilidad_fecha(db, area.id, datos.fecha_evento)

    tarea_inspeccion = TareaDiaria(
        plantilla_id=None,
        incidencia_id=None,
        titulo=f"Inspeccionar entrega de {area.nombre} tras reserva de Unidad {unidad.identificador}",
        area=area.nombre,
        fecha=datos.fecha_evento,
        completada=False,
    )
    db.add(tarea_inspeccion)
    await db.flush()

    ahora = datetime.now(UTC)
    reserva = ReservaAreaSocial(
        area_id=area.id,
        unidad_id=unidad.id,
        solicitante_id=usuario.id,
        fecha_evento=datos.fecha_evento,
        motivo_evento=datos.motivo_evento.strip(),
        estado="CONFIRMADA",
        tarea_inspeccion_id=tarea_inspeccion.id,
        creado_en=ahora,
    )
    db.add(reserva)
    await db.commit()
    await db.refresh(reserva)
    return _serializar_reserva(reserva, area.nombre, unidad.identificador)


@router.put(
    "/reservas/{reserva_id}/inspeccionar",
    response_model=ReservaAreaResponse,
    responses={
        403: {"description": "Solo Conserje, Presidente o Tesorero pueden registrar la inspección"},
        404: {"description": "Reserva no encontrada"},
        409: {"description": "La inspección post-evento de esta reserva ya fue registrada"},
    },
)
async def inspeccionar_entrega_area_social(
    reserva_id: int,
    datos: ReservaInspeccionarRequest,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ReservaAreaResponse:
    """Registra el resultado de la inspección post-evento y completa automáticamente la TareaDiaria del conserje."""
    verificar_roles(usuario, _ROLES_INSPECCION)
    res = await db.execute(select(ReservaAreaSocial).where(ReservaAreaSocial.id == reserva_id))
    reserva = res.scalars().first()
    if not reserva:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva de área social no encontrada.")

    if reserva.estado in ("FINALIZADA_SIN_DANOS", "FINALIZADA_CON_DANOS"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La inspección post-evento de esta reserva ya fue registrada.",
        )

    reserva.estado = datos.estado
    reserva.observaciones_inspeccion = datos.observaciones_inspeccion.strip()

    if reserva.tarea_inspeccion_id is not None:
        res_tarea = await db.execute(select(TareaDiaria).where(TareaDiaria.id == reserva.tarea_inspeccion_id))
        tarea = res_tarea.scalars().first()
        if tarea:
            tarea.completada = True
            tarea.completada_en = datetime.now(UTC)

    await db.commit()
    await db.refresh(reserva)

    res_area = await db.execute(select(AreaSocial).where(AreaSocial.id == reserva.area_id))
    area = res_area.scalars().first()
    res_unidad = await db.execute(select(Unidad).where(Unidad.id == reserva.unidad_id))
    unidad = res_unidad.scalars().first()

    return _serializar_reserva(
        reserva,
        area.nombre if area else f"Área #{reserva.area_id}",
        unidad.identificador if unidad else f"U-{reserva.unidad_id}",
    )
