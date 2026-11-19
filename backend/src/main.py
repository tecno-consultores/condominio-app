import hmac
import logging
import os
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.database import Base, engine
from src.routers import accesos, administracion, auth, consultas, finanzas, incidencias, operaciones, pagos, reservas
from src.schemas import HealthResponse
from src.security import (
    decode_token_unverified_exp,
    is_csrf_enforced,
    is_trusted_proxy_ip,
    should_use_secure_cookie,
    validate_csrf_token,
    validate_production_security_settings,
)

logger = logging.getLogger(__name__)

_METODOS_OPENAPI = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
_CSRF_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_CSRF_PUBLIC_PREAUTH_PATHS = frozenset({"/api/auth/login", "/api/auth/register"})
_DOCS_PATHS = frozenset({"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"})
_DEFAULT_ALLOWED_HOSTS: frozenset[str] = frozenset(
    {"localhost", "127.0.0.1", "::1", "api", "condominio_backend_api", "testserver", "test"}
)
_API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'"
_DOCS_CSP = (
    "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'"
)
_PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
_FETCH_METADATA_VARY = ("Sec-Fetch-Dest", "Sec-Fetch-Mode", "Sec-Fetch-Site")
_INVALID_HOST_CHARS = frozenset({" ", "\r", "\n", "\x00", "/", "@", "\\"})


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


def _parse_valid_host_url(clean: str) -> str | None:
    try:
        parsed = urlparse(f"http://{clean}")
    except ValueError:
        return None
    has_extra = any((parsed.username, parsed.password, parsed.path, parsed.query))
    if has_extra or not parsed.hostname:
        return None
    return parsed.hostname.lower()


def _extract_host_from_header(raw_host: str) -> str | None:
    clean = raw_host.strip()
    if not clean or not _INVALID_HOST_CHARS.isdisjoint(clean):
        return None
    return _parse_valid_host_url(clean)


def _parse_allowed_hosts_env(raw_hosts: str) -> set[str]:
    parsed_hosts: set[str] = set()
    for item in raw_hosts.split(","):
        host = _extract_host_from_header(item)
        if host:
            parsed_hosts.add(host)
    return parsed_hosts


def _extract_origin_host(origin: str) -> str | None:
    clean_origin = origin.strip()
    if not clean_origin:
        return None
    hostname = urlparse(clean_origin).hostname
    return hostname.lower() if hostname else None


def _allowed_hosts_set() -> set[str]:
    raw_hosts = os.getenv("ALLOWED_HOSTS", "").strip()
    if raw_hosts:
        return _parse_allowed_hosts_env(raw_hosts)
    hosts = set(_DEFAULT_ALLOWED_HOSTS)
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(","):
        host = _extract_origin_host(origin)
        if host:
            hosts.add(host)
    return hosts


def _is_allowed_host(request: Request) -> bool:
    host = _extract_host_from_header(request.headers.get("host", ""))
    if not host:
        return False
    if request.url.path == "/health" and host in {"127.0.0.1", "localhost", "::1"}:
        return True
    return host in _allowed_hosts_set()


def _extract_metrics_token(request: Request) -> str:
    header_tok = request.headers.get("x-metrics-token", "").strip()
    if header_tok:
        return header_tok
    auth_header = request.headers.get("authorization", "").strip()
    if auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ").strip()
    return ""


def _extract_client_host(request: Request) -> str | None:
    return request.client.host if request.client else None


def _is_metrics_authorized(request: Request) -> bool:
    expected = os.getenv("METRICS_AUTH_TOKEN", "").strip()
    if expected:
        provided = _extract_metrics_token(request)
        return bool(provided) and hmac.compare_digest(provided, expected)
    if _es_produccion():
        return False
    return is_trusted_proxy_ip(_extract_client_host(request))


def _requires_cookie_csrf_check(request: Request) -> bool:
    if not is_csrf_enforced():
        return False
    if request.method.upper() not in _CSRF_MUTATING_METHODS:
        return False
    if request.url.path in _CSRF_PUBLIC_PREAUTH_PATHS:
        return False
    has_access_cookie = bool(request.cookies.get("access_token", "").strip())
    has_refresh_cookie = bool(request.cookies.get("refresh_token", "").strip())
    return has_access_cookie or has_refresh_cookie


