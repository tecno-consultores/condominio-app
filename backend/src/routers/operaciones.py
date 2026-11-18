"""Rutas operativas: conserjería, galería de voceros (máx. 30 fotos/mes), bitácora y comunicados (Hito 4)."""

import asyncio
from datetime import UTC, date, datetime
from email.message import EmailMessage
from email.parser import BytesParser
from email.policy import default as default_email_policy
from io import BytesIO
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from PIL import Image, UnidentifiedImageError
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import get_db
from src.dependencies import (
    IdempotentAPIRoute,
    exigir_idempotencia,
    get_current_user,
    verificar_roles,
    verificar_usuario_activo,
)
from src.models import (
    BitacoraActa,
    Comunicado,
    FotoVocero,
    Incidencia,
    PlantillaTarea,
    TareaDiaria,
    Usuario,
)
from src.redis_client import get_redis_client
from src.schemas import (
    BitacoraActaCreate,
    BitacoraActaResponse,
    ComunicadoCreate,
    ComunicadoResponse,
    EvidenciaUploadResponse,
    FotoVoceroCreate,
    FotoVoceroResponse,
    GaleriaVoceroResponse,
    GenerarTareasDiariasResponse,
    PlantillaTareaCreate,
    PlantillaTareaResponse,
    TareaCompletarRequest,
    TareaDiariaCreate,
    TareaDiariaResponse,
)
from src.security import (
    MAX_UPLOAD_SIZE_BYTES,
    read_uploaded_file_safely,
    validate_file_magic_bytes,
    validate_safe_outgoing_url_async,
)
from src.worker import (
    construir_clave_evidencia,
    encolar_tarea_media,
    generar_tareas_diarias_desde_plantillas,
    resolver_bucket_minio,
)

router = APIRouter(
    prefix="/api",
    tags=["Operaciones"],
    route_class=IdempotentAPIRoute,
    responses={401: {"description": "No autenticado"}},
)

LIMITE_FOTOS_MENSUAL_VOCEROS = 30
_ROLES_DIRECTIVA = ("PRESIDENTE", "VICEPRESIDENTE")
_ROLES_CONSERJERIA = ("CONSERJE", "PRESIDENTE", "VICEPRESIDENTE")
_ROLES_VOCERIA = ("VOCERO", "PRESIDENTE")
_ROLES_SECRETARIA = ("SECRETARIO", "PRESIDENTE")


