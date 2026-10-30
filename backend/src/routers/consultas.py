import hashlib
import hmac
from datetime import UTC, datetime
from decimal import Decimal

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies import get_current_user, verificar_roles, verificar_usuario_activo
from src.finanzas import (
    CUATRO_DECIMALES,
    calcular_ip_hash_voto,
    construir_mensaje_voto_consulta,
    evaluar_escrutinio_consulta,
    generar_firma_voto_consulta,
    umbral_quorum_por_regla,
)
from src.models import (
    BitacoraActa,
    ConsultaComunitaria,
    ContratoOcupacion,
    OpcionConsulta,
    Unidad,
    Usuario,
    VotoConsulta,
)
from src.redis_client import check_and_set_idempotency_key, get_redis_client
from src.schemas import (
    CerrarConsultaResponse,
    ConsultaCreate,
    ConsultaDetalleResponse,
    ConsultaResumenResponse,
    OpcionConsultaResultadoResponse,
    ReciboVotoResponse,
    VotarConsultaRequest,
    VotoReciboResumenResponse,
)
from src.security import SECRET_KEY

router = APIRouter(prefix="/api/consultas", tags=["Gobernanza y Cartas Consulta LPH"])

_ROLES_GOBERNANZA = ("PRESIDENTE", "SECRETARIO")


async def _cargar_opciones_y_votos(
    db: AsyncSession, consulta_id: int
) -> tuple[list[OpcionConsulta], list[VotoConsulta]]:
    res_op = await db.execute(
        select(OpcionConsulta).where(OpcionConsulta.consulta_id == consulta_id).order_by(OpcionConsulta.id.asc())
    )
    res_votos = await db.execute(
        select(VotoConsulta).where(VotoConsulta.consulta_id == consulta_id).order_by(VotoConsulta.id.asc())
    )
    return list(res_op.scalars().all()), list(res_votos.scalars().all())


def _calcular_metricas_consulta(
    opciones: list[OpcionConsulta], votos: list[VotoConsulta], quorum_minimo: Decimal
) -> tuple[Decimal, Decimal, list[OpcionConsultaResultadoResponse]]:
    conteo_por_opcion: dict[int, int] = {op.id: 0 for op in opciones}
    alicuota_por_opcion: dict[int, Decimal] = {op.id: Decimal("0.0000") for op in opciones}
    aprobatorias_ids = {op.id for op in opciones if op.es_opcion_aprobatoria}

    for v in votos:
        alic = Decimal(str(v.alicuota_capturada)).quantize(CUATRO_DECIMALES)
        conteo_por_opcion[v.opcion_id] = conteo_por_opcion.get(v.opcion_id, 0) + 1
        alicuota_por_opcion[v.opcion_id] = (
            alicuota_por_opcion.get(v.opcion_id, Decimal("0.0000")) + alic
        ).quantize(CUATRO_DECIMALES)

    _, participacion_total, alicuota_aprobatoria = evaluar_escrutinio_consulta(
        quorum_minimo_alicuota=quorum_minimo,
        opciones_aprobatorias_ids=aprobatorias_ids,
        alicuotas_por_opcion=alicuota_por_opcion,
    )

    opciones_resp = [
        OpcionConsultaResultadoResponse(
            id=op.id,
            etiqueta=op.etiqueta,
            es_opcion_aprobatoria=bool(op.es_opcion_aprobatoria),
            votos_cantidad=conteo_por_opcion.get(op.id, 0),
            alicuota_acumulada=alicuota_por_opcion.get(op.id, Decimal("0.0000")),
        )
        for op in opciones
    ]
    return participacion_total, alicuota_aprobatoria, opciones_resp


async def _unidades_usuario(db: AsyncSession, usuario_id: int) -> set[int]:
    res = await db.execute(
        select(ContratoOcupacion.unidad_id).where(
            ContratoOcupacion.usuario_id == usuario_id,
            ContratoOcupacion.es_activo.is_(True),
            ContratoOcupacion.fecha_fin.is_(None),
        )
    )
    return {int(uid) for uid in res.scalars().all()}


