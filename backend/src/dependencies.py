"""Dependencias compartidas de FastAPI (autenticación de usuario actual)."""

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import get_db
from src.models import Usuario
from src.security import decode_access_token


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> Usuario:
    """Extrae y valida el usuario autenticado a partir de la cookie JWT HttpOnly."""
    auth_cookie = request.cookies.get("access_token")
    if not auth_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")

    token = auth_cookie.replace("Bearer ", "").strip()
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
