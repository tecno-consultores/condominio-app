from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from src.routers import auth

app = FastAPI(title="Condominio App API", version="1.0.0")

# Instrumentación de Nivel 11X (Métricas RED)
Instrumentator().instrument(app).expose(app)

# Registro de Routers
app.include_router(auth.router)

@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}