async def _construir_mi_voto(
    db: AsyncSession,
    votos: list[VotoConsulta],
    opciones_map: dict[int, str],
    usuario_id: int,
    unidades_propias: set[int],
) -> VotoReciboResumenResponse | None:
    voto_propio = next(
        (v for v in votos if v.usuario_id == usuario_id or v.unidad_id in unidades_propias),
        None,
    )
    if not voto_propio:
        return None
    res_u = await db.execute(select(Unidad).where(Unidad.id == voto_propio.unidad_id))
    unidad = res_u.scalars().first()
    identificador = unidad.identificador if unidad else f"U-{voto_propio.unidad_id}"
    return VotoReciboResumenResponse(
        voto_id=voto_propio.id,
        unidad_id=voto_propio.unidad_id,
        identificador_unidad=identificador,
        opcion_id=voto_propio.opcion_id,
        opcion_etiqueta=opciones_map.get(voto_propio.opcion_id, ""),
        alicuota_capturada=Decimal(str(voto_propio.alicuota_capturada)).quantize(CUATRO_DECIMALES),
        fecha_voto=voto_propio.fecha_voto,
        firma_hmac=voto_propio.firma_hmac,
    )


async def _armar_detalle_consulta(
    db: AsyncSession, consulta: ConsultaComunitaria, usuario_id: int
) -> ConsultaDetalleResponse:
    opciones, votos = await _cargar_opciones_y_votos(db, consulta.id)
    quorum_min = Decimal(str(consulta.quorum_minimo_alicuota)).quantize(CUATRO_DECIMALES)
    participacion, aprobatoria, opciones_resp = _calcular_metricas_consulta(opciones, votos, quorum_min)
    unidades_propias = await _unidades_usuario(db, usuario_id)
    opciones_map = {op.id: op.etiqueta for op in opciones}
    mi_voto = await _construir_mi_voto(db, votos, opciones_map, usuario_id, unidades_propias)

    return ConsultaDetalleResponse(
        id=consulta.id,
        titulo=consulta.titulo,
        descripcion_legal=consulta.descripcion_legal,
        tipo_consulta=consulta.tipo_consulta,
        regla_quorum=consulta.regla_quorum,
        quorum_minimo_alicuota=quorum_min,
        participacion_alicuota=participacion,
        alicuota_aprobatoria=aprobatoria,
        total_votos=len(votos),
        fecha_apertura=consulta.fecha_apertura,
        fecha_cierre=consulta.fecha_cierre,
        estado=consulta.estado,
        creada_por_id=consulta.creada_por_id,
        acta_bitacora_id=consulta.acta_bitacora_id,
        ya_voto_usuario=mi_voto is not None,
        opciones=opciones_resp,
        mi_voto=mi_voto,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ConsultaDetalleResponse,
    responses={
        403: {"description": "Solo Presidente o Secretario pueden convocar consultas"},
        409: {"description": "Petición duplicada (Idempotency-Key)"},
    },
)
async def crear_consulta(
    datos: ConsultaCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
    redis_conn: aioredis.Redis = Depends(get_redis_client),
) -> ConsultaDetalleResponse:
    """Crea una nueva Carta Consulta (Art. 23 LPH) o convocatoria de Asamblea (Art. 24 LPH)."""
    verificar_roles(usuario, _ROLES_GOBERNANZA)

    es_unica = await check_and_set_idempotency_key(
        redis_conn, idempotency_key, ttl_seconds=120, scope=f"crear_consulta:{usuario.id}"
    )
    if not es_unica:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Petición duplicada detectada (Idempotency-Key ya procesada).",
        )

    quorum_minimo = umbral_quorum_por_regla(datos.regla_quorum)
    ahora = datetime.now(UTC)
    consulta = ConsultaComunitaria(
        titulo=datos.titulo.strip(),
        descripcion_legal=datos.descripcion_legal.strip(),
        tipo_consulta=datos.tipo_consulta,
        regla_quorum=datos.regla_quorum,
        quorum_minimo_alicuota=quorum_minimo,
        fecha_apertura=ahora,
        fecha_cierre=datos.fecha_cierre,
        estado="ABIERTA",
        creada_por_id=usuario.id,
    )
    db.add(consulta)
    await db.flush()

    for op in datos.opciones:
        db.add(
            OpcionConsulta(
                consulta_id=consulta.id,
                etiqueta=op.etiqueta.strip(),
                es_opcion_aprobatoria=op.es_opcion_aprobatoria,
            )
        )

    await db.commit()
    await db.refresh(consulta)
    return await _armar_detalle_consulta(db, consulta, usuario.id)


