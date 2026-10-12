import re
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.database import Base, engine
from src.routers import auth, finanzas, pagos

_METODOS_OPENAPI = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Garantiza el esquema en entornos efímeros (SQLite) al arrancar el servicio."""
    if engine.dialect.name == "sqlite":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Condominio App API", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def no_store_cache(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """Previene el almacenamiento en caché de respuestas con datos (mejora de DAST [10049])."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response

# Instrumentación de Nivel 11X (Métricas RED). Excluido del contrato OpenAPI: su
# Content-Type es text/plain, no application/json.
Instrumentator().instrument(app).expose(app, include_in_schema=False)


def _metodos_permitidos(path: str) -> set[str]:
    """Métodos HTTP documentados para un path, resolviendo también plantillas con parámetros."""
    permitidos: set[str] = set()
    for plantilla, operaciones in app.openapi().get("paths", {}).items():
        patron = re.sub(r"\{[^}]+\}", r"[^/]+", plantilla)
        if re.fullmatch(patron, path):
            permitidos.update(metodo.upper() for metodo in operaciones if metodo.lower() in _METODOS_OPENAPI)
    return permitidos


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

@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}
