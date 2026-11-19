import json
import secrets
from typing import Any

import jwt
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import DEFAULT_CONDOMINIO_ID, bind_rls_tenant, get_db
from src.dependencies import (
    IdempotentAPIRoute,
    exigir_idempotencia_anonima,
    extract_bearer_or_cookie_token,
)
from src.models import ContratoOcupacion, Unidad, Usuario
from src.redis_client import (
    REVOKED_USER_TTL_SECONDS,
    clear_login_failures,
    get_redis_client,
    get_refresh_token_from_grace_period,
    is_login_locked_out,
    is_session_id_revoked,
    is_user_session_revoked,
    mark_refresh_jti_used,
    record_login_failure,
    revoke_session_id,
    revoke_user_session,
    rotate_refresh_token_with_grace_period,
)
from src.schemas import (
    AuthMeResponse,
    AuthSessionResponse,
    LogoutResponse,
    UsuarioCreate,
    UsuarioResponse,
)
from src.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    decode_token_unverified_exp,
    generate_csrf_token,
    get_password_hash_async,
    is_trusted_proxy_ip,
    should_use_secure_cookie,
    verify_password_async,
)

router = APIRouter(prefix="/api/auth", tags=["Autenticación"], route_class=IdempotentAPIRoute)


class LoginData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correo: str
    password: str = Field(..., min_length=8, max_length=128)


def _extract_client_ip(request: Request) -> str:
    direct_host = request.client.host if request.client else "unknown"
    if is_trusted_proxy_ip(direct_host):
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if forwarded:
            return forwarded
    return direct_host


def _extract_refresh_token(request: Request) -> str | None:
    cookie_val = request.cookies.get("refresh_token")
    if cookie_val:
        return cookie_val.removeprefix("Bearer ").strip()
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ").strip()
    return None


def _emitir_cookies_sesion(
    response: Response,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
) -> None:
    """Fija las cookies HttpOnly de acceso/renovación y la cookie legible X-CSRF-Token."""
    secure_flag = should_use_secure_cookie()
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=secure_flag,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure_flag,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=secure_flag,
        samesite="lax",
        path="/",
    )
    response.headers["X-CSRF-Token"] = csrf_token


def _limpiar_cookies_sesion(response: Response) -> None:
    """Elimina cookies de sesión e instruye limpieza del almacenamiento del navegador (Logout)."""
    secure_flag = should_use_secure_cookie()
    for cookie_name in ("access_token", "refresh_token", "csrf_token"):
        response.delete_cookie(key=cookie_name, path="/", samesite="lax", secure=secure_flag)
    response.headers["Clear-Site-Data"] = '"cookies", "storage", "cache"'


def _crear_par_tokens(user: Usuario, sid: str) -> tuple[str, str, str]:
    condo_id = int(getattr(user, "condominio_id", DEFAULT_CONDOMINIO_ID) or DEFAULT_CONDOMINIO_ID)
    claims: dict[str, Any] = {
        "sub": user.correo,
        "rol": user.rol,
        "id": user.id,
        "sid": sid,
        "condominio_id": condo_id,
    }
    access_token = create_access_token(data=claims)
    refresh_token = create_refresh_token(
        data={"sub": user.correo, "id": user.id, "sid": sid, "condominio_id": condo_id}
    )
    csrf_token = generate_csrf_token(sid)
    return access_token, refresh_token, csrf_token


def _entero_estricto_o_none(valor: Any) -> int | None:
    if isinstance(valor, int) and not isinstance(valor, bool):
        return valor
    return None