@router.get(
    "",
    response_model=list[ConsultaResumenResponse],
    responses={403: {"description": "Usuario Fantasma o inactivo"}},
)
async def listar_consultas(
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> list[ConsultaResumenResponse]:
    """Lista las Cartas Consulta y Asambleas con su avance de quórum por alícuota en tiempo real."""
    verificar_usuario_activo(usuario)
    res = await db.execute(select(ConsultaComunitaria).order_by(ConsultaComunitaria.id.desc()))
    consultas = list(res.scalars().all())
    unidades_propias = await _unidades_usuario(db, usuario.id)
    salida: list[ConsultaResumenResponse] = []

    for c in consultas:
        opciones, votos = await _cargar_opciones_y_votos(db, c.id)
        quorum_min = Decimal(str(c.quorum_minimo_alicuota)).quantize(CUATRO_DECIMALES)
        participacion, aprobatoria, _ = _calcular_metricas_consulta(opciones, votos, quorum_min)
        ya_voto = any(v.usuario_id == usuario.id or v.unidad_id in unidades_propias for v in votos)
        salida.append(
            ConsultaResumenResponse(
                id=c.id,
                titulo=c.titulo,
                descripcion_legal=c.descripcion_legal,
                tipo_consulta=c.tipo_consulta,
                regla_quorum=c.regla_quorum,
                quorum_minimo_alicuota=quorum_min,
                participacion_alicuota=participacion,
                alicuota_aprobatoria=aprobatoria,
                total_votos=len(votos),
                fecha_apertura=c.fecha_apertura,
                fecha_cierre=c.fecha_cierre,
                estado=c.estado,
                creada_por_id=c.creada_por_id,
                acta_bitacora_id=c.acta_bitacora_id,
                ya_voto_usuario=ya_voto,
            )
        )
    return salida


@router.get(
    "/{consulta_id}",
    response_model=ConsultaDetalleResponse,
    responses={
        403: {"description": "Usuario Fantasma o inactivo"},
        404: {"description": "Consulta no encontrada"},
    },
)
async def obtener_detalle_consulta(
    consulta_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ConsultaDetalleResponse:
    """Obtiene el detalle de una Carta Consulta o Asamblea, sus opciones y el recibo de voto si ya participó."""
    verificar_usuario_activo(usuario)
    res = await db.execute(select(ConsultaComunitaria).where(ConsultaComunitaria.id == consulta_id))
    consulta = res.scalars().first()
    if not consulta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consulta comunitaria no encontrada.")
    return await _armar_detalle_consulta(db, consulta, usuario.id)


async def _validar_derecho_voto_unidad(
    db: AsyncSession, usuario_id: int, unidad_id: int
) -> tuple[Unidad, ContratoOcupacion]:
    res_u = await db.execute(select(Unidad).where(Unidad.id == unidad_id))
    unidad = res_u.scalars().first()
    if not unidad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidad inmobiliaria no encontrada.")

    res_c = await db.execute(
        select(ContratoOcupacion).where(
            ContratoOcupacion.usuario_id == usuario_id,
            ContratoOcupacion.unidad_id == unidad_id,
            ContratoOcupacion.es_activo.is_(True),
            ContratoOcupacion.fecha_fin.is_(None),
        )
    )
    contrato = res_c.scalars().first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No posee un contrato de ocupación activo sobre la unidad indicada.",
        )

    es_propietario = contrato.tipo_ocupante == "PROPIETARIO"
    tiene_poder = bool(getattr(contrato, "puede_votar_asamblea", es_propietario))
    if not es_propietario and not tiene_poder:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Solo el propietario titular o un representante con poder registrado "
                "puede votar en Cartas Consulta."
            ),
        )
    return unidad, contrato


