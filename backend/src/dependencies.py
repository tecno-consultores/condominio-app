"""Dependencias compartidas de FastAPI (autenticación por Cookie/Bearer, RLS y RBAC Fail-Closed)."""

import hashlib
import inspect
import json
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass
from typing import Any, cast

import jwt
import redis.asyncio as aioredis
from fastapi import Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import DEFAULT_CONDOMINIO_ID, bind_rls_tenant, get_db
from src.models import Usuario
from src.redis_client import (
    IdempotencyResponsePayload,
    acquire_idempotency_slot,
    build_scoped_idempotency_key,
    get_redis_client,
    is_session_id_revoked,
    is_user_session_revoked,
    release_idempotency_slot,
    store_idempotency_response,
)
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


def _extraer_user_condo(user: Usuario, fallback: int) -> int:
    """Obtiene el condominio_id entero del usuario o retorna el respaldo del token."""
    raw = getattr(user, "condominio_id", fallback)
    return int(raw) if raw else fallback


def _validar_usuario_en_tenant(user: Usuario | None, claim_condo: int) -> tuple[Usuario, int] | None:
    """Verifica que el usuario exista, esté activo y pertenezca al condominio del claim."""
    if user is None or getattr(user, "es_activo", False) is not True:
        return None
    user_condo = _extraer_user_condo(user, claim_condo)
    if user_condo != claim_condo:
        return None
    return user, user_condo


async def _sesion_activa_valida(redis_conn: aioredis.Redis, user: Usuario, sid: Any) -> bool:
    """Comprueba de forma no bloqueante que la sesión no haya sido revocada en Redis."""
    try:
        await _validar_sesion_no_revocada(redis_conn, user, str(sid or ""))
        return True
    except HTTPException:
        return False


async def _cargar_usuario_activo_desde_payload(
    db: AsyncSession,
    redis_conn: aioredis.Redis,
    payload: dict[str, Any],
) -> Usuario | None:
    correo = payload.get("sub")
    if not correo:
        return None
    claim_condo = _extraer_claim_condominio(payload)
    # Fija el tenant antes del SELECT para cumplir la política RLS en PostgreSQL
    await bind_rls_tenant(db, claim_condo)
    res = await db.execute(select(Usuario).where(Usuario.correo == str(correo)))
    validado = _validar_usuario_en_tenant(res.scalars().first(), claim_condo)
    if validado is None:
        return None
    user, user_condo = validado
    await bind_rls_tenant(db, user_condo)
    if not await _sesion_activa_valida(redis_conn, user, payload.get("sid")):
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


class IdempotencyReplayException(Exception):
    """Excepción de control para devolver la respuesta idempotente cacheada con cabecera X-Idempotency-Replayed."""

    def __init__(self, status_code: int, body: Any) -> None:
        super().__init__("Idempotency replay")
        self.status_code = status_code
        self.body = body


@dataclass(frozen=True)
class ActiveIdempotencySlot:
    redis_conn: aioredis.Redis
    redis_key: str
    payload_hash: str


async def _release_request_slot(request: Request) -> None:
    slot: ActiveIdempotencySlot | None = getattr(request.state, "idempotency_slot", None)
    if slot is None:
        return
    request.state.idempotency_slot = None
    await release_idempotency_slot(slot.redis_conn, slot.redis_key)


def _decode_response_json(response: Response) -> Any:
    raw_body = getattr(response, "body", b"")
    if not raw_body:
        return None
    try:
        return json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None


async def _finalize_request_slot(request: Request, response: Response) -> None:
    slot: ActiveIdempotencySlot | None = getattr(request.state, "idempotency_slot", None)
    if slot is None:
        return
    request.state.idempotency_slot = None
    if 200 <= response.status_code < 300:
        await store_idempotency_response(
            slot.redis_conn,
            slot.redis_key,
            IdempotencyResponsePayload(
                payload_hash=slot.payload_hash,
                status_code=response.status_code,
                body=_decode_response_json(response),
            ),
        )
        return
    await release_idempotency_slot(slot.redis_conn, slot.redis_key)