def _session_id_from_payload(payload: dict[str, Any]) -> str | None:
    raw_sid = payload.get("sid") or payload.get("sub")
    if not raw_sid:
        return None
    return str(raw_sid).strip() or None


def _session_id_from_token(raw_cookie: str) -> str | None:
    token = raw_cookie.removeprefix("Bearer ").strip()
    if not token:
        return None
    payload = decode_token_unverified_exp(token)
    return _session_id_from_payload(payload) if payload else None


def _extract_cookie_session_id_for_csrf(request: Request) -> str | None:
    for cookie_name in ("access_token", "refresh_token"):
        session_id = _session_id_from_token(request.cookies.get(cookie_name, ""))
        if session_id:
            return session_id
    return None


def _is_valid_cookie_csrf(request: Request) -> bool:
    session_id = _extract_cookie_session_id_for_csrf(request)
    if session_id is None:
        return request.url.path == "/api/auth/logout"
    return validate_csrf_token(request.headers.get("x-csrf-token", ""), session_id)


@app.middleware("http")
async def csrf_protection_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Valida X-CSRF-Token HMAC-SHA256 siempre que existan cookies HttpOnly de sesión."""
    if _requires_cookie_csrf_check(request) and not _is_valid_cookie_csrf(request):
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


def _parse_vary_items(raw_vary: str) -> list[str]:
    return [item.strip() for item in raw_vary.split(",") if item.strip()]


def _merge_vary_header(response: Response) -> None:
    """Preserva Vary existente e incorpora cabeceras Fetch Metadata para caches intermedias."""
    existing_items = _parse_vary_items(response.headers.get("Vary", ""))
    existing_lower = {item.lower() for item in existing_items}
    missing = [h for h in _FETCH_METADATA_VARY if h.lower() not in existing_lower]
    response.headers["Vary"] = ", ".join(existing_items + missing)


def _is_https_request(request: Request) -> bool:
    if should_use_secure_cookie() or request.url.scheme == "https":
        return True
    if not is_trusted_proxy_ip(_extract_client_host(request)):
        return False
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
    return forwarded_proto == "https"


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
    if _is_https_request(request):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def _check_pre_route_guards(request: Request) -> JSONResponse | None:
    if not _is_allowed_host(request):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Encabezado Host inválido o no autorizado."},
        )
    if not _is_allowed_fetch_metadata(request):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Solicitud cross-site rechazada por política Fetch Metadata."},
        )
    if request.url.path == "/metrics" and not _is_metrics_authorized(request):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Acceso no autorizado al endpoint de métricas."},
        )
    return None


@app.middleware("http")
async def security_headers_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Valida Host/Fetch Metadata/métricas, captura 500 e inyecta cabeceras OSHP en toda respuesta."""
    guard_response = _check_pre_route_guards(request)
    if guard_response is not None:
        return _apply_security_headers(request, guard_response)
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Error interno no controlado en %s %s", request.method, request.url.path)
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Error interno del servidor."},
        )
    return _apply_security_headers(request, response)


# Instrumentación de Nivel 11X (Métricas RED). Excluido del contrato OpenAPI: su
# Content-Type es text/plain, no application/json.
Instrumentator().instrument(app).expose(app, include_in_schema=False)


def _extraer_metodos_ops(ops_ruta: dict[str, Any]) -> set[str]:
    return {metodo.upper() for metodo in ops_ruta if metodo.lower() in _METODOS_OPENAPI}


def _metodos_permitidos(path: str) -> set[str]:
    """Métodos HTTP documentados para un path, priorizando coincidencia exacta antes que plantillas."""
    paths = app.openapi().get("paths", {})
    if path in paths:
        return _extraer_metodos_ops(paths[path])
    permitidos: set[str] = set()
    for plantilla, ops_ruta in paths.items():
        patron = re.sub(r"\{[^}]+\}", r"[^/]+", plantilla)
        if re.fullmatch(patron, path):
            permitidos.update(_extraer_metodos_ops(ops_ruta))
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


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    return HealthResponse(status="healthy")