@router.post(
    "/{consulta_id}/votar",
    status_code=status.HTTP_201_CREATED,
    response_model=ReciboVotoResponse,
    responses={
        403: {"description": "Sin derecho a voto sobre la unidad o inquilino sin poder"},
        404: {"description": "Consulta, unidad u opción no encontrada"},
        409: {"description": "La unidad ya votó, la consulta está cerrada o Idempotency-Key duplicada"},
    },
)
async def votar_en_consulta(
    consulta_id: int,
    datos: VotarConsultaRequest,
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
    redis_conn: aioredis.Redis = Depends(get_redis_client),
) -> ReciboVotoResponse:
    """Registra el voto inmutable de una unidad ponderado por su alícuota y emite recibo HMAC-SHA256."""
    verificar_usuario_activo(usuario)

    es_unica = await check_and_set_idempotency_key(
        redis_conn, idempotency_key, ttl_seconds=120, scope=f"votar:{consulta_id}:{datos.unidad_id}"
    )
    if not es_unica:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Petición duplicada detectada (Idempotency-Key ya procesada).",
        )

    res_c = await db.execute(select(ConsultaComunitaria).where(ConsultaComunitaria.id == consulta_id))
    consulta = res_c.scalars().first()
    if not consulta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consulta comunitaria no encontrada.")
    if consulta.estado != "ABIERTA":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La consulta ya se encuentra cerrada y no admite nuevos votos.",
        )

    res_op = await db.execute(
        select(OpcionConsulta).where(
            OpcionConsulta.id == datos.opcion_id,
            OpcionConsulta.consulta_id == consulta_id,
        )
    )
    opcion = res_op.scalars().first()
    if not opcion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opción de consulta no encontrada.")

    unidad, _ = await _validar_derecho_voto_unidad(db, usuario.id, datos.unidad_id)

    res_voto_previo = await db.execute(
        select(VotoConsulta).where(
            VotoConsulta.consulta_id == consulta_id,
            VotoConsulta.unidad_id == unidad.id,
        )
    )
    if res_voto_previo.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La unidad inmobiliaria ya emitió su voto en esta consulta.",
        )

    alicuota_capturada = Decimal(str(unidad.alicuota or Decimal("0.0000"))).quantize(CUATRO_DECIMALES)
    fecha_voto = datetime.now(UTC)
    fecha_voto_iso = fecha_voto.isoformat()
    secret_key = SECRET_KEY
    ip_cliente = request.client.host if request.client else "127.0.0.1"
    ip_hash = calcular_ip_hash_voto(ip_cliente, consulta_id, secret_key)
    firma_hmac = generar_firma_voto_consulta(
        consulta_id=consulta_id,
        unidad_id=unidad.id,
        opcion_id=opcion.id,
        alicuota_capturada=alicuota_capturada,
        fecha_voto_iso=fecha_voto_iso,
        secret_key=secret_key,
    )
    mensaje_verificacion = construir_mensaje_voto_consulta(
        consulta_id=consulta_id,
        unidad_id=unidad.id,
        opcion_id=opcion.id,
        alicuota_capturada=alicuota_capturada,
        fecha_voto_iso=fecha_voto_iso,
    )

    voto = VotoConsulta(
        consulta_id=consulta_id,
        unidad_id=unidad.id,
        usuario_id=usuario.id,
        opcion_id=opcion.id,
        alicuota_capturada=alicuota_capturada,
        fecha_voto=fecha_voto,
        ip_hash=ip_hash,
        firma_hmac=firma_hmac,
    )
    db.add(voto)
    try:
        await db.commit()
        await db.refresh(voto)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La unidad inmobiliaria ya emitió su voto en esta consulta.",
        ) from exc

    opciones, votos = await _cargar_opciones_y_votos(db, consulta_id)
    quorum_min = Decimal(str(consulta.quorum_minimo_alicuota)).quantize(CUATRO_DECIMALES)
    participacion_total, _, _ = _calcular_metricas_consulta(opciones, votos, quorum_min)

    return ReciboVotoResponse(
        voto_id=voto.id,
        consulta_id=consulta.id,
        titulo_consulta=consulta.titulo,
        unidad_id=unidad.id,
        identificador_unidad=unidad.identificador,
        usuario_id=usuario.id,
        opcion_id=opcion.id,
        opcion_etiqueta=opcion.etiqueta,
        alicuota_capturada=alicuota_capturada,
        participacion_total_alicuota=participacion_total,
        quorum_minimo_alicuota=quorum_min,
        fecha_voto=fecha_voto,
        ip_hash=ip_hash,
        firma_hmac=firma_hmac,
        mensaje_verificacion=mensaje_verificacion,
    )