async def _resolver_unidad_activa_id(db: AsyncSession, user: Any) -> int | None:
    if not isinstance(user, Usuario):
        return _entero_estricto_o_none(getattr(user, "unidad_activa_id", None))
    stmt = (
        select(ContratoOcupacion.unidad_id)
        .where(
            ContratoOcupacion.usuario_id == user.id,
            ContratoOcupacion.es_activo.is_(True),
            ContratoOcupacion.fecha_fin.is_(None),
        )
        .order_by(ContratoOcupacion.id.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    return _entero_estricto_o_none(res.scalars().first())


async def _validar_registro_disponible(db: AsyncSession, user: UsuarioCreate) -> None:
    result = await db.execute(select(Usuario).where((Usuario.correo == user.correo) | (Usuario.cedula == user.cedula)))
    if result.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuario ya registrado")

    res_unidad = await db.execute(select(Unidad.id).where(Unidad.id == user.unidad_solicitada_id))
    if res_unidad.scalars().first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unidad inmobiliaria solicitada no encontrada",
        )


async def _crear_usuario_fantasma_y_contrato(db: AsyncSession, user: UsuarioCreate) -> Usuario:
    password_hash = await get_password_hash_async(user.password)
    new_user = Usuario(
        condominio_id=DEFAULT_CONDOMINIO_ID,
        nombre=user.nombre,
        cedula=user.cedula,
        correo=user.correo,
        telefono=user.telefono,
        password_hash=password_hash,
        es_activo=False,
        rol="FANTASMA",
    )
    db.add(new_user)
    await db.flush()

    nuevo_contrato = ContratoOcupacion(
        condominio_id=DEFAULT_CONDOMINIO_ID,
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


@router.post(
    "/register",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_idempotencia_anonima("register"))],
    responses={
        400: {"description": "Cuerpo JSON malformado"},
        404: {"description": "Unidad inmobiliaria solicitada no encontrada"},
        409: {"description": "Usuario ya registrado o petición duplicada (Idempotency-Key ya procesada)"},
    },
)
async def register_user(
    user: UsuarioCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    try:
        await bind_rls_tenant(db, DEFAULT_CONDOMINIO_ID)
        await _validar_registro_disponible(db, user)
        return await _crear_usuario_fantasma_y_contrato(db, user)
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


async def _verificar_estado_cuenta_login(redis_conn: aioredis.Redis, user: Usuario) -> None:
    user_id = getattr(user, "id", None)
    if user_id is not None and await is_user_session_revoked(redis_conn, int(user_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta o sesión revocada por la administración.",
        )
    if not getattr(user, "es_activo", False) and getattr(user, "rol", "") != "FANTASMA":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta deshabilitada por la administración.",
        )


@router.post(
    "/login",
    response_model=AuthSessionResponse,
    responses={
        400: {"description": "Cuerpo JSON malformado"},
        401: {"description": "Credenciales inválidas"},
        403: {"description": "Cuenta revocada o deshabilitada"},
        429: {"description": "Demasiados intentos fallidos (Lockout temporal 15 minutos)"},
    },
)
async def login(
    request: Request,
    response: Response,
    login_data: LoginData,
    db: AsyncSession = Depends(get_db),
    redis_conn: aioredis.Redis = Depends(get_redis_client),
) -> AuthSessionResponse:
    """Autentica credenciales PBKDF2 en hilo separado, aplica lockout Lua y emite cookies + CSRF."""
    client_ip = _extract_client_ip(request)
    if await is_login_locked_out(redis_conn, client_ip, login_data.correo):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos fallidos de inicio de sesión. Intente nuevamente en 15 minutos.",
        )

    await bind_rls_tenant(db, DEFAULT_CONDOMINIO_ID)
    result = await db.execute(select(Usuario).where(Usuario.correo == login_data.correo))
    user = result.scalars().first()

    password_ok = await verify_password_async(
        login_data.password,
        user.password_hash if user is not None else DUMMY_PASSWORD_HASH,
    )
    if user is None or not password_ok:
        await record_login_failure(redis_conn, client_ip, login_data.correo)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    await _verificar_estado_cuenta_login(redis_conn, user)
    await clear_login_failures(redis_conn, client_ip, login_data.correo)

    sid = secrets.token_urlsafe(24)
    access_token, refresh_token, csrf_token = _crear_par_tokens(user, sid)
    _emitir_cookies_sesion(response, access_token, refresh_token, csrf_token)
    return AuthSessionResponse(message="Login exitoso", rol=user.rol, csrf_token=csrf_token)


async def _revocar_payload_sesion(redis_conn: aioredis.Redis, payload: dict[str, Any]) -> None:
    """Revoca únicamente el sid de la sesión actual y quema su JTI refresh (aísla otros dispositivos)."""
    sid = payload.get("sid")
    if sid:
        await revoke_session_id(redis_conn, str(sid), ttl_seconds=REVOKED_USER_TTL_SECONDS)
    jti = payload.get("jti")
    if payload.get("typ") == "refresh" and jti:
        await mark_refresh_jti_used(redis_conn, str(jti), ttl_seconds=REVOKED_USER_TTL_SECONDS)


async def _revocar_tokens_entrantes(request: Request, redis_conn: aioredis.Redis) -> None:
    candidatos = (extract_bearer_or_cookie_token(request), _extract_refresh_token(request))
    for raw_tok in [tok for tok in dict.fromkeys(candidatos) if tok]:
        payload = decode_token_unverified_exp(raw_tok)
        if payload:
            await _revocar_payload_sesion(redis_conn, payload)


@router.post("/logout", response_model=LogoutResponse, status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    response: Response,
    redis_conn: aioredis.Redis = Depends(get_redis_client),
) -> LogoutResponse:
    """Revoca la sesión activa (sid/jti) en KeyDB y purga cookies de autenticación del cliente."""
    await _revocar_tokens_entrantes(request, redis_conn)
    _limpiar_cookies_sesion(response)
    return LogoutResponse(message="Sesión cerrada exitosamente")


def _validar_refresh_token_payload(raw_token: str | None) -> dict[str, Any]:
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token ausente")
    try:
        return decode_refresh_token(raw_token)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expirado") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido") from exc


async def _validar_usuario_no_revocado(redis_conn: aioredis.Redis, user: Usuario) -> None:
    user_id = getattr(user, "id", None)
    if user_id is not None and await is_user_session_revoked(redis_conn, int(user_id)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión revocada por la administración")


async def _verificar_usuario_sesion_vigente(
    db: AsyncSession,
    redis_conn: aioredis.Redis,
    correo: str,
    sid: str,
    not_found_status: int,
) -> Usuario:
    result = await db.execute(select(Usuario).where(Usuario.correo == correo))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=not_found_status, detail="Usuario no encontrado")
    await _validar_usuario_no_revocado(redis_conn, user)
    if sid and await is_session_id_revoked(redis_conn, sid):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión revocada")
    return user


