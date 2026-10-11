from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Condominio App API", version="1.0.0")

# Instrumentación de Nivel 11X (Métricas RED)
Instrumentator().instrument(app).expose(app)

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy"}