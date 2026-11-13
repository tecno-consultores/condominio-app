import logging
import os
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.database import Base, engine
from src.routers import accesos, administracion, auth, consultas, finanzas, incidencias, operaciones, pagos, reservas
from src.security import (
    decode_token_unverified_exp,
    is_csrf_enforced,
    should_use_secure_cookie,
    validate_csrf_token,
    validate_production_security_settings,
)

logger = logging.getLogger(__name__)

_METODOS_OPENAPI = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
_CSRF_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_CSRF_PUBLIC_PREAUTH_PATHS = frozenset({"/api/auth/login", "/api/auth/register"})
_DOCS_PATHS = frozenset({"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"})
_API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'"
_DOCS_CSP = (
    "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "frame-ancestors 'none'; base-uri 'none'; object-src 'none'"
)
_PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
_FETCH_METADATA_VARY = ("Sec-Fetch-Dest", "Sec-Fetch-Mode", "Sec-Fetch-Site")


def _es_produccion() -> bool:
    """Determina si la aplicación corre en modo producción (Patrones 3 y 12)."""
    return os.getenv("APP_ENV", "development").lower() == "production"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Valida secretos de producción y garantiza el esquema SQLite en entornos efímeros."""
    validate_production_security_settings()
    if engine.dialect.name == "sqlite":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield


_IS_PROD = _es_produccion()

app = FastAPI(
    title="Condominio App API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if _IS_PROD else "/docs",
    redoc_url=None if _IS_PROD else "/redoc",
    openapi_url=None if _IS_PROD else "/openapi.json",
)


def _requires_cookie_csrf_check(request: Request) -> bool:
    if not is_csrf_enforced():
        return False
    if request.method.upper() not in _CSRF_MUTATING_METHODS:
        return False
    if request.url.path in _CSRF_PUBLIC_PREAUTH_PATHS:
        return False
    return not request.headers.get("authorization", "").startswith("Bearer ")


def _extract_cookie_session_id_for_csrf(request: Request) -> str | None:
    raw_access = request.cookies.get("access_token", "")
    token = raw_access.removeprefix("Bearer ").strip()
    if not token:
        token = request.cookies.get("refresh_token", "").removeprefix("Bearer ").strip()
    if not token:
        return None
    payload = decode_token_unverified_exp(token)
    if not payload:
        return None
    session_id = str(payload.get("sid") or payload.get("sub") or "").strip()
    return session_id or None


@app.middleware("http")
async def csrf_protection_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Valida X-CSRF-Token HMAC-SHA256 en mutaciones autenticadas por cookie HttpOnly."""
    if _requires_cookie_csrf_check(request):
        session_id = _extract_cookie_session_id_for_csrf(request)
        if session_id and not validate_csrf_token(request.headers.get("x-csrf-token", ""), session_id):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Token CSRF inválido o ausente."},
            )
    return await call_next(request)


def _is_allowed_fetch_metadata(request: Request) -> bool:
    """Aplica aislamiento de recursos Fetch Metadata antes de ejecutar autenticación o rutas."""
    sec_fetch_site = request.headers.get("sec-fetch-site", "").strip().lower()
    if sec_fetch_site in {"", "same-origin", "same-site", "none"}:
        return True
    sec_fetch_mode = request.headers.get("sec-fetch-mode", "").strip().lower()
    sec_fetch_dest = request.headers.get("sec-fetch-dest", "").strip().lower()
    if sec_fetch_mode != "navigate":
        return False
    return request.method in {"GET", "HEAD"} and sec_fetch_dest not in {"object", "embed"}


def _merge_vary_header(response: Response) -> None:
    """Preserva Vary existente e incorpora cabeceras Fetch Metadata para caches intermedias."""
    existing_raw = response.headers.get("Vary", "")
    existing_items = [item.strip() for item in existing_raw.split(",") if item.strip()]
    existing_lower = {item.lower() for item in existing_items}
    for header_name in _FETCH_METADATA_VARY:
        if header_name.lower() not in existing_lower:
            existing_items.append(header_name)
            existing_lower.add(header_name.lower())
    response.headers["Vary"] = ", ".join(existing_items)


def _apply_security_headers(request: Request, response: Response) -> Response:
    """Inyecta cabeceras HTTP defensivas, CSP, aislamiento COOP/CORP y HSTS condicional."""
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = _DOCS_CSP if request.url.path in _DOCS_PATHS else _API_CSP
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = _PERMISSIONS_POLICY
    _merge_vary_header(response)
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
    if should_use_secure_cookie() or request.url.scheme == "https" or forwarded_proto == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.middleware("http")
async def security_headers_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Aplica Fetch Metadata pre-auth e inyecta cabeceras HTTP defensivas en toda respuesta."""
    if not _is_allowed_fetch_metadata(request):
        blocked = JSONResponse(
            status_code=403,
            content={"detail": "Solicitud cross-site rechazada por política Fetch Metadata."},
        )
        return _apply_security_headers(request, blocked)
    response = await call_next(request)
    return _apply_security_headers(request, response)


# Instrumentación de Nivel 11X (Métricas RED). Excluido del contrato OpenAPI: su
# Content-Type es text/plain, no application/json.
Instrumentator().instrument(app).expose(app, include_in_schema=False)


def _metodos_permitidos(path: str) -> set[str]:
    """Métodos HTTP documentados para un path, resolviendo también plantillas con parámetros."""
    permitidos: set[str] = set()
    for plantilla, ops_ruta in app.openapi().get("paths", {}).items():
        patron = re.sub(r"\{[^}]+\}", r"[^/]+", plantilla)
        if re.fullmatch(patron, path):
            permitidos.update(metodo.upper() for metodo in ops_ruta if metodo.lower() in _METODOS_OPENAPI)
    return permitidos


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Sanitiza errores de validación 422 en producción para evitar fuga de esquemas (Patrón 3)."""
    if _es_produccion():
        logger.warning("Fallo de validación 422 en %s %s: %s", request.method, request.url.path, exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": "Los datos proporcionados no cumplen con los requisitos de validación."},
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": jsonable_encoder(exc.errors())},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Reconstruye el header Allow en respuestas 405 para declarar todos los métodos del path."""
    headers = dict(exc.headers or {})
    if exc.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        permitidos = _metodos_permitidos(request.url.path)
        if permitidos:
            headers["Allow"] = ", ".join(sorted(permitidos))
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=headers)


# Registro de Routers
app.include_router(auth.router)
app.include_router(pagos.router)
app.include_router(finanzas.router)
app.include_router(administracion.router)
app.include_router(incidencias.router)
app.include_router(operaciones.router)
app.include_router(consultas.router)
app.include_router(accesos.router)
app.include_router(reservas.router)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}
