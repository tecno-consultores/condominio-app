"""Dependencias compartidas de FastAPI (autenticación de usuario actual por Cookie o Bearer)."""

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import get_db
from src.models import Usuario
from src.security import decode_access_token


def extract_bearer_or_cookie_token(request: Request) -> str | None:
    """Extrae el JWT desde la cookie HttpOnly o desde la cabecera Authorization: Bearer."""
    auth_cookie = request.cookies.get("access_token")
    if auth_cookie:
        return auth_cookie.replace("Bearer ", "").strip()
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ").strip()
    return None


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> Usuario:
    """Extrae y valida el usuario autenticado a partir de la cookie JWT HttpOnly o token Bearer."""
    token = extract_bearer_or_cookie_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    correo = payload.get("sub")
    if not correo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sin identificación de usuario")

    result = await db.execute(select(Usuario).where(Usuario.correo == correo))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return user


def verificar_usuario_activo(usuario: Usuario) -> None:
    """Rechaza a Usuarios Fantasma (es_activo=False o rol='FANTASMA') con HTTP 403."""
    es_activo = getattr(usuario, "es_activo", True)
    rol = getattr(usuario, "rol", "")
    if not es_activo or rol == "FANTASMA":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta pendiente de aprobación por la Junta de Condominio.",
        )


def verificar_roles(usuario: Usuario, roles_permitidos: tuple[str, ...]) -> None:
    """Valida que el usuario esté activo y posea uno de los roles autorizados (RBAC)."""
    verificar_usuario_activo(usuario)
    if getattr(usuario, "rol", "") not in roles_permitidos:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para ejecutar esta acción.",
        )
