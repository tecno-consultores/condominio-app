import pytest
from fastapi.testclient import TestClient
from src.main import app
import os

# Configuramos la variable de entorno para obligar a FastAPI a usar la base de datos en memoria (SQLite)
# Esto garantiza que las pruebas no alteren la base de datos de PostgreSQL real, cumpliendo la regla 11X
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="module")
def client():
    """Fixture que levanta el TestClient de FastAPI para simular llamadas HTTP aisladas"""
    with TestClient(app) as test_client:
        yield test_client