"""Dependencias compartidas de FastAPI (autenticación por Cookie/Bearer, RLS y RBAC Fail-Closed)."""

import inspect
from typing import Any, cast

import jwt
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import DEFAULT_CONDOMINIO_ID, bind_rls_tenant, get_db
from src.models import Usuario
from src.redis_client import get_redis_client, is_session_id_revoked, is_user_session_revoked
from src.security import decode_access_token

ROLES_ACTIVOS_VALIDOS: frozenset[str] = frozenset(
    {
        "PROPIETARIO",
        "INQUILINO",
        "CONSERJE",
        "PRESIDENTE",
        "VICEPRESIDENTE",
        "SECRETARIO",
        "TESORERO",
        "VOCERO",
    }
)


def extract_bearer_or_cookie_token(request: Request) -> str | None:
    """Extrae el JWT desde la cookie HttpOnly o desde la cabecera Authorization: Bearer."""
    auth_cookie = request.cookies.get("access_token")
    if auth_cookie:
        return auth_cookie.replace("Bearer ", "").strip()
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ").strip()
    return None


def _decodificar_payload_token(request: Request) -> dict[str, Any]:
    token = extract_bearer_or_cookie_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido") from exc
    if not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sin identificación de usuario")
    return payload


def _extraer_claim_condominio(payload: dict[str, Any]) -> int:
    raw = payload.get("condominio_id")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw > 0:
        return raw
    return DEFAULT_CONDOMINIO_ID


async def _validar_sesion_no_revocada(
    redis_conn: aioredis.Redis,
    user: Usuario,
    sid: str,
) -> None:
    user_id = getattr(user, "id", None)
    if user_id is not None and await is_user_session_revoked(redis_conn, int(user_id)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión revocada por la administración",
        )
    if sid and await is_session_id_revoked(redis_conn, sid):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión revocada",
        )


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis_conn: aioredis.Redis = Depends(get_redis_client),
) -> Usuario:
    """Extrae y valida el usuario autenticado e inyecta el condominio_id en la sesión RLS."""
    payload = _decodificar_payload_token(request)
    claim_condo = _extraer_claim_condominio(payload)
    await bind_rls_tenant(db, claim_condo)

    result = await db.execute(select(Usuario).where(Usuario.correo == payload["sub"]))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")

    user_condo = int(getattr(user, "condominio_id", claim_condo) or claim_condo)
    if user_condo != claim_condo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido para el condominio activo")
    await bind_rls_tenant(db, user_condo)
    await _validar_sesion_no_revocada(redis_conn, user, str(payload.get("sid") or ""))
    return user


def verificar_usuario_activo(usuario: Usuario) -> None:
    """Valida Fail-Closed que el usuario esté activo (es_activo=True) y posea un rol válido no-Fantasma."""
    es_activo = getattr(usuario, "es_activo", False) is True
    rol = str(getattr(usuario, "rol", "") or "")
    if not es_activo or rol not in ROLES_ACTIVOS_VALIDOS:
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


async def _resolver_override_usuario(request: Request, db: AsyncSession) -> Usuario | None:
    override_fn = request.app.dependency_overrides.get(get_current_user)
    if override_fn is None:
        return None
    candidato = override_fn()
    if inspect.isawaitable(candidato):
        candidato = await candidato
    if getattr(candidato, "es_activo", False) is not True:
        return None
    await bind_rls_tenant(db, int(getattr(candidato, "condominio_id", DEFAULT_CONDOMINIO_ID) or DEFAULT_CONDOMINIO_ID))
    return cast(Usuario, candidato)


async def _cargar_usuario_activo_desde_payload(
    db: AsyncSession,
    redis_conn: aioredis.Redis,
    payload: dict[str, Any],
) -> Usuario | None:
    correo = payload.get("sub")
    if not correo:
        return None
    claim_condo = _extraer_claim_condominio(payload)
    await bind_rls_tenant(db, claim_condo)
    res = await db.execute(select(Usuario).where(Usuario.correo == str(correo)))
    user = res.scalars().first()
    if not user or getattr(user, "es_activo", False) is not True:
        return None
    user_condo = int(getattr(user, "condominio_id", claim_condo) or claim_condo)
    if user_condo != claim_condo:
        return None
    await bind_rls_tenant(db, user_condo)
    try:
        await _validar_sesion_no_revocada(redis_conn, user, str(payload.get("sid") or ""))
    except HTTPException:
        return None
    return user


async def get_optional_active_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis_conn: aioredis.Redis = Depends(get_redis_client),
) -> Usuario | None:
    """Retorna el usuario activo si hay sesión válida; None para anónimos, tokens inválidos o Fantasmas."""
    if get_current_user in request.app.dependency_overrides:
        return await _resolver_override_usuario(request, db)
    token = extract_bearer_or_cookie_token(request)
    if not token:
        return None
    try:
        payload = decode_access_token(token)
    except jwt.InvalidTokenError:
        return None
    return await _cargar_usuario_activo_desde_payload(db, redis_conn, payload)