@router.post(
    "/tareas/plantillas",
    response_model=PlantillaTareaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_idempotencia("tarea_plantilla", roles=_ROLES_DIRECTIVA))],
    responses={
        400: {"description": "Cuerpo JSON malformado"},
        403: {"description": "Permisos insuficientes"},
        409: {"description": "Petición duplicada (Idempotency-Key ya procesada)"},
    },
)
async def crear_plantilla_tarea(
    datos: PlantillaTareaCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> PlantillaTarea:
    """Crea una plantilla periódica de tareas para el conserje."""
    verificar_roles(usuario, _ROLES_DIRECTIVA)
    plantilla = PlantillaTarea(
        titulo=datos.titulo,
        area=datos.area,
        frecuencia=datos.frecuencia,
        activa=True,
    )
    db.add(plantilla)
    await db.commit()
    await db.refresh(plantilla)
    return plantilla


@router.post(
    "/tareas/diarias",
    response_model=TareaDiariaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_idempotencia("tarea_diaria", roles=_ROLES_DIRECTIVA))],
    responses={
        400: {"description": "Cuerpo JSON malformado"},
        403: {"description": "Permisos insuficientes"},
        404: {"description": "Incidencia vinculada no encontrada"},
        409: {"description": "Petición duplicada (Idempotency-Key ya procesada)"},
    },
)
async def asignar_tarea_directa(
    datos: TareaDiariaCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> TareaDiaria:
    """Asigna una tarea puntual al conserje; si está vinculada a una incidencia, la pasa a EN_PROCESO."""
    verificar_roles(usuario, _ROLES_DIRECTIVA)

    if datos.incidencia_id is not None:
        res_inc = await db.execute(select(Incidencia).where(Incidencia.id == datos.incidencia_id).with_for_update())
        incidencia = res_inc.scalars().first()
        if not incidencia:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidencia no encontrada.")
        incidencia.estado = "EN_PROCESO"

    tarea = TareaDiaria(
        plantilla_id=None,
        incidencia_id=datos.incidencia_id,
        titulo=datos.titulo,
        area=datos.area,
        fecha=datos.fecha or date.today(),
        completada=False,
    )
    db.add(tarea)
    await db.commit()
    await db.refresh(tarea)
    return tarea


@router.post(
    "/tareas/generar-diarias",
    response_model=GenerarTareasDiariasResponse,
    responses={403: {"description": "Permisos insuficientes"}},
)
async def ejecutar_cronjob_tareas_diarias(
    fecha: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> GenerarTareasDiariasResponse:
    """Dispara la generación idempotente de tareas diarias a partir de las plantillas activas."""
    verificar_roles(usuario, _ROLES_DIRECTIVA)
    creadas = await generar_tareas_diarias_desde_plantillas(db, fecha_objetivo=fecha)
    return GenerarTareasDiariasResponse(tareas_generadas=creadas)


@router.get(
    "/tareas/diarias",
    response_model=list[TareaDiariaResponse],
    responses={403: {"description": "Usuario fantasma sin activar"}},
)
async def listar_tareas_diarias(
    fecha: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> list[TareaDiaria]:
    """Devuelve el checklist de tareas del conserje para la fecha consultada."""
    verificar_usuario_activo(usuario)
    fecha_consulta = fecha or date.today()
    res = await db.execute(
        select(TareaDiaria)
        .where(TareaDiaria.fecha == fecha_consulta)
        .order_by(TareaDiaria.id.asc())
        .limit(limit)
        .offset(offset)
    )
    return list(res.scalars().all())


@router.put(
    "/tareas/{tarea_id}/completar",
    response_model=TareaDiariaResponse,
    dependencies=[Depends(exigir_idempotencia("completar_tarea:{tarea_id}", roles=_ROLES_CONSERJERIA))],
    responses={
        400: {"description": "Cuerpo JSON malformado"},
        403: {"description": "Permisos insuficientes"},
        404: {"description": "Tarea no encontrada"},
        409: {"description": "Petición duplicada (Idempotency-Key ya procesada)"},
    },
)
async def completar_tarea_diaria(
    tarea_id: int,
    datos: TareaCompletarRequest,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> TareaDiaria:
    """Marca una tarea del conserje como completada y cierra automáticamente su incidencia asociada."""
    verificar_roles(usuario, _ROLES_CONSERJERIA)

    res = await db.execute(select(TareaDiaria).where(TareaDiaria.id == tarea_id).with_for_update())
    tarea = res.scalars().first()
    if not tarea:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada.")

    tarea.completada = True
    tarea.url_evidencia = datos.url_evidencia
    tarea.completada_en = datetime.now(UTC)

    if tarea.incidencia_id is not None:
        res_inc = await db.execute(select(Incidencia).where(Incidencia.id == tarea.incidencia_id).with_for_update())
        incidencia = res_inc.scalars().first()
        if incidencia is not None:
            incidencia.estado = "CERRADO"

    await db.commit()
    await db.refresh(tarea)
    return tarea


@router.post(
    "/voceros/fotos",
    response_model=FotoVoceroResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_idempotencia("vocero_foto", roles=_ROLES_VOCERIA))],
    responses={
        400: {"description": "Cuerpo JSON malformado"},
        403: {"description": "Permisos insuficientes"},
        409: {"description": "Petición duplicada (Idempotency-Key ya procesada)"},
        429: {"description": "Límite mensual de 30 fotografías alcanzado"},
    },
)
async def subir_foto_vocero(
    datos: FotoVoceroCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> FotoVocero:
    """Registra una foto de inspección validando el límite estricto de 30 fotos por mes calendario."""
    verificar_roles(usuario, _ROLES_VOCERIA)

    res_existentes = await db.execute(select(FotoVocero).where(FotoVocero.periodo == datos.periodo).with_for_update())
    existentes = list(res_existentes.scalars().all())
    if len(existentes) >= LIMITE_FOTOS_MENSUAL_VOCEROS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Límite mensual de 30 fotografías alcanzado.",
        )

    foto = FotoVocero(
        usuario_id=usuario.id,
        periodo=datos.periodo,
        area=datos.area,
        comentario=datos.comentario,
        url_foto=datos.url_foto,
    )
    db.add(foto)
    await db.commit()
    await db.refresh(foto)
    return foto


@router.get(
    "/voceros/galeria",
    response_model=GaleriaVoceroResponse,
    responses={403: {"description": "Usuario fantasma sin activar"}},
)
async def listar_galeria_voceros(
    periodo: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> GaleriaVoceroResponse:
    """Lista las fotografías del periodo y devuelve el contador de cuota mensual (X / 30)."""
    verificar_usuario_activo(usuario)
    periodo_consulta = periodo or date.today().strftime("%Y-%m")
    res = await db.execute(
        select(FotoVocero).where(FotoVocero.periodo == periodo_consulta).order_by(FotoVocero.id.desc())
    )
    fotos = list(res.scalars().all())
    fotos_paginadas = fotos[offset : offset + limit]
    return GaleriaVoceroResponse(
        periodo=periodo_consulta,
        fotos_usadas_mes=len(fotos),
        limite_mensual=LIMITE_FOTOS_MENSUAL_VOCEROS,
        fotos=[FotoVoceroResponse.model_validate(f) for f in fotos_paginadas],
    )


@router.post(
    "/bitacora/acta",
    response_model=BitacoraActaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_idempotencia("bitacora_acta", roles=_ROLES_SECRETARIA))],
    responses={
        400: {"description": "Cuerpo JSON malformado"},
        403: {"description": "Permisos insuficientes"},
        409: {"description": "Petición duplicada (Idempotency-Key ya procesada)"},
    },
)
async def crear_acta_bitacora(
    datos: BitacoraActaCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> BitacoraActa:
    """Registra una nueva acta o minuta oficial en la bitácora del condominio."""
    verificar_roles(usuario, _ROLES_SECRETARIA)
    acta = BitacoraActa(
        fecha=datos.fecha,
        hora=datos.hora,
        ubicacion=datos.ubicacion,
        contenido=datos.contenido,
        autor_id=usuario.id,
    )
    db.add(acta)
    await db.commit()
    await db.refresh(acta)
    return acta


@router.get(
    "/bitacora/historial",
    response_model=list[BitacoraActaResponse],
    responses={403: {"description": "Usuario fantasma sin activar"}},
)
async def listar_historial_bitacora(
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> list[BitacoraActa]:
    """Devuelve la línea de tiempo de actas ordenadas de la más reciente a la más antigua."""
    verificar_usuario_activo(usuario)
    res = await db.execute(
        select(BitacoraActa).order_by(BitacoraActa.fecha.desc(), BitacoraActa.id.desc()).limit(limit).offset(offset)
    )
    return list(res.scalars().all())


@router.post(
    "/comunicados",
    response_model=ComunicadoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_idempotencia("comunicado", roles=_ROLES_SECRETARIA))],
    responses={
        400: {"description": "Enlace externo inseguro rechazado por Anti-SSRF"},
        403: {"description": "Permisos insuficientes"},
        409: {"description": "Petición duplicada (Idempotency-Key ya procesada)"},
    },
)
async def publicar_comunicado(
    datos: ComunicadoCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Comunicado:
    """Publica un comunicado en la cartelera validando que el enlace externo sea seguro (Anti-SSRF)."""
    verificar_roles(usuario, _ROLES_SECRETARIA)
    enlace = datos.enlace_externo
    if enlace is not None:
        try:
            enlace = await validate_safe_outgoing_url_async(enlace)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    comunicado = Comunicado(
        titulo=datos.titulo,
        contenido=datos.contenido,
        enlace_externo=enlace,
        activo=True,
    )
    db.add(comunicado)
    await db.commit()
    await db.refresh(comunicado)
    return comunicado


@router.get(
    "/comunicados/recientes",
    response_model=list[ComunicadoResponse],
    responses={403: {"description": "Usuario fantasma sin activar"}},
)
async def listar_comunicados_recientes(
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> list[Comunicado]:
    """Lista los comunicados activos para el carrusel del Dashboard."""
    verificar_usuario_activo(usuario)
    res = await db.execute(
        select(Comunicado).where(Comunicado.activo.is_(True)).order_by(Comunicado.id.desc()).limit(limit).offset(offset)
    )
    return list(res.scalars().all())


class _RequestStreamReader:
    """Adaptador de lectura acotada por streaming sobre Starlette request.stream()."""

    def __init__(self, request: Request) -> None:
        self._iterator = request.stream()

    async def read(self, size: int = -1) -> bytes:
        del size
        while True:
            try:
                chunk = await anext(self._iterator)
            except StopAsyncIteration:
                return b""
            if chunk:
                return chunk


def _buscar_parte_binaria(msg: EmailMessage) -> bytes | None:
    for part in msg.iter_parts():
        disp_name = part.get_param("name", header="Content-Disposition")
        if part.get_filename() or disp_name in {"archivo", "file"}:
            payload = part.get_payload(decode=True)
            if isinstance(payload, bytes):
                return payload
    return None


def _extraer_archivo_multipart(content_type: str, raw_body: bytes) -> bytes:
    envelope = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("latin-1", "ignore") + raw_body
    msg = BytesParser(policy=default_email_policy).parsebytes(envelope)
    if not msg.is_multipart():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cuerpo multipart/form-data inválido.",
        )
    contenido = _buscar_parte_binaria(msg)
    if contenido is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se encontró el campo binario de archivo en multipart/form-data.",
        )
    return contenido


def _validar_imagen_segura(file_bytes: bytes) -> None:
    try:
        with Image.open(BytesIO(file_bytes)) as img:
            img.verify()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Archivo de imagen corrupto o excede los límites seguros de resolución.",
        ) from exc


