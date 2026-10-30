from typing import Any

import jwt
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import get_db
from src.dependencies import extract_bearer_or_cookie_token
from src.models import ContratoOcupacion, Usuario
from src.redis_client import (
    check_and_set_idempotency_key,
    get_redis_client,
    is_user_session_revoked,
)
from src.schemas import UsuarioCreate, UsuarioResponse
from src.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


class LoginData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correo: str
    password: str


@router.post(
    "/register",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Cuerpo JSON malformado"},
        409: {"description": "Usuario ya registrado o petición duplicada (Idempotency-Key ya procesada)"},
    },
)
async def register_user(
    user: UsuarioCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    redis_conn: aioredis.Redis = Depends(get_redis_client),
) -> Any:
    try:
        is_unique = await check_and_set_idempotency_key(redis_conn, idempotency_key, ttl_seconds=120, scope="register")
        if not is_unique:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Petición duplicada detectada (Idempotency-Key ya procesada)",
            )

        result = await db.execute(
            select(Usuario).where((Usuario.correo == user.correo) | (Usuario.cedula == user.cedula))
        )
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuario ya registrado")

        new_user = Usuario(
            nombre=user.nombre,
            cedula=user.cedula,
            correo=user.correo,
            telefono=user.telefono,
            password_hash=get_password_hash(user.password),
            es_activo=False,
            rol="FANTASMA",
        )
        db.add(new_user)
        await db.flush()

        nuevo_contrato = ContratoOcupacion(
            usuario_id=new_user.id,
            unidad_id=user.unidad_solicitada_id,
            tipo_ocupante=user.tipo_ocupante_solicitado,
            es_activo=False,
            puede_votar_asamblea=(user.tipo_ocupante_solicitado == "PROPIETARIO"),
        )
        db.add(nuevo_contrato)
        await db.commit()
        await db.refresh(new_user)

        return new_user
    except HTTPException:
        raise
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Datos inválidos o duplicados en el registro",
        ) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en base de datos al registrar",
        ) from exc


@router.post(
    "/login",
    responses={
        400: {"description": "Cuerpo JSON malformado"},
        401: {"description": "Credenciales inválidas"},
    },
)
async def login(response: Response, login_data: LoginData, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    result = await db.execute(select(Usuario).where(Usuario.correo == login_data.correo))
    user = result.scalars().first()

    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    access_token = create_access_token(data={"sub": user.correo, "rol": user.rol, "id": user.id})
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return {"message": "Login exitoso", "rol": user.rol}


@router.get(
    "/me",
    responses={
        401: {"description": "No autenticado"},
        404: {"description": "Usuario no encontrado"},
    },
)
async def get_me(request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    token = extract_bearer_or_cookie_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido") from exc

    user_email = payload.get("sub")
    if not user_email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sin identificación de usuario")

    result = await db.execute(select(Usuario).where(Usuario.correo == user_email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    if getattr(user, "id", None) is not None and await is_user_session_revoked(get_redis_client(), int(user.id)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión revocada por la administración",
        )

    return {
        "id": user.id,
        "correo": user.correo,
        "nombre": user.nombre,
        "rol": user.rol,
        "es_activo": user.es_activo,
    }