class IdempotentAPIRoute(APIRoute):
    """Ruta FastAPI con replay automático en 2xx y liberación de Idempotency-Key en errores 4xx/5xx."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original_handler = super().get_route_handler()

        async def _custom_handler(request: Request) -> Response:
            try:
                response = await original_handler(request)
            except IdempotencyReplayException as replay:
                return JSONResponse(
                    status_code=replay.status_code,
                    content=replay.body,
                    headers={"X-Idempotency-Replayed": "true"},
                )
            except Exception:
                await _release_request_slot(request)
                raise
            await _finalize_request_slot(request, response)
            return response

        return _custom_handler


async def _compute_request_payload_hash(request: Request, *, hash_body: bool) -> str:
    if not hash_body:
        meta = f"{request.method}:{request.url.path}:{request.url.query}:{request.headers.get('content-length', '')}"
        return hashlib.sha256(meta.encode("utf-8")).hexdigest()
    body_bytes = await request.body()
    return hashlib.sha256(body_bytes).hexdigest()


async def _claim_idempotency_slot(
    request: Request,
    redis_conn: aioredis.Redis,
    redis_key: str,
    *,
    hash_body: bool = True,
) -> None:
    payload_hash = await _compute_request_payload_hash(request, hash_body=hash_body)
    slot_result = await acquire_idempotency_slot(redis_conn, redis_key, payload_hash)
    if slot_result.acquired:
        request.state.idempotency_slot = ActiveIdempotencySlot(
            redis_conn=redis_conn,
            redis_key=redis_key,
            payload_hash=payload_hash,
        )
        return
    if slot_result.replay_status is not None:
        raise IdempotencyReplayException(status_code=slot_result.replay_status, body=slot_result.replay_body)
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=slot_result.conflict_detail or "Petición duplicada detectada (Idempotency-Key ya procesada).",
    )


@dataclass(frozen=True)
class _PoliticaIdempotencia:
    """Configuración inmutable de autorización y hashing para la guardia idempotente."""

    scope_template: str
    roles: tuple[str, ...] | None
    require_active: bool
    hash_body: bool


@dataclass(frozen=True)
class _ContextoIdempotencia:
    """Dependencias de petición inyectadas para ejecutar la guardia de idempotencia."""

    request: Request
    usuario: Usuario
    idempotency_key: str
    redis_conn: aioredis.Redis


async def _resolver_guardia_idempotencia(
    politica: _PoliticaIdempotencia,
    ctx: _ContextoIdempotencia,
) -> None:
    """Valida RBAC/usuario activo y reclama el slot idempotente en Redis."""
    if politica.roles is not None:
        verificar_roles(ctx.usuario, politica.roles)
    elif politica.require_active:
        verificar_usuario_activo(ctx.usuario)
    condo_id = _extraer_user_condo(ctx.usuario, DEFAULT_CONDOMINIO_ID)
    uid_raw = getattr(ctx.usuario, "id", 0)
    usuario_id = int(uid_raw) if uid_raw else 0
    scope = politica.scope_template.format(**ctx.request.path_params)
    redis_key = build_scoped_idempotency_key(condo_id, usuario_id, scope, ctx.idempotency_key)
    await _claim_idempotency_slot(ctx.request, ctx.redis_conn, redis_key, hash_body=politica.hash_body)


def exigir_idempotencia(
    scope_template: str,
    *,
    roles: tuple[str, ...] | None = None,
    require_active: bool = True,
    hash_body: bool = True,
) -> Callable[..., Awaitable[None]]:
    """Dependencia FastAPI que valida RBAC/activo y adquiere idemp:{condo}:{user}:{scope}:{key}."""
    politica = _PoliticaIdempotencia(
        scope_template=scope_template,
        roles=roles,
        require_active=require_active,
        hash_body=hash_body,
    )

    # FastAPI resuelve Depends/Header inspeccionando directamente la firma del closure _dependency
    async def _dependency(
        request: Request,
        usuario: Usuario = Depends(get_current_user),
        idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
        redis_conn: aioredis.Redis = Depends(get_redis_client),
    ) -> None:
        await _resolver_guardia_idempotencia(
            politica,
            _ContextoIdempotencia(
                request=request,
                usuario=usuario,
                idempotency_key=idempotency_key,
                redis_conn=redis_conn,
            ),
        )

    return _dependency


def exigir_idempotencia_anonima(scope: str) -> Callable[..., Awaitable[None]]:
    """Dependencia FastAPI para rutas pre-auth (p. ej. /api/auth/register)."""

    async def _dependency(
        request: Request,
        idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
        redis_conn: aioredis.Redis = Depends(get_redis_client),
    ) -> None:
        redis_key = build_scoped_idempotency_key(DEFAULT_CONDOMINIO_ID, 0, scope, idempotency_key)
        await _claim_idempotency_slot(request, redis_conn, redis_key, hash_body=True)

    return _dependency