async def _obtener_usuario_para_refresh(
    db: AsyncSession,
    redis_conn: aioredis.Redis,
    payload: dict[str, Any],
) -> Usuario:
    correo = payload.get("sub")
    if not correo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token sin usuario")
    condo_id = int(payload.get("condominio_id") or DEFAULT_CONDOMINIO_ID)
    await bind_rls_tenant(db, condo_id)
    user = await _verificar_usuario_sesion_vigente(
        db,
        redis_conn,
        str(correo),
        str(payload.get("sid") or ""),
        status.HTTP_401_UNAUTHORIZED,
    )
    await bind_rls_tenant(db, int(getattr(user, "condominio_id", condo_id) or condo_id))
    return user


async def _resolver_replay_refresh(
    response: Response,
    redis_conn: aioredis.Redis,
    user: Usuario,
    sid: str,
    jti: str,
) -> Any:
    cached = await get_refresh_token_from_grace_period(redis_conn, jti)
    if cached:
        rotated = json.loads(cached)
        _emitir_cookies_sesion(response, rotated["access"], rotated["refresh"], rotated["csrf"])
        return {"message": "Sesión renovada", "rol": user.rol, "csrf_token": rotated["csrf"]}

    user_id = getattr(user, "id", None)
    if user_id is not None:
        await revoke_user_session(redis_conn, int(user_id), ttl_seconds=REVOKED_USER_TTL_SECONDS)
    if sid:
        await revoke_session_id(redis_conn, sid, ttl_seconds=REVOKED_USER_TTL_SECONDS)
    err_resp = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Refresh token reutilizado o sesión revocada"},
    )
    _limpiar_cookies_sesion(err_resp)
    return err_resp


@router.post(
    "/refresh",
    response_model=AuthSessionResponse,
    responses={401: {"description": "Refresh token ausente, expirado, inválido o reutilizado"}},
)
async def refresh_session(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_conn: aioredis.Redis = Depends(get_redis_client),
) -> Any:
    """Rota el refresh token con ventana de cortesía de 5s para peticiones concurrentes."""
    payload = _validar_refresh_token_payload(_extract_refresh_token(request))
    user = await _obtener_usuario_para_refresh(db, redis_conn, payload)
    sid = str(payload.get("sid") or secrets.token_urlsafe(24))
    jti = str(payload.get("jti") or "")
    if not jti:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token sin JTI")

    if not await mark_refresh_jti_used(redis_conn, jti, ttl_seconds=REVOKED_USER_TTL_SECONDS):
        return await _resolver_replay_refresh(response, redis_conn, user, sid, jti)

    access_token, new_refresh_token, csrf_token = _crear_par_tokens(user, sid)
    grace_payload = json.dumps({"access": access_token, "refresh": new_refresh_token, "csrf": csrf_token})
    await rotate_refresh_token_with_grace_period(redis_conn, jti, grace_payload)
    _emitir_cookies_sesion(response, access_token, new_refresh_token, csrf_token)
    return AuthSessionResponse(message="Sesión renovada", rol=user.rol, csrf_token=csrf_token)


def _decodificar_access_token_me(token: str | None) -> dict[str, Any]:
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


@router.get(
    "/me",
    response_model=AuthMeResponse,
    responses={
        401: {"description": "No autenticado"},
        404: {"description": "Usuario no encontrado"},
    },
)
async def get_me(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_conn: aioredis.Redis = Depends(get_redis_client),
) -> AuthMeResponse:
    """Devuelve el perfil completo del usuario autenticado y rehidrata la cookie CSRF."""
    payload = _decodificar_access_token_me(extract_bearer_or_cookie_token(request))
    condo_id = int(payload.get("condominio_id") or DEFAULT_CONDOMINIO_ID)
    await bind_rls_tenant(db, condo_id)
    sid = str(payload.get("sid") or "")
    user = await _verificar_usuario_sesion_vigente(
        db,
        redis_conn,
        str(payload["sub"]),
        sid,
        status.HTTP_404_NOT_FOUND,
    )
    await bind_rls_tenant(db, int(getattr(user, "condominio_id", condo_id) or condo_id))

    csrf_token = generate_csrf_token(sid or str(user.correo))
    response.headers["X-CSRF-Token"] = csrf_token
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=should_use_secure_cookie(),
        samesite="lax",
        path="/",
    )
    unidad_activa_id = await _resolver_unidad_activa_id(db, user)
    return AuthMeResponse(
        id=user.id,
        nombre=user.nombre,
        cedula=str(getattr(user, "cedula", "")),
        correo=user.correo,
        telefono=str(getattr(user, "telefono", "")),
        es_activo=user.es_activo,
        rol=user.rol,
        unidad_activa_id=unidad_activa_id,
    )
