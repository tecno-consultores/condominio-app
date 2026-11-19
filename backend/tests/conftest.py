import os
from collections.abc import Generator

# Configuramos las variables de entorno ANTES de importar src.main para aislar SQLite en memoria y sin Redis compartido
# Esto garantiza que las pruebas unitarias y Mutmut en paralelo no lean ni alteren motores externos
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
if not os.getenv("POSTGRES_TEST_URL"):
    os.environ["REDIS_URL"] = "redis://127.0.0.1:1/15"

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture(autouse=True)
def _clear_app_dependency_overrides() -> Generator[None]:
    """Garantiza limpieza determinista de dependency_overrides después de cada prueba."""
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient]:
    """Fixture que levanta el TestClient de FastAPI para simular llamadas HTTP aisladas."""
    with TestClient(app) as test_client:
        yield test_client
