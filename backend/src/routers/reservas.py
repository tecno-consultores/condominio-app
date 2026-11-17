"""Rutas de Reserva de Áreas Sociales Vinculada a Solvencia Estricta e Inspección Post-Evento (Hito 13)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import DEFAULT_CONDOMINIO_ID, get_db, sellar_cadena_worm
from src.dependencies import (
    IdempotentAPIRoute,
    exigir_idempotencia,
    get_current_user,
    verificar_roles,
    verificar_usuario_activo,
)
from src.finanzas import calcular_deuda_total, cuantizar, determinar_estado_recibo
from src.models import (
    AreaSocial,
    AuditoriaRecibo,
    ContratoOcupacion,
    Recibo,
    ReciboItem,
    ReporteMensual,
    ReservaAreaSocial,
    TareaDiaria,
    Unidad,
    Usuario,
)
from src.schemas import (
    AreaSocialCreate,
    AreaSocialResponse,
    ReservaAreaCreate,
    ReservaAreaResponse,
    ReservaInspeccionarRequest,
)

router = APIRouter(
    prefix="/api",
    tags=["Reservas de Áreas Sociales"],
    route_class=IdempotentAPIRoute,
    responses={401: {"description": "No autenticado"}},
)

_ROLES_GESTION_AREAS = ("PRESIDENTE", "TESORERO")
_ROLES_CANCELACION_JUNTA = ("PRESIDENTE", "VICEPRESIDENTE", "TESORERO", "SECRETARIO")
_ROLES_INSPECCION = ("CONSERJE", "PRESIDENTE", "TESORERO")
_ROLES_JUNTA_Y_GARITA = ("CONSERJE", "PRESIDENTE", "VICEPRESIDENTE", "SECRETARIO", "TESORERO")


@dataclass(frozen=True)
class _CargoReservaSpec:
    unidad_id: int
    fecha_evento: date
    monto: Decimal
    tipo_item: str
    descripcion: str
    motivo_auditoria: str
    usuario_id: int
    condominio_id: int


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
            ReservaAreaSocial.estado != "CANCELADA",
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
    dependencies=[Depends(exigir_idempotencia("crear_area", roles=_ROLES_GESTION_AREAS))],
    responses={
        400: {"description": "Cuerpo JSON malformado"},
        403: {"description": "Solo Presidente o Tesorero pueden configurar áreas sociales"},
        409: {"description": "Nombre de área duplicado o Idempotency-Key repetida"},
    },
)
async def crear_area_social(
    datos: AreaSocialCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> AreaSocial:
    """Registra una nueva área común reservable con políticas de aforo, depósito y solvencia."""
    verificar_roles(usuario, _ROLES_GESTION_AREAS)

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
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> list[AreaSocial]:
    """Lista las áreas sociales activas disponibles para reserva en el condominio."""
    verificar_usuario_activo(usuario)
    res = await db.execute(
        select(AreaSocial)
        .where(AreaSocial.es_activa.is_(True))
        .order_by(AreaSocial.id.asc())
        .limit(limit)
        .offset(offset)
    )
    return list(res.scalars().all())


@router.get(
    "/reservas",
    response_model=list[ReservaAreaResponse],
    responses={403: {"description": "Usuario Fantasma o inactivo"}},
)
async def listar_reservas_areas(
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> list[ReservaAreaResponse]:
    """Lista reservas confirmadas o inspeccionadas en una sola consulta SQL con JOIN."""
    verificar_usuario_activo(usuario)
    stmt = (
        select(ReservaAreaSocial, AreaSocial.nombre, Unidad.identificador)
        .join(AreaSocial, AreaSocial.id == ReservaAreaSocial.area_id)
        .join(Unidad, Unidad.id == ReservaAreaSocial.unidad_id)
    )
    if usuario.rol not in _ROLES_JUNTA_Y_GARITA:
        unidades_propias = await _unidades_activas_usuario(db, usuario.id)
        if not unidades_propias:
            return []
        stmt = stmt.where(ReservaAreaSocial.unidad_id.in_(unidades_propias))

    res = await db.execute(
        stmt.order_by(ReservaAreaSocial.fecha_evento.desc(), ReservaAreaSocial.id.desc()).limit(limit).offset(offset)
    )
    return [_serializar_reserva(r, nombre_area, identificador) for r, nombre_area, identificador in res.all()]


@router.post(
    "/reservas/solicitar",
    status_code=status.HTTP_201_CREATED,
    response_model=ReservaAreaResponse,
    dependencies=[Depends(exigir_idempotencia("reservar"))],
    responses={
        400: {"description": "Cuerpo JSON malformado"},
        403: {"description": "Unidad morosa (Candado de Solvencia Estricta) o sin contrato activo"},
        404: {"description": "Área social o unidad no encontrada"},
        409: {"description": "Fecha ya reservada para el área social o Idempotency-Key duplicada"},
    },
)
async def solicitar_reserva_area_social(
    datos: ReservaAreaCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ReservaAreaResponse:
    """Solicita la reserva exclusiva de un área social verificando solvencia ($0.00 USD) y agenda tarea."""
    verificar_usuario_activo(usuario)

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
    await db.flush()

    costo_uso = cuantizar(area.costo_uso_usd)
    if costo_uso > Decimal("0.00"):
        condo_raw = getattr(usuario, "condominio_id", None)
        condo_id = int(DEFAULT_CONDOMINIO_ID if condo_raw is None else condo_raw)
        await _registrar_cargo_reserva(
            db,
            _CargoReservaSpec(
                unidad_id=unidad.id,
                fecha_evento=datos.fecha_evento,
                monto=costo_uso,
                tipo_item="USO_AREA_SOCIAL",
                descripcion=f"Uso área social ({area.nombre} - Reserva #{reserva.id})",
                motivo_auditoria=f"Cargo por uso de área social en reserva #{reserva.id}",
                usuario_id=usuario.id,
                condominio_id=condo_id,
            ),
        )

    await db.commit()
    await db.refresh(reserva)
    return _serializar_reserva(reserva, area.nombre, unidad.identificador)


async def _completar_tarea_inspeccion(db: AsyncSession, tarea_inspeccion_id: int | None) -> None:
    if tarea_inspeccion_id is None:
        return
    res_tarea = await db.execute(select(TareaDiaria).where(TareaDiaria.id == tarea_inspeccion_id))
    tarea = res_tarea.scalars().first()
    if tarea and not tarea.completada:
        tarea.completada = True
        tarea.completada_en = datetime.now(UTC)


async def _verificar_permiso_cancelacion(db: AsyncSession, usuario: Usuario, reserva: ReservaAreaSocial) -> None:
    if usuario.rol in _ROLES_CANCELACION_JUNTA or reserva.solicitante_id == usuario.id:
        return
    unidades_propias = await _unidades_activas_usuario(db, usuario.id)
    if reserva.unidad_id not in unidades_propias:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para cancelar esta reserva.",
        )


async def _resolver_periodo_cargo_abierto(db: AsyncSession, fecha_evento: date) -> str:
    periodo_evento = fecha_evento.strftime("%Y-%m")
    res_rep = await db.execute(select(ReporteMensual).where(ReporteMensual.periodo == periodo_evento))
    reporte = res_rep.scalars().first()
    if reporte is not None and reporte.estado == "CERRADO":
        return datetime.now(UTC).strftime("%Y-%m")
    return str(periodo_evento)


async def _obtener_recibo_abierto_reserva(
    db: AsyncSession,
    spec: _CargoReservaSpec,
) -> tuple[Recibo, str]:
    periodo_cargo = await _resolver_periodo_cargo_abierto(db, spec.fecha_evento)
    res_rec = await db.execute(
        select(Recibo).where(Recibo.unidad_id == spec.unidad_id, Recibo.periodo == periodo_cargo).with_for_update()
    )
    recibo = res_rec.scalars().first()

    if recibo is not None and recibo.bloqueado:
        periodo_cargo = datetime.now(UTC).strftime("%Y-%m")
        res_rec = await db.execute(
            select(Recibo).where(Recibo.unidad_id == spec.unidad_id, Recibo.periodo == periodo_cargo).with_for_update()
        )
        recibo = res_rec.scalars().first()

    if recibo is not None and not recibo.bloqueado:
        estado_viejo = recibo.estado
        recibo.monto_usd = cuantizar(recibo.monto_usd + spec.monto)
        pagado_raw = getattr(recibo, "monto_pagado_usd", None)
        pagado = Decimal("0.00") if pagado_raw is None else cuantizar(pagado_raw)
        recibo.estado = determinar_estado_recibo(recibo.monto_usd, pagado)
        return recibo, estado_viejo

    recibo_nuevo = Recibo(
        condominio_id=spec.condominio_id,
        unidad_id=spec.unidad_id,
        periodo=periodo_cargo,
        monto_usd=spec.monto,
        monto_pagado_usd=Decimal("0.00"),
        estado="PENDIENTE",
        bloqueado=False,
    )
    db.add(recibo_nuevo)
    await db.flush()
    return recibo_nuevo, "INEXISTENTE"


async def _registrar_cargo_reserva(db: AsyncSession, spec: _CargoReservaSpec) -> None:
    """Registra un cargo contable individual de reserva (Recibo, ReciboItem y AuditoriaRecibo WORM)."""
    if spec.monto <= Decimal("0.00"):
        return
    recibo, estado_viejo = await _obtener_recibo_abierto_reserva(db, spec)
    condo_raw = getattr(recibo, "condominio_id", None)
    condo_id = int(spec.condominio_id if condo_raw is None else condo_raw)

    db.add(
        ReciboItem(
            condominio_id=condo_id,
            recibo_id=recibo.id,
            tipo_item=spec.tipo_item,
            descripcion=spec.descripcion,
            monto_usd=spec.monto,
        )
    )
    prev_hash, rec_hash = await sellar_cadena_worm(
        db,
        "auditoria_recibos",
        condo_id,
        f"{recibo.id}|None|{spec.usuario_id}|{estado_viejo}->{recibo.estado}|{spec.motivo_auditoria}",
    )
    db.add(
        AuditoriaRecibo(
            condominio_id=condo_id,
            recibo_id=recibo.id,
            usuario_id=spec.usuario_id,
            estado_viejo=estado_viejo,
            estado_nuevo=recibo.estado,
            motivo=spec.motivo_auditoria,
            prev_hash=prev_hash,
            record_hash=rec_hash,
        )
    )


async def _registrar_cargo_danos_reserva(
    db: AsyncSession,
    reserva: ReservaAreaSocial,
    area: AreaSocial,
    usuario_id: int,
) -> None:
    """Registra el cargo contable (Recibo, ReciboItem y AuditoriaRecibo) por retención de depósito."""
    monto_danos = cuantizar(area.deposito_garantia_usd)
    if monto_danos <= Decimal("0.00"):
        return
    condo_raw = getattr(reserva, "condominio_id", None)
    condo_id = int(DEFAULT_CONDOMINIO_ID if condo_raw is None else condo_raw)
    await _registrar_cargo_reserva(
        db,
        _CargoReservaSpec(
            unidad_id=reserva.unidad_id,
            fecha_evento=reserva.fecha_evento,
            monto=monto_danos,
            tipo_item="DANOS_AREA_SOCIAL",
            descripcion=f"Cargo por daños post-evento en {area.nombre} ({reserva.fecha_evento.isoformat()})",
            motivo_auditoria=f"Retención/cargo de depósito por daños en reserva #{reserva.id}",
            usuario_id=usuario_id,
            condominio_id=condo_id,
        ),
    )


async def _revertir_cargo_uso_cancelacion(
    db: AsyncSession,
    reserva: ReservaAreaSocial,
    area: AreaSocial,
    usuario_id: int,
) -> None:
    if cuantizar(area.costo_uso_usd) <= Decimal("0.00"):
        return
    res_item = await db.execute(
        select(ReciboItem, Recibo)
        .join(Recibo, Recibo.id == ReciboItem.recibo_id)
        .where(
            Recibo.unidad_id == reserva.unidad_id,
            ReciboItem.tipo_item == "USO_AREA_SOCIAL",
            ReciboItem.descripcion.contains(f"Reserva #{reserva.id})"),
        )
        .with_for_update()
    )
    fila = res_item.first()
    if fila is None:
        return
    item, recibo = fila
    condo_raw = getattr(recibo, "condominio_id", None)
    condo_id = int(DEFAULT_CONDOMINIO_ID if condo_raw is None else condo_raw)
    pagado_raw = getattr(recibo, "monto_pagado_usd", None)
    pagado = Decimal("0.00") if pagado_raw is None else cuantizar(pagado_raw)
    nuevo_monto = cuantizar(recibo.monto_usd - item.monto_usd)
    estado_viejo = recibo.estado

    if not recibo.bloqueado and nuevo_monto >= pagado:
        recibo.monto_usd = nuevo_monto
        recibo.estado = determinar_estado_recibo(recibo.monto_usd, pagado)
        await db.delete(item)
        motivo = f"Reverso de cargo por uso tras cancelación de reserva #{reserva.id}"
    else:
        res_u = await db.execute(select(Unidad).where(Unidad.id == reserva.unidad_id).with_for_update())
        unidad_obj = res_u.scalars().first()
        if unidad_obj is not None:
            cred_raw = getattr(unidad_obj, "credito_disponible_usd", None)
            cred_prev = Decimal("0.00") if cred_raw is None else cuantizar(cred_raw)
            unidad_obj.credito_disponible_usd = cuantizar(cred_prev + item.monto_usd)
        motivo = f"Crédito a favor por cancelación de reserva #{reserva.id}"

    prev_hash, rec_hash = await sellar_cadena_worm(
        db,
        "auditoria_recibos",
        condo_id,
        f"{recibo.id}|None|{usuario_id}|{estado_viejo}->{recibo.estado}|{motivo}",
    )
    db.add(
        AuditoriaRecibo(
            condominio_id=condo_id,
            recibo_id=recibo.id,
            usuario_id=usuario_id,
            estado_viejo=estado_viejo,
            estado_nuevo=recibo.estado,
            motivo=motivo,
            prev_hash=prev_hash,
            record_hash=rec_hash,
        )
    )


@router.put(
    "/reservas/{reserva_id}/cancelar",
    response_model=ReservaAreaResponse,
    dependencies=[Depends(exigir_idempotencia("cancelar_reserva:{reserva_id}"))],
    responses={
        403: {"description": "Sin permisos sobre la reserva"},
        404: {"description": "Reserva no encontrada"},
        409: {"description": "Reserva no cancelable o Idempotency-Key duplicada"},
    },
)
async def cancelar_reserva_area_social(
    reserva_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ReservaAreaResponse:
    """Cancela una reserva CONFIRMADA liberando fecha, tarea asociada y revirtiendo cargo de uso."""
    verificar_usuario_activo(usuario)

    res = await db.execute(select(ReservaAreaSocial).where(ReservaAreaSocial.id == reserva_id).with_for_update())
    reserva = res.scalars().first()
    if not reserva:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva de área social no encontrada.")

    await _verificar_permiso_cancelacion(db, usuario, reserva)
    if reserva.estado != "CONFIRMADA":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo pueden cancelarse reservas en estado CONFIRMADA.",
        )

    res_area = await db.execute(select(AreaSocial).where(AreaSocial.id == reserva.area_id))
    area = res_area.scalars().first()
    if area is not None:
        await _revertir_cargo_uso_cancelacion(db, reserva, area, usuario.id)

    reserva.estado = "CANCELADA"
    await _completar_tarea_inspeccion(db, reserva.tarea_inspeccion_id)
    await db.commit()
    await db.refresh(reserva)

    res_unidad = await db.execute(select(Unidad).where(Unidad.id == reserva.unidad_id))
    unidad = res_unidad.scalars().first()
    return _serializar_reserva(
        reserva,
        area.nombre if area else f"Área #{reserva.area_id}",
        unidad.identificador if unidad else f"U-{reserva.unidad_id}",
    )


@router.put(
    "/reservas/{reserva_id}/inspeccionar",
    response_model=ReservaAreaResponse,
    dependencies=[Depends(exigir_idempotencia("inspeccionar_reserva:{reserva_id}", roles=_ROLES_INSPECCION))],
    responses={
        400: {"description": "Cuerpo JSON malformado"},
        403: {"description": "Solo Conserje, Presidente o Tesorero pueden registrar la inspección"},
        404: {"description": "Reserva no encontrada"},
        409: {"description": "La inspección post-evento de esta reserva ya fue registrada o fue cancelada"},
    },
)
async def inspeccionar_entrega_area_social(
    reserva_id: int,
    datos: ReservaInspeccionarRequest,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ReservaAreaResponse:
    """Registra la inspección post-evento, completa la TareaDiaria y genera cargo contable si hubo daños."""
    verificar_roles(usuario, _ROLES_INSPECCION)
    res = await db.execute(select(ReservaAreaSocial).where(ReservaAreaSocial.id == reserva_id).with_for_update())
    reserva = res.scalars().first()
    if not reserva:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva de área social no encontrada.")

    if reserva.estado != "CONFIRMADA":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La inspección post-evento de esta reserva ya fue registrada o fue cancelada.",
        )

    reserva.estado = datos.estado
    reserva.observaciones_inspeccion = datos.observaciones_inspeccion.strip()
    await _completar_tarea_inspeccion(db, reserva.tarea_inspeccion_id)

    res_area = await db.execute(select(AreaSocial).where(AreaSocial.id == reserva.area_id))
    area = res_area.scalars().first()
    res_unidad = await db.execute(select(Unidad).where(Unidad.id == reserva.unidad_id))
    unidad = res_unidad.scalars().first()

    if datos.estado == "FINALIZADA_CON_DANOS" and area is not None:
        await _registrar_cargo_danos_reserva(db, reserva, area, usuario.id)

    await db.commit()
    await db.refresh(reserva)

    return _serializar_reserva(
        reserva,
        area.nombre if area else f"Área #{reserva.area_id}",
        unidad.identificador if unidad else f"U-{reserva.unidad_id}",
    )
