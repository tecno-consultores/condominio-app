"""Rutas de Control de Acceso QR (HMAC-SHA256 + KeyDB Anti-Replay) y Paquetería en Garita (Hito 12)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies import get_current_user, verificar_roles, verificar_usuario_activo
from src.finanzas import (
    ErrorFinanciero,
    construir_token_pase_qr,
    decodificar_y_verificar_token_pase_qr,
    generar_firma_pase_qr,
)
from src.models import ContratoOcupacion, PaqueteRecibido, PaseVisita, Unidad, Usuario
from src.redis_client import (
    burn_qr_nonce,
    check_and_set_idempotency_key,
    get_redis_client,
    is_qr_nonce_burned,
)
from src.schemas import (
    PaqueteCreate,
    PaqueteResponse,
    PaseVisitaCreate,
    PaseVisitaResponse,
    VerificarPaseQRRequest,
    VerificarPaseQRResponse,
)
from src.security import SECRET_KEY, validate_safe_outgoing_url
from src.worker import encolar_notificacion_correo

router = APIRouter(prefix="/api", tags=["Accesos QR y Paquetería en Garita"])

_ROLES_GARITA = ("CONSERJE", "PRESIDENTE", "VOCERO")
_ROLES_PAQUETERIA = ("CONSERJE", "PRESIDENTE")
_ROLES_JUNTA_Y_GARITA = ("CONSERJE", "PRESIDENTE", "VICEPRESIDENTE", "SECRETARIO", "TESORERO", "VOCERO")
_MAX_SEGUNDOS_PASE_QR = 72 * 3600


def _normalizar_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


async def _unidades_activas_usuario(db: AsyncSession, usuario_id: int) -> set[int]:
    res = await db.execute(
        select(ContratoOcupacion.unidad_id).where(
            ContratoOcupacion.usuario_id == usuario_id,
            ContratoOcupacion.es_activo.is_(True),
            ContratoOcupacion.fecha_fin.is_(None),
        )
    )
    return {int(uid) for uid in res.scalars().all()}


async def _obtener_unidad_o_404(db: AsyncSession, unidad_id: int) -> Unidad:
    res = await db.execute(select(Unidad).where(Unidad.id == unidad_id))
    unidad = res.scalars().first()
    if not unidad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidad inmobiliaria no encontrada.")
    return unidad


async def _verificar_acceso_unidad_anfitriona(
    db: AsyncSession,
    usuario: Usuario,
    unidad_id: int,
) -> Unidad:
    unidad = await _obtener_unidad_o_404(db, unidad_id)
    if usuario.rol == "PRESIDENTE":
        return unidad
    unidades_propias = await _unidades_activas_usuario(db, usuario.id)
    if unidad_id not in unidades_propias:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No posee un contrato de ocupación activo sobre la unidad indicada.",
        )
    return unidad


def _resolver_ventana_validez(datos: PaseVisitaCreate) -> tuple[datetime, datetime]:
    ahora = datetime.now(UTC)
    desde = _normalizar_utc(datos.valido_desde) if datos.valido_desde else ahora
    hasta = _normalizar_utc(datos.valido_hasta) if datos.valido_hasta else desde + timedelta(hours=datos.horas_validez)
    duracion = (hasta - desde).total_seconds()
    if duracion <= 0 or duracion > _MAX_SEGUNDOS_PASE_QR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La ventana de validez del pase QR debe ser positiva y no exceder las 72 horas.",
        )
    return desde, hasta


def _serializar_pase(pase: PaseVisita, identificador_unidad: str, ahora: datetime | None = None) -> PaseVisitaResponse:
    ahora_utc = ahora or datetime.now(UTC)
    desde_utc = _normalizar_utc(pase.valido_desde)
    hasta_utc = _normalizar_utc(pase.valido_hasta)
    estado_efectivo = pase.estado
    if estado_efectivo == "ACTIVO" and ahora_utc > hasta_utc:
        estado_efectivo = "EXPIRADO"
    exp_unix = int(hasta_utc.timestamp())
    qr_token = construir_token_pase_qr(
        jti=pase.jti,
        unidad_id=pase.unidad_id,
        modalidad=pase.modalidad,
        exp_unix=exp_unix,
        firma_hmac=pase.firma_hmac,
    )
    return PaseVisitaResponse(
        id=pase.id,
        jti=pase.jti,
        unidad_id=pase.unidad_id,
        identificador_unidad=identificador_unidad,
        creado_por_id=pase.creado_por_id,
        nombre_visitante=pase.nombre_visitante,
        cedula_visitante=pase.cedula_visitante,
        placa_vehiculo=pase.placa_vehiculo,
        modalidad=pase.modalidad,
        valido_desde=desde_utc,
        valido_hasta=hasta_utc,
        estado=estado_efectivo,
        usado_en=pase.usado_en,
        verificado_por_id=pase.verificado_por_id,
        firma_hmac=pase.firma_hmac,
        qr_token=qr_token,
    )


@router.post(
    "/accesos/pases",
    status_code=status.HTTP_201_CREATED,
    response_model=PaseVisitaResponse,
    responses={
        400: {"description": "Ventana de validez inválida (> 72h)"},
        403: {"description": "Usuario Fantasma o sin contrato en la unidad"},
        404: {"description": "Unidad no encontrada"},
        409: {"description": "Idempotency-Key duplicada"},
    },
)
async def crear_pase_visita(
    datos: PaseVisitaCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
    redis_conn: aioredis.Redis = Depends(get_redis_client),
) -> PaseVisitaResponse:
    """Emite un PaseVisita firmado con HMAC-SHA256 y JTI único para verificación en garita."""
    verificar_usuario_activo(usuario)
    es_unica = await check_and_set_idempotency_key(
        redis_conn, idempotency_key, ttl_seconds=120, scope=f"crear_pase:{usuario.id}"
    )
    if not es_unica:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Petición duplicada detectada (Idempotency-Key ya procesada).",
        )

    unidad = await _verificar_acceso_unidad_anfitriona(db, usuario, datos.unidad_id)
    valido_desde, valido_hasta = _resolver_ventana_validez(datos)
    jti = str(uuid.uuid4())
    exp_unix = int(valido_hasta.timestamp())
    firma_hmac = generar_firma_pase_qr(
        jti=jti,
        unidad_id=unidad.id,
        modalidad=datos.modalidad,
        exp_unix=exp_unix,
        secret_key=SECRET_KEY,
    )
    placa_limpia = (
        datos.placa_vehiculo.strip().upper() if datos.placa_vehiculo and datos.placa_vehiculo.strip() else None
    )

    pase = PaseVisita(
        jti=jti,
        unidad_id=unidad.id,
        creado_por_id=usuario.id,
        nombre_visitante=datos.nombre_visitante.strip(),
        cedula_visitante=datos.cedula_visitante.strip().upper(),
        placa_vehiculo=placa_limpia,
        modalidad=datos.modalidad,
        valido_desde=valido_desde,
        valido_hasta=valido_hasta,
        estado="ACTIVO",
        firma_hmac=firma_hmac,
    )
    db.add(pase)
    await db.commit()
    await db.refresh(pase)
    return _serializar_pase(pase, unidad.identificador)


@router.get(
    "/accesos/pases/mios",
    response_model=list[PaseVisitaResponse],
    responses={403: {"description": "Usuario Fantasma o inactivo"}},
)
async def listar_mis_pases_visita(
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> list[PaseVisitaResponse]:
    """Lista los pases de visita activos e históricos de las unidades del residente."""
    verificar_usuario_activo(usuario)
    res_pases = await db.execute(select(PaseVisita).order_by(PaseVisita.id.desc()))
    todos_pases = list(res_pases.scalars().all())
    unidades_propias = await _unidades_activas_usuario(db, usuario.id)

    res_unidades = await db.execute(select(Unidad))
    mapa_unidades = {u.id: u.identificador for u in res_unidades.scalars().all()}
    ahora = datetime.now(UTC)

    filtrados = [
        p
        for p in todos_pases
        if usuario.rol == "PRESIDENTE" or p.creado_por_id == usuario.id or p.unidad_id in unidades_propias
    ]
    return [_serializar_pase(p, mapa_unidades.get(p.unidad_id, f"U-{p.unidad_id}"), ahora) for p in filtrados]


@router.delete(
    "/accesos/pases/{pase_id}",
    response_model=PaseVisitaResponse,
    responses={
        403: {"description": "Solo el creador del pase o el Presidente pueden revocarlo"},
        404: {"description": "Pase de visita no encontrado"},
    },
)
async def revocar_pase_visita(
    pase_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
    redis_conn: aioredis.Redis = Depends(get_redis_client),
) -> PaseVisitaResponse:
    """Revoca inmediatamente un pase de visita y quema su JTI en KeyDB Multi-Hilo."""
    verificar_usuario_activo(usuario)
    res = await db.execute(select(PaseVisita).where(PaseVisita.id == pase_id))
    pase = res.scalars().first()
    if not pase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pase de visita no encontrado.")

    if pase.creado_por_id != usuario.id and usuario.rol != "PRESIDENTE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el residente que emitió el pase o el Presidente pueden revocarlo.",
        )

    pase.estado = "REVOCADO"
    await burn_qr_nonce(redis_conn, pase.jti)
    await db.commit()
    await db.refresh(pase)
    unidad = await _obtener_unidad_o_404(db, pase.unidad_id)
    return _serializar_pase(pase, unidad.identificador)


async def _validar_estado_y_vigencia_pase(
    db: AsyncSession,
    redis_conn: aioredis.Redis,
    pase: PaseVisita,
    exp_unix: int,
    ahora: datetime,
) -> None:
    if pase.estado == "REVOCADO":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Alerta de Seguridad: Este pase QR fue revocado por el anfitrión",
        )
    if pase.modalidad == "UNICO_USO" and (pase.estado == "USADO" or await is_qr_nonce_burned(redis_conn, pase.jti)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Alerta de Seguridad: Este pase QR de único uso ya fue utilizado",
        )

    desde_utc = _normalizar_utc(pase.valido_desde)
    hasta_utc = _normalizar_utc(pase.valido_hasta)
    if ahora < desde_utc or ahora > hasta_utc or int(ahora.timestamp()) > exp_unix:
        if ahora > hasta_utc and pase.estado == "ACTIVO":
            pase.estado = "EXPIRADO"
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pase QR expirado o aún no vigente",
        )


@router.post(
    "/accesos/verificar-qr",
    response_model=VerificarPaseQRResponse,
    responses={
        400: {"description": "Firma criptográfica de pase QR inválida"},
        403: {"description": "Rol no autorizado para escaneo en garita"},
        409: {"description": "Pase QR ya utilizado (Anti-Replay), expirado, revocado o Idempotency-Key duplicada"},
    },
)
async def verificar_pase_qr_en_garita(
    datos: VerificarPaseQRRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
    redis_conn: aioredis.Redis = Depends(get_redis_client),
) -> VerificarPaseQRResponse:
    """Verifica firma HMAC-SHA256, vigencia temporal y unicidad Anti-Replay en KeyDB de un pase QR."""
    verificar_roles(usuario, _ROLES_GARITA)
    es_unica = await check_and_set_idempotency_key(
        redis_conn, idempotency_key, ttl_seconds=120, scope=f"scan_qr:{usuario.id}"
    )
    if not es_unica:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Petición duplicada detectada (Idempotency-Key ya procesada).",
        )

    try:
        jti, _, _, exp_unix, firma_esperada = decodificar_y_verificar_token_pase_qr(datos.qr_token, SECRET_KEY)
    except ErrorFinanciero as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    res_pase = await db.execute(select(PaseVisita).where(PaseVisita.jti == jti))
    pase = res_pase.scalars().first()
    if not pase or pase.firma_hmac != firma_esperada:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Firma criptográfica de pase QR inválida",
        )

    ahora = datetime.now(UTC)
    await _validar_estado_y_vigencia_pase(db, redis_conn, pase, exp_unix, ahora)

    if pase.modalidad == "UNICO_USO":
        ttl = max(60, int((_normalizar_utc(pase.valido_hasta) - ahora).total_seconds()) + 3600)
        primer_uso = await burn_qr_nonce(redis_conn, pase.jti, ttl_seconds=ttl)
        if not primer_uso:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Alerta de Seguridad: Este pase QR de único uso ya fue utilizado",
            )
        pase.estado = "USADO"

    pase.usado_en = ahora
    pase.verificado_por_id = usuario.id
    await db.commit()
    await db.refresh(pase)

    unidad = await _obtener_unidad_o_404(db, pase.unidad_id)
    return VerificarPaseQRResponse(
        autorizado=True,
        pase_id=pase.id,
        jti=pase.jti,
        unidad_id=pase.unidad_id,
        identificador_unidad=unidad.identificador,
        nombre_visitante=pase.nombre_visitante,
        cedula_visitante=pase.cedula_visitante,
        placa_vehiculo=pase.placa_vehiculo,
        modalidad=pase.modalidad,
        estado=pase.estado,
        usado_en=ahora,
        verificado_por_id=usuario.id,
        mensaje=f"Acceso autorizado a Unidad {unidad.identificador} para {pase.nombre_visitante}.",
    )


async def _notificar_paquete_unidad(
    db: AsyncSession,
    redis_conn: aioredis.Redis,
    unidad: Unidad,
    paquete: PaqueteRecibido,
) -> None:
    res_contratos = await db.execute(
        select(ContratoOcupacion.usuario_id).where(
            ContratoOcupacion.unidad_id == unidad.id,
            ContratoOcupacion.es_activo.is_(True),
            ContratoOcupacion.fecha_fin.is_(None),
        )
    )
    uids = [int(uid) for uid in res_contratos.scalars().all()]
    if not uids:
        return
    res_usuarios = await db.execute(select(Usuario.correo).where(Usuario.id.in_(uids)))
    correos = [str(c) for c in res_usuarios.scalars().all() if c]
    if correos:
        await encolar_notificacion_correo(
            destinatarios=correos,
            asunto=f"Paquete recibido en garita — Unidad {unidad.identificador}",
            cuerpo=f"Se recibió un paquete de {paquete.empresa_envio}: {paquete.descripcion}",
            redis_client=redis_conn,
        )


def _serializar_paquete(paquete: PaqueteRecibido, identificador_unidad: str) -> PaqueteResponse:
    return PaqueteResponse(
        id=paquete.id,
        unidad_id=paquete.unidad_id,
        identificador_unidad=identificador_unidad,
        recibido_por_id=paquete.recibido_por_id,
        empresa_envio=paquete.empresa_envio,
        descripcion=paquete.descripcion,
        url_foto_evidencia=paquete.url_foto_evidencia,
        estado=paquete.estado,
        fecha_recepcion=paquete.fecha_recepcion,
        fecha_entrega=paquete.fecha_entrega,
        retirado_por_id=paquete.retirado_por_id,
    )


@router.post(
    "/paqueteria/registrar",
    status_code=status.HTTP_201_CREATED,
    response_model=PaqueteResponse,
    responses={
        400: {"description": "URL de evidencia insegura (Anti-SSRF)"},
        403: {"description": "Solo Conserje o Presidente pueden registrar paquetes"},
        404: {"description": "Unidad destinataria no encontrada"},
        409: {"description": "Idempotency-Key duplicada"},
    },
)
async def registrar_paquete_en_garita(
    datos: PaqueteCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
    redis_conn: aioredis.Redis = Depends(get_redis_client),
) -> PaqueteResponse:
    """Registra la recepción de una encomienda en garita y encola notificación a la unidad destinataria."""
    verificar_roles(usuario, _ROLES_PAQUETERIA)
    es_unica = await check_and_set_idempotency_key(
        redis_conn, idempotency_key, ttl_seconds=120, scope=f"paquete:{usuario.id}"
    )
    if not es_unica:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Petición duplicada detectada (Idempotency-Key ya procesada).",
        )

    if datos.url_foto_evidencia and datos.url_foto_evidencia.startswith(("http://", "https://")):
        try:
            validate_safe_outgoing_url(datos.url_foto_evidencia)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    unidad = await _obtener_unidad_o_404(db, datos.unidad_id)
    ahora = datetime.now(UTC)
    paquete = PaqueteRecibido(
        unidad_id=unidad.id,
        recibido_por_id=usuario.id,
        empresa_envio=datos.empresa_envio.strip().upper(),
        descripcion=datos.descripcion.strip(),
        url_foto_evidencia=datos.url_foto_evidencia,
        estado="EN_GARITA",
        fecha_recepcion=ahora,
    )
    db.add(paquete)
    await db.commit()
    await db.refresh(paquete)

    await _notificar_paquete_unidad(db, redis_conn, unidad, paquete)
    return _serializar_paquete(paquete, unidad.identificador)


@router.get(
    "/paqueteria",
    response_model=list[PaqueteResponse],
    responses={403: {"description": "Usuario Fantasma o inactivo"}},
)
async def listar_paqueteria(
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> list[PaqueteResponse]:
    """Lista paquetes pendientes en garita e historial de entregas (filtrado por unidad para residentes)."""
    verificar_usuario_activo(usuario)
    res_paquetes = await db.execute(select(PaqueteRecibido).order_by(PaqueteRecibido.id.desc()))
    paquetes = list(res_paquetes.scalars().all())
    res_unidades = await db.execute(select(Unidad))
    mapa_unidades = {u.id: u.identificador for u in res_unidades.scalars().all()}

    if usuario.rol in _ROLES_JUNTA_Y_GARITA:
        visibles = paquetes
    else:
        unidades_propias = await _unidades_activas_usuario(db, usuario.id)
        visibles = [p for p in paquetes if p.unidad_id in unidades_propias]

    return [_serializar_paquete(p, mapa_unidades.get(p.unidad_id, f"U-{p.unidad_id}")) for p in visibles]


@router.put(
    "/paqueteria/{paquete_id}/entregar",
    response_model=PaqueteResponse,
    responses={
        403: {"description": "Sin permisos para retirar el paquete de otra unidad"},
        404: {"description": "Paquete no encontrado"},
        409: {"description": "El paquete ya fue entregado previamente"},
    },
)
async def confirmar_entrega_paquete(
    paquete_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> PaqueteResponse:
    """Marca un paquete como ENTREGADO registrando fecha y usuario que retira o confirma."""
    verificar_usuario_activo(usuario)
    res = await db.execute(select(PaqueteRecibido).where(PaqueteRecibido.id == paquete_id))
    paquete = res.scalars().first()
    if not paquete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paquete no encontrado.")

    if usuario.rol not in _ROLES_PAQUETERIA:
        unidades_propias = await _unidades_activas_usuario(db, usuario.id)
        if paquete.unidad_id not in unidades_propias:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el conserje o el residente de la unidad destinataria pueden confirmar la entrega.",
            )

    if paquete.estado == "ENTREGADO":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El paquete ya fue entregado previamente.",
        )

    paquete.estado = "ENTREGADO"
    paquete.fecha_entrega = datetime.now(UTC)
    paquete.retirado_por_id = usuario.id
    await db.commit()
    await db.refresh(paquete)
    unidad = await _obtener_unidad_o_404(db, paquete.unidad_id)
    return _serializar_paquete(paquete, unidad.identificador)