def _generar_texto_acta_cierre(
    consulta: ConsultaComunitaria,
    estado_final: str,
    participacion: Decimal,
    aprobatoria: Decimal,
    opciones_resp: list[OpcionConsultaResultadoResponse],
    total_votos: int,
    hash_global: str,
) -> str:
    desglose = "; ".join(
        f"{op.etiqueta}: {op.votos_cantidad} votos ({op.alicuota_acumulada:.4f}% alícuota)"
        for op in opciones_resp
    )
    return (
        f"[ACTA AUTOMÁTICA LPH ART. 23/24] Cierre de '{consulta.titulo}' ({consulta.tipo_consulta}). "
        f"Resultado: {estado_final}. Regla de quórum: {consulta.regla_quorum} "
        f"(mínimo requerido: {Decimal(str(consulta.quorum_minimo_alicuota)):.4f}%). "
        f"Participación escrutada: {participacion:.4f}% ({total_votos} unidades). "
        f"Alícuota aprobatoria: {aprobatoria:.4f}%. Desglose: [{desglose}]. "
        f"Sello criptográfico de escrutinio HMAC-SHA256: {hash_global}"
    )


@router.post(
    "/{consulta_id}/cerrar",
    response_model=CerrarConsultaResponse,
    responses={
        403: {"description": "Solo Presidente o Secretario pueden cerrar consultas"},
        404: {"description": "Consulta no encontrada"},
        409: {"description": "La consulta ya fue cerrada o Idempotency-Key duplicada"},
    },
)
async def cerrar_consulta(
    consulta_id: int,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
    redis_conn: aioredis.Redis = Depends(get_redis_client),
) -> CerrarConsultaResponse:
    """Cierra el escrutinio de la consulta, determina su estado legal y asienta el acta en BitacoraActa."""
    verificar_roles(usuario, _ROLES_GOBERNANZA)

    es_unica = await check_and_set_idempotency_key(
        redis_conn, idempotency_key, ttl_seconds=120, scope=f"cerrar_consulta:{consulta_id}"
    )
    if not es_unica:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Petición duplicada detectada (Idempotency-Key ya procesada).",
        )

    res_c = await db.execute(select(ConsultaComunitaria).where(ConsultaComunitaria.id == consulta_id))
    consulta = res_c.scalars().first()
    if not consulta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consulta comunitaria no encontrada.")
    if consulta.estado != "ABIERTA":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La consulta ya fue cerrada previamente.",
        )

    opciones, votos = await _cargar_opciones_y_votos(db, consulta_id)
    quorum_min = Decimal(str(consulta.quorum_minimo_alicuota)).quantize(CUATRO_DECIMALES)
    participacion, aprobatoria, opciones_resp = _calcular_metricas_consulta(opciones, votos, quorum_min)
    aprobatorias_ids = {op.id for op in opciones if op.es_opcion_aprobatoria}
    alicuotas_map = {op.id: op.alicuota_acumulada for op in opciones_resp}
    estado_final, _, _ = evaluar_escrutinio_consulta(quorum_min, aprobatorias_ids, alicuotas_map)

    firmas_concat = "|".join(v.firma_hmac for v in votos) or f"SIN_VOTOS|{consulta.id}"
    hash_global = hmac.new(
        SECRET_KEY.encode("utf-8"),
        firmas_concat.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    ahora = datetime.now(UTC)
    contenido_acta = _generar_texto_acta_cierre(
        consulta, estado_final, participacion, aprobatoria, opciones_resp, len(votos), hash_global
    )
    acta = BitacoraActa(
        fecha=ahora.date(),
        hora=ahora.strftime("%H:%M"),
        ubicacion="Plataforma Digital LPH (Art. 23/24)",
        contenido=contenido_acta,
        autor_id=usuario.id,
    )
    db.add(acta)
    await db.flush()

    consulta.estado = estado_final
    consulta.acta_bitacora_id = acta.id
    await db.commit()
    await db.refresh(consulta)

    return CerrarConsultaResponse(
        consulta_id=consulta.id,
        titulo=consulta.titulo,
        estado=estado_final,
        regla_quorum=consulta.regla_quorum,
        quorum_minimo_alicuota=quorum_min,
        participacion_alicuota=participacion,
        alicuota_aprobatoria=aprobatoria,
        total_votos=len(votos),
        acta_bitacora_id=acta.id,
        hash_global_escrutinio=hash_global,
    )
