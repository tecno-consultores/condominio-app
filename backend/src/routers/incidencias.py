"""Rutas del embudo de incidencias vecinales y lógica de adhesión comunitaria ('Me Sumo')."""

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import get_db
from src.dependencies import get_current_user, verificar_usuario_activo
from src.models import Incidencia, IncidenciaAdhesion, Usuario
from src.redis_client import check_and_set_idempotency_key, get_redis_client
from src.schemas import IncidenciaCreate, IncidenciaResponse
from src.worker import encolar_notificacion_correo

router = APIRouter(prefix="/api/incidencias", tags=["Incidencias"])


@router.get(
    "/abiertas",
    response_model=list[IncidenciaResponse],
    responses={403: {"description": "Usuario fantasma sin activar"}},
)
async def listar_incidencias_abiertas(
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> list[Incidencia]:
    """Lista las incidencias abiertas o en proceso ordenadas por prioridad comunitaria (adhesiones)."""
    verificar_usuario_activo(usuario)
    res = await db.execute(
        select(Incidencia)
        .where(Incidencia.estado.in_(("ABIERTO", "EN_PROCESO")))
        .order_by(Incidencia.adhesiones_count.desc(), Incidencia.id.desc())
    )
    return list(res.scalars().all())


@router.post(
    "/crear",
    response_model=IncidenciaResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"description": "Usuario fantasma sin activar"},
        409: {"description": "Petición duplicada (Idempotency-Key ya utilizada)"},
        500: {"description": "Error interno de base de datos"},
    },
)
async def crear_incidencia(
    datos: IncidenciaCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1),
    db: AsyncSession = Depends(get_db),
    redis_client: Any = Depends(get_redis_client),
    usuario: Usuario = Depends(get_current_user),
) -> Incidencia:
    """Crea un nuevo reporte de incidencia vecinal y encola notificación a la Junta de Condominio."""
    verificar_usuario_activo(usuario)

    es_nueva = await check_and_set_idempotency_key(
        redis_client,
        idempotency_key,
        scope=f"incidencia:{usuario.id}",
    )
    if not es_nueva:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta incidencia ya fue procesada.",
        )

    incidencia = Incidencia(
        usuario_creador_id=usuario.id,
        area=datos.area,
        descripcion=datos.descripcion,
        url_foto=datos.url_foto,
        estado="ABIERTO",
        adhesiones_count=1,
    )
    db.add(incidencia)
    try:
        await db.flush()
        db.add(
            IncidenciaAdhesion(
                incidencia_id=incidencia.id or 1,
                usuario_id=usuario.id,
            )
        )
        await db.commit()
        await db.refresh(incidencia)
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al registrar la incidencia.",
        )

    await encolar_notificacion_correo(
        destinatarios=["junta@condominio.local"],
        asunto=f"Nueva incidencia reportada en {datos.area}",
        cuerpo=datos.descripcion,
        redis_client=redis_client,
    )
    return incidencia


@router.post(
    "/{incidencia_id}/adherir",
    response_model=IncidenciaResponse,
    responses={
        403: {"description": "Usuario fantasma sin activar"},
        404: {"description": "Incidencia no encontrada"},
        409: {"description": "Incidencia cerrada o adhesión duplicada del mismo vecino"},
    },
)
async def adherir_a_incidencia(
    incidencia_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Incidencia:
    """Suma al vecino actual a una incidencia abierta ('Me Sumo'), incrementando su prioridad."""
    verificar_usuario_activo(usuario)

    res_inc = await db.execute(select(Incidencia).where(Incidencia.id == incidencia_id))
    incidencia = res_inc.scalars().first()
    if not incidencia:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidencia no encontrada.")

    if incidencia.estado == "CERRADO":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No es posible sumarse a una incidencia cerrada.",
        )

    res_adh = await db.execute(
        select(IncidenciaAdhesion).where(
            IncidenciaAdhesion.incidencia_id == incidencia_id,
            IncidenciaAdhesion.usuario_id == usuario.id,
        )
    )
    if res_adh.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya te sumaste a esta incidencia.",
        )

    db.add(IncidenciaAdhesion(incidencia_id=incidencia_id, usuario_id=usuario.id))
    incidencia.adhesiones_count = int(incidencia.adhesiones_count) + 1
    try:
        await db.commit()
        await db.refresh(incidencia)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya te sumaste a esta incidencia.",
        )
    return incidencia