@router.post(
    "/evidencias/subir",
    response_model=EvidenciaUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(exigir_idempotencia("subir_evidencia", hash_body=False))],
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}},
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {"archivo": {"type": "string", "format": "binary"}},
                    }
                },
            },
        }
    },
    responses={
        400: {"description": "Cuerpo multipart/form-data inválido"},
        401: {"description": "No autenticado"},
        403: {"description": "Usuario fantasma sin activar"},
        409: {"description": "Petición duplicada (Idempotency-Key ya procesada)"},
        413: {"description": "El archivo excede el tamaño máximo de 2 MB"},
        415: {"description": "Formato binario de archivo no permitido"},
        422: {"description": "Parámetros o cabeceras inválidas"},
        503: {"description": "Cola de procesamiento multimedia no disponible"},
    },
)
async def subir_evidencia_segura(
    request: Request,
    categoria: Literal["comprobantes", "incidencias", "tareas", "voceros"] = Query(default="comprobantes"),
    redis_client: Any = Depends(get_redis_client),
    usuario: Usuario = Depends(get_current_user),
) -> EvidenciaUploadResponse:
    """Valida stream (<= 2 MB) y Magic Bytes de comprobantes/evidencias y encola conversión AVIF en worker."""
    verificar_usuario_activo(usuario)
    raw_body = await read_uploaded_file_safely(
        _RequestStreamReader(request),
        max_bytes=MAX_UPLOAD_SIZE_BYTES,
        verify_magic_bytes=False,
    )
    content_type = request.headers.get("content-type", "").strip()
    file_bytes = (
        _extraer_archivo_multipart(content_type, raw_body)
        if content_type.lower().startswith("multipart/form-data")
        else raw_body
    )
    mime_origen = validate_file_magic_bytes(file_bytes[:16])
    if mime_origen != "application/pdf":
        await asyncio.to_thread(_validar_imagen_segura, file_bytes)

    prefijo = f"{categoria}/{date.today().strftime('%Y-%m')}"
    objeto_key, formato_destino = construir_clave_evidencia(file_bytes, prefijo, mime_origen)
    try:
        await encolar_tarea_media(redis_client, file_bytes, prefijo, mime_origen, objeto_key)
    except (RedisError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cola de procesamiento multimedia temporalmente no disponible.",
        ) from exc

    bucket = resolver_bucket_minio()
    return EvidenciaUploadResponse(
        url=f"s3://{bucket}/{objeto_key}",
        mime_origen=mime_origen,
        formato_destino=formato_destino,
        bytes_recibidos=len(file_bytes),
        estado="ENCOLADO",
    )
