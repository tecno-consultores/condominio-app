"""Rutas administrativas: generación de estructura/unidades, activación de usuarios fantasma y Junta (Hito 4)."""

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import get_db
from src.dependencies import get_current_user, verificar_roles
from src.models import ContratoOcupacion, Estructura, Unidad, Usuario
from src.redis_client import check_and_set_idempotency_key, get_redis_client
from src.schemas import (
    EstructuraGenerarRequest,
    EstructuraGenerarResponse,
    JuntaCargoRequest,
    UnidadResponse,
    UsuarioAsignarRequest,
    UsuarioResponse,
)

router = APIRouter(prefix="/api", tags=["Administracion"])

_ROLES_DIRECTIVA = ("PRESIDENTE", "VICEPRESIDENTE")


@router.get("/estructura/unidades", response_model=list[UnidadResponse])
async def listar_unidades(db: AsyncSession = Depends(get_db)) -> list[Unidad]:
    """Lista las unidades registradas para el selector de registro y el panel administrativo."""
    res = await db.execute(select(Unidad).order_by(Unidad.identificador.asc()))
    return list(res.scalars().all())


@router.post(
    "/estructura/generar",
    response_model=EstructuraGenerarResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"description": "Permisos insuficientes"},
        409: {"description": "Idempotencia repetida o identificador de unidad duplicado"},
        500: {"description": "Error interno de base de datos"},
    },
)
async def generar_estructura(
    datos: EstructuraGenerarRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1),
    db: AsyncSession = Depends(get_db),
    redis_client: Any = Depends(get_redis_client),
    usuario: Usuario = Depends(get_current_user),
) -> EstructuraGenerarResponse:
    """Crea una estructura (EDIFICIO/CALLE) y autogenera su lote de unidades de forma idempotente."""
    verificar_roles(usuario, _ROLES_DIRECTIVA)

    es_nueva = await check_and_set_idempotency_key(
        redis_client,
        idempotency_key,
        scope=f"estructura:{usuario.id}",
    )
    if not es_nueva:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta operación de generación de estructura ya fue procesada.",
        )

    estructura = Estructura(nombre=datos.nombre, tipo=datos.tipo)
    db.add(estructura)
    try:
        await db.flush()
        unidades_creadas: list[Unidad] = []
        for ident in dict.fromkeys(i.strip() for i in datos.identificadores if i.strip()):
            unidad = Unidad(identificador=ident, estructura_id=estructura.id or 1)
            db.add(unidad)
            unidades_creadas.append(unidad)
        await db.commit()
        await db.refresh(estructura)
        for u in unidades_creadas:
            await db.refresh(u)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Uno o más identificadores de unidad ya existen en el condominio.",
        )
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al generar la estructura.",
        )

    return EstructuraGenerarResponse(
        estructura_id=estructura.id,
        nombre=estructura.nombre,
        tipo=estructura.tipo,
        unidades_creadas=len(unidades_creadas),
        unidades=[UnidadResponse.model_validate(u) for u in unidades_creadas],
    )


@router.get(
    "/usuarios/pendientes",
    response_model=list[UsuarioResponse],
    responses={403: {"description": "Permisos insuficientes"}},
)
async def listar_usuarios_pendientes(
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> list[Usuario]:
    """Lista los Usuarios Fantasma (es_activo=False) pendientes de aprobación por la Junta."""
    verificar_roles(usuario, _ROLES_DIRECTIVA)
    res = await db.execute(select(Usuario).where(Usuario.es_activo.is_(False)).order_by(Usuario.id.asc()))
    return list(res.scalars().all())


@router.put(
    "/usuarios/{usuario_id}/asignar",
    response_model=UsuarioResponse,
    responses={
        403: {"description": "Permisos insuficientes"},
        404: {"description": "Usuario o unidad no encontrada"},
    },
)
async def asignar_y_activar_usuario(
    usuario_id: int,
    datos: UsuarioAsignarRequest,
    db: AsyncSession = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
) -> Usuario:
    """Aprueba un Usuario Fantasma, le asigna unidad y rol, y registra su ContratoOcupacion activo."""
    verificar_roles(usuario_actual, _ROLES_DIRECTIVA)

    res_u = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    objetivo = res_u.scalars().first()
    if not objetivo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    res_unidad = await db.execute(select(Unidad).where(Unidad.id == datos.unidad_id))
    unidad = res_unidad.scalars().first()
    if not unidad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidad no encontrada.")

    res_contratos = await db.execute(
        select(ContratoOcupacion).where(
            ContratoOcupacion.usuario_id == objetivo.id,
            ContratoOcupacion.unidad_id == unidad.id,
        )
    )
    contratos_previos = list(res_contratos.scalars().all())
    if contratos_previos:
        for contrato in contratos_previos:
            contrato.tipo_ocupante = datos.tipo_ocupante
            contrato.es_activo = True
    else:
        db.add(
            ContratoOcupacion(
                usuario_id=objetivo.id,
                unidad_id=unidad.id,
                tipo_ocupante=datos.tipo_ocupante,
                es_activo=True,
            )
        )

    objetivo.es_activo = True
    objetivo.rol = datos.rol
    await db.commit()
    await db.refresh(objetivo)
    return objetivo


@router.put(
    "/junta/cargos",
    response_model=UsuarioResponse,
    responses={
        400: {"description": "El usuario no cumple el requisito de ser propietario activo"},
        403: {"description": "Permisos insuficientes"},
        404: {"description": "Usuario no encontrado"},
    },
)
async def asignar_cargo_junta(
    datos: JuntaCargoRequest,
    db: AsyncSession = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
) -> Usuario:
    """Asigna un cargo de Junta validando que el residente sea PROPIETARIO activo con unidad asignada."""
    verificar_roles(usuario_actual, ("PRESIDENTE",))

    res_u = await db.execute(select(Usuario).where(Usuario.id == datos.usuario_id))
    objetivo = res_u.scalars().first()
    if not objetivo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    res_prop = await db.execute(
        select(ContratoOcupacion).where(
            ContratoOcupacion.usuario_id == objetivo.id,
            ContratoOcupacion.es_activo.is_(True),
            ContratoOcupacion.tipo_ocupante == "PROPIETARIO",
        )
    )
    contrato_propietario = res_prop.scalars().first()
    if not objetivo.es_activo or not contrato_propietario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo los propietarios activos con unidad asignada pueden integrar la Junta de Condominio.",
        )

    objetivo.rol = datos.cargo
    await db.commit()
    await db.refresh(objetivo)
    return objetivo
