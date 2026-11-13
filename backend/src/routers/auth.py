import json
import secrets
from typing import Any

import jwt
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import get_db
from src.dependencies import extract_bearer_or_cookie_token
from src.models import ContratoOcupacion, Usuario
from src.redis_client import (
    check_and_set_idempotency_key,
    clear_login_failures,
    clear_user_session_revocation,
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
from src.schemas import UsuarioCreate, UsuarioResponse
from src.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    decode_token_unverified_exp,
    generate_csrf_token,
    get_password_hash,
    should_use_secure_cookie,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


class LoginData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correo: str
    password: str


def _extract_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else "unknown"


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
    claims: dict[str, Any] = {"sub": user.correo, "rol": user.rol, "id": user.id, "sid": sid}
    access_token = create_access_token(data=claims)
    refresh_token = create_refresh_token(data={"sub": user.correo, "id": user.id, "sid": sid})
    csrf_token = generate_csrf_token(sid)
    return access_token, refresh_token, csrf_token


async def _resolver_unidad_activa_id(db: AsyncSession, user: Any) -> int | None:
    if not isinstance(user, Usuario):
        raw_fake = getattr(user, "unidad_activa_id", None)
        return raw_fake if isinstance(raw_fake, int) and not isinstance(raw_fake, bool) else None
    stmt = (
        select(ContratoOcupacion.unidad_id)
        .where(ContratoOcupacion.usuario_id == user.id, ContratoOcupacion.es_activo.is_(True))
        .order_by(ContratoOcupacion.id.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    raw_uid = res.scalars().first()
    return raw_uid if isinstance(raw_uid, int) and not isinstance(raw_uid, bool) else None


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
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    db: AsyncSession = Depends(get_db),
    redis_conn: aioredis.Redis = Depends(get_redis_client),
) -> Any:
    try:
        is_unique = await check_and_set_idempotency_key(redis_conn, idempotency_key, scope="register")
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
        429: {"description": "Demasiados intentos fallidos (Lockout temporal 15 minutos)"},
    },
)
async def login(
    request: Request,
    response: Response,
    login_data: LoginData,
    db: AsyncSession = Depends(get_db),
    redis_conn: aioredis.Redis = Depends(get_redis_client),
) -> dict[str, str]:
    """Autentica credenciales PBKDF2 en tiempo constante, aplica lockout 5/15m y emite cookies + CSRF."""
    client_ip = _extract_client_ip(request)
    if await is_login_locked_out(redis_conn, client_ip, login_data.correo):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos fallidos de inicio de sesión. Intente nuevamente en 15 minutos.",
        )

    result = await db.execute(select(Usuario).where(Usuario.correo == login_data.correo))
    user = result.scalars().first()

    password_ok = verify_password(
        login_data.password,
        user.password_hash if user is not None else DUMMY_PASSWORD_HASH,
    )
    if user is None or not password_ok:
        await record_login_failure(redis_conn, client_ip, login_data.correo)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    await clear_login_failures(redis_conn, client_ip, login_data.correo)
    user_id = getattr(user, "id", None)
    if user_id is not None:
        await clear_user_session_revocation(redis_conn, int(user_id))

    sid = secrets.token_urlsafe(24)
    access_token, refresh_token, csrf_token = _crear_par_tokens(user, sid)
    _emitir_cookies_sesion(response, access_token, refresh_token, csrf_token)
    return {"message": "Login exitoso", "rol": user.rol, "csrf_token": csrf_token}


async def _revocar_payload_sesion(redis_conn: aioredis.Redis, payload: dict[str, Any]) -> None:
    uid = payload.get("id")
    if uid is not None:
        await revoke_user_session(redis_conn, int(uid))
    sid = str(payload.get("sid") or "")
    if sid:
        await revoke_session_id(redis_conn, sid)
    jti = str(payload.get("jti") or "")
    if payload.get("typ") == "refresh" and jti:
        await mark_refresh_jti_used(redis_conn, jti)


async def _revocar_tokens_entrantes(request: Request, redis_conn: aioredis.Redis) -> None:
    candidatos = (extract_bearer_or_cookie_token(request), _extract_refresh_token(request))
    for raw_tok in [tok for tok in dict.fromkeys(candidatos) if tok]:
        payload = decode_token_unverified_exp(raw_tok)
        if payload:
            await _revocar_payload_sesion(redis_conn, payload)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    response: Response,
    redis_conn: aioredis.Redis = Depends(get_redis_client),
) -> dict[str, str]:
    """Revoca la sesión activa en KeyDB y purga cookies de autenticación del cliente."""
    await _revocar_tokens_entrantes(request, redis_conn)
    _limpiar_cookies_sesion(response)
    return {"message": "Sesión cerrada exitosamente"}


def _validar_refresh_token_payload(raw_token: str | None) -> dict[str, Any]:
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token ausente")
    try:
        return decode_refresh_token(raw_token)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expirado") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido") from exc


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
    user_id = getattr(user, "id", None)
    if user_id is not None and await is_user_session_revoked(redis_conn, int(user_id)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión revocada por la administración")
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
    return await _verificar_usuario_sesion_vigente(
        db,
        redis_conn,
        str(correo),
        str(payload.get("sid") or ""),
        status.HTTP_401_UNAUTHORIZED,
    )


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
        await revoke_user_session(redis_conn, int(user_id))
    if sid:
        await revoke_session_id(redis_conn, sid)
    err_resp = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Refresh token reutilizado o sesión revocada"},
    )
    _limpiar_cookies_sesion(err_resp)
    return err_resp


@router.post(
    "/refresh",
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

    if not await mark_refresh_jti_used(redis_conn, jti):
        return await _resolver_replay_refresh(response, redis_conn, user, sid, jti)

    access_token, new_refresh_token, csrf_token = _crear_par_tokens(user, sid)
    grace_payload = json.dumps({"access": access_token, "refresh": new_refresh_token, "csrf": csrf_token})
    await rotate_refresh_token_with_grace_period(redis_conn, jti, grace_payload)
    _emitir_cookies_sesion(response, access_token, new_refresh_token, csrf_token)
    return {"message": "Sesión renovada", "rol": user.rol, "csrf_token": csrf_token}


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
) -> dict[str, Any]:
    """Devuelve el perfil completo del usuario autenticado y rehidrata la cookie CSRF."""
    payload = _decodificar_access_token_me(extract_bearer_or_cookie_token(request))
    sid = str(payload.get("sid") or "")
    user = await _verificar_usuario_sesion_vigente(
        db,
        redis_conn,
        str(payload["sub"]),
        sid,
        status.HTTP_404_NOT_FOUND,
    )

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
    return {
        "id": user.id,
        "nombre": user.nombre,
        "cedula": str(getattr(user, "cedula", "")),
        "correo": user.correo,
        "telefono": str(getattr(user, "telefono", "")),
        "es_activo": user.es_activo,
        "rol": user.rol,
        "unidad_activa_id": unidad_activa_id,
    }
