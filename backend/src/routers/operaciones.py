"""Rutas operativas: conserjería, galería de voceros (máx. 30 fotos/mes), bitácora y comunicados (Hito 4)."""

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import get_db
from src.dependencies import get_current_user, verificar_roles, verificar_usuario_activo
from src.models import (
    BitacoraActa,
    Comunicado,
    FotoVocero,
    Incidencia,
    PlantillaTarea,
    TareaDiaria,
    Usuario,
)
from src.schemas import (
    BitacoraActaCreate,
    BitacoraActaResponse,
    ComunicadoCreate,
    ComunicadoResponse,
    FotoVoceroCreate,
    FotoVoceroResponse,
    GaleriaVoceroResponse,
    PlantillaTareaCreate,
    PlantillaTareaResponse,
    TareaCompletarRequest,
    TareaDiariaCreate,
    TareaDiariaResponse,
)
from src.security import validate_safe_outgoing_url
from src.worker import generar_tareas_diarias_desde_plantillas

router = APIRouter(prefix="/api", tags=["Operaciones"])

LIMITE_FOTOS_MENSUAL_VOCEROS = 30
_ROLES_DIRECTIVA = ("PRESIDENTE", "VICEPRESIDENTE")
_ROLES_CONSERJERIA = ("CONSERJE", "PRESIDENTE", "VICEPRESIDENTE")
_ROLES_VOCERIA = ("VOCERO", "PRESIDENTE")
_ROLES_SECRETARIA = ("SECRETARIO", "PRESIDENTE")


@router.post(
    "/tareas/plantillas",
    response_model=PlantillaTareaResponse,
    status_code=status.HTTP_201_CREATED,
    responses={403: {"description": "Permisos insuficientes"}},
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
    responses={
        403: {"description": "Permisos insuficientes"},
        404: {"description": "Incidencia vinculada no encontrada"},
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
        res_inc = await db.execute(select(Incidencia).where(Incidencia.id == datos.incidencia_id))
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
    responses={403: {"description": "Permisos insuficientes"}},
)
async def ejecutar_cronjob_tareas_diarias(
    fecha: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> dict[str, int]:
    """Dispara la generación idempotente de tareas diarias a partir de las plantillas activas."""
    verificar_roles(usuario, _ROLES_DIRECTIVA)
    creadas = await generar_tareas_diarias_desde_plantillas(db, fecha_objetivo=fecha)
    return {"tareas_generadas": creadas}


@router.get(
    "/tareas/diarias",
    response_model=list[TareaDiariaResponse],
    responses={403: {"description": "Usuario fantasma sin activar"}},
)
async def listar_tareas_diarias(
    fecha: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> list[TareaDiaria]:
    """Devuelve el checklist de tareas del conserje para la fecha consultada."""
    verificar_usuario_activo(usuario)
    fecha_consulta = fecha or date.today()
    res = await db.execute(
        select(TareaDiaria).where(TareaDiaria.fecha == fecha_consulta).order_by(TareaDiaria.id.asc())
    )
    return list(res.scalars().all())


@router.put(
    "/tareas/{tarea_id}/completar",
    response_model=TareaDiariaResponse,
    responses={
        403: {"description": "Permisos insuficientes"},
        404: {"description": "Tarea no encontrada"},
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

    res = await db.execute(select(TareaDiaria).where(TareaDiaria.id == tarea_id))
    tarea = res.scalars().first()
    if not tarea:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada.")

    tarea.completada = True
    tarea.url_evidencia = datos.url_evidencia
    tarea.completada_en = datetime.now(UTC)

    if tarea.incidencia_id is not None:
        res_inc = await db.execute(select(Incidencia).where(Incidencia.id == tarea.incidencia_id))
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
    responses={
        403: {"description": "Permisos insuficientes"},
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

    res_existentes = await db.execute(select(FotoVocero).where(FotoVocero.periodo == datos.periodo))
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
    periodo: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
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
    return GaleriaVoceroResponse(
        periodo=periodo_consulta,
        fotos_usadas_mes=len(fotos),
        limite_mensual=LIMITE_FOTOS_MENSUAL_VOCEROS,
        fotos=[FotoVoceroResponse.model_validate(f) for f in fotos],
    )


@router.post(
    "/bitacora/acta",
    response_model=BitacoraActaResponse,
    status_code=status.HTTP_201_CREATED,
    responses={403: {"description": "Permisos insuficientes"}},
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
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> list[BitacoraActa]:
    """Devuelve la línea de tiempo de actas ordenadas de la más reciente a la más antigua."""
    verificar_usuario_activo(usuario)
    res = await db.execute(select(BitacoraActa).order_by(BitacoraActa.fecha.desc(), BitacoraActa.id.desc()))
    return list(res.scalars().all())


@router.post(
    "/comunicados",
    response_model=ComunicadoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Enlace externo inseguro rechazado por Anti-SSRF"},
        403: {"description": "Permisos insuficientes"},
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
            enlace = validate_safe_outgoing_url(enlace)
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
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> list[Comunicado]:
    """Lista los comunicados activos para el carrusel del Dashboard."""
    verificar_usuario_activo(usuario)
    res = await db.execute(select(Comunicado).where(Comunicado.activo.is_(True)).order_by(Comunicado.id.desc()))
    return list(res.scalars().all())
