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
from src.routers import administracion, auth, consultas, finanzas, incidencias, operaciones, pagos

logger = logging.getLogger(__name__)

_METODOS_OPENAPI = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def _es_produccion() -> bool:
    """Determina si la aplicación corre en modo producción (Patrones 3 y 12)."""
    return os.getenv("APP_ENV", "development").lower() == "production"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Garantiza el esquema en entornos efímeros (SQLite) al arrancar el servicio."""
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


@app.middleware("http")
async def security_headers_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Inyecta cabeceras HTTP defensivas y evita almacenamiento en caché de datos sensibles."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


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


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}
