# Guía de Pruebas y Validación para Backend (FastAPI) - Condominio App

Este documento detalla la estrategia completa de pruebas automatizadas, calidad de código y resiliencia para el **Backend en FastAPI** de Condominio App bajo el estándar corporativo **Nivel 11X**.

---

## 1. Reglas de Ejecución Efímera en Docker

Toda validación de Backend se ejecuta dentro de contenedores efímeros usando imágenes base oficiales alojadas en Docker Hub, sin instalar paquetes en la máquina anfitriona y reutilizando el volumen de caché de `uv`:

* **Imagen Base Python/API/Tests:** `sinfallas/base-python-uv:3.13` (o tag compatible).
* **Pruebas BDD de Caja Negra:** `sinfallas/karatelabs:latest`.
* **Seguridad Dinámica (DAST):** `zaproxy/zap-stable:latest`.
* **Ingeniería del Caos:** `gaiaadm/pumba:latest`.
* **Observabilidad RED:** `prom/prometheus:latest`.
* **Servidor MCP de Contexto IA:** `sinfallas/remote-graphify:latest`.

---

## 2. Pila Tecnológica de QA (11 Capas Transversales)

1. **Calidad y Formateo:** `ruff` (linter y formateador ultrarrápido).
2. **Tipado Estático:** `mypy` con `strict = true`.
3. **Pruebas Unitarias y Mocking:** `pytest`, `pytest-asyncio`, `pytest-mock`, `httpx` / `TestClient`.
4. **Piso de Cobertura:** `pytest-cov` con fallo obligatorio si `--cov-fail-under=95`.
5. **Seguridad Estática (SAST):** `bandit` (detección de patrones vulnerables) y `uv pip audit` (escaneo de CVEs en dependencias).
6. **Seguridad Dinámica (DAST):** `OWASP ZAP` (escaneo *Baseline* interceptando cabeceras y configuraciones).
7. **Deuda Técnica y Complejidad:** `radon` (auditoría de complejidad ciclomática e índice de mantenibilidad).
8. **Profiling:** `py-spy` (análisis de CPU y detección de bloqueos en el Event Loop asíncrono con Flamegraphs).
9. **Pruebas de Mutación:** `mutmut` (mutación de lógica para eliminar falsos positivos).
10. **Contratos y Fuzzing:** `schemathesis` (bombardeo de combinaciones inválidas contra `openapi.json`).
11. **Comportamiento BDD:** `Karate Labs` (ejecución de escenarios funcionales Gherkin como caja negra opaca).
12. **Resiliencia y Caos:** `Pumba` (inyección de latencia y jitter en kernel) + `Locust` (oleadas de estrés concurrente) + `Prometheus` (monitoreo de métricas RED).

---

## 3. Requisito de Observabilidad en Código (`src/main.py`)

Para permitir que Prometheus y las pruebas de caos recopilen telemetría sin interferir con la lógica de negocio, `src/main.py` debe incluir:

```python
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Condominio App API", version="1.0.0")

# Instrumentación Nivel 11X (Expone automáticamente /metrics)
Instrumentator().instrument(app).expose(app)
```

---

## 4. Archivo de Configuración del Proyecto: `pyproject.toml`

A continuación se muestra la plantilla de referencia no destructiva para configurar dependencias de producción, herramientas de QA y parámetros de linters:

```toml
[project]
name = "condominio-app-backend"
version = "1.0.0"
description = "API para administración y control financiero de condominios"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "sqlalchemy>=2.0.0",
    "aiosqlite>=0.20.0",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "pydantic[email]>=2.6.0",
    "python-dotenv>=1.0.0",
    "pyjwt>=2.8.0",
    "passlib[bcrypt]>=1.7.4",
    "httpx>=0.27.0",
    "redis>=5.0.0"
]

[project.optional-dependencies]
dev = [
    # Core Testing & Mocking
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.5",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.14.0",
    
    # Linting & Tipado
    "ruff>=0.3.0",
    "mypy>=1.9.0",
    
    # Seguridad y Mutación
    "bandit>=1.7.8",
    "mutmut>=2.4.5",
    
    # Complejidad y Profiling
    "radon>=6.0.1",
    "py-spy>=0.3.14",
    
    # Contratos y Estrés
    "schemathesis>=3.25.0",
    "locust>=2.24.0",
    
    # Observabilidad
    "prometheus-fastapi-instrumentator>=7.0.0",
    "prometheus-client>=0.20.0"
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
# Tool Boundary: Solo archivos con sufijo .unit.py o .spec.py
python_files = ["test_*.unit.py", "test_*.spec.py"]
addopts = "--strict-markers --cov=src/ --cov-report=html --cov-report=term-missing --cov-fail-under=95"

[tool.ruff]
line-length = 120
target-version = "py313"

[tool.mypy]
strict = true
ignore_missing_imports = true

[tool.mutmut]
source_paths = ["src/"]
backup = false
runner = "uv run pytest -x tests/"
```

---

## 5. Orquestador Docker Efímero: `docker-compose.qa.yml`

Este archivo reside en la carpeta `backend/` para orquestar la suite completa:

```yaml
services:
  api:
    image: sinfallas/base-python-uv:3.13
    container_name: condominio_backend_api
    hostname: condominio_backend_api
    pull_policy: always
    environment:
      TZ: 'America/Caracas'
      UV_CACHE_DIR: /root/.cache/uv
      DATABASE_URL: 'sqlite+aiosqlite:///:memory:'
    volumes:
      - .:/app
      - uv-cache:/root/.cache/uv
    working_dir: /app
    ports:
      - "8000:8000"
    cap_add:
      - SYS_PTRACE
    security_opt:
      - seccomp:unconfined
    command: bash -c "uv pip install --system -e '.[dev]' && uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload"

  qa-backend:
    image: sinfallas/base-python-uv:3.13
    container_name: condominio_qa_backend
    hostname: condominio_qa_backend
    pull_policy: always
    environment:
      TZ: 'America/Caracas'
      UV_PYTHON_DOWNLOADS: 'true'
      UV_CACHE_DIR: /root/.cache/uv
      DATABASE_URL: 'sqlite+aiosqlite:///:memory:'
    volumes:
      - .:/app
      - uv-cache:/root/.cache/uv
    working_dir: /app
    cap_add:
      - SYS_PTRACE
    command: bash -c "echo 'Contenedor QA Backend listo para Lint, Pytest y Mutmut'; sleep infinity"

  karatelabs:
    image: sinfallas/karatelabs:latest
    container_name: condominio_backend_karate
    hostname: condominio_backend_karate
    pull_policy: always
    depends_on:
      - api
    volumes:
      - ./test:/app/src/test/java/examples/test
    command: bash -c "echo 'Contenedor Karate listo'; sleep infinity"

  zap:
    image: zaproxy/zap-stable:latest
    container_name: condominio_backend_zap
    hostname: condominio_backend_zap
    pull_policy: always
    depends_on:
      - api
    user: root
    volumes:
      - .:/zap/wrk/:rw
    command: bash -c "echo 'Contenedor ZAP listo'; sleep infinity"

  pumba:
    image: gaiaadm/pumba:latest
    container_name: condominio_backend_pumba
    hostname: condominio_backend_pumba
    profiles:
      - chaos
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on:
      - api
    command: netem --tc-image gaiadocker/iproute2 --duration 1m delay --time 500 --jitter 50 re2:^condominio_backend_api$

  prometheus:
    image: prom/prometheus:latest
    container_name: condominio_backend_prometheus
    hostname: condominio_backend_prometheus
    profiles:
      - chaos
    entrypoint:
      - /bin/sh
      - -c
      - |
        echo "
        global:
          scrape_interval: 2s
        scrape_configs:
          - job_name: 'fastapi_qa'
            metrics_path: '/metrics'
            static_configs:
              - targets: ['api:8000']
        " > /tmp/prometheus.yml
        /bin/prometheus --config.file=/tmp/prometheus.yml
    ports:
      - "9090:9090"
    depends_on:
      - api

  stress_test:
    image: sinfallas/base-python-uv:3.13
    container_name: condominio_backend_chaos_locust
    hostname: condominio_backend_chaos_locust
    profiles:
      - chaos
    depends_on:
      - api
    environment:
      UV_CACHE_DIR: /root/.cache/uv
    volumes:
      - .:/app
      - uv-cache:/root/.cache/uv
    working_dir: /app
    command: bash -c "uv pip install --system -e '.[dev]' && echo 'Esperando API...' && sleep 5 && locust -f tests/locustfile.py --headless -u 100 -r 10 -t 1m --host http://api:8000 --html chaos-report.html"

volumes:
  uv-cache:
    name: condominio_backend_uv_cache
```

---

## 6. Comandos Operativos: `Makefile`

El archivo `backend/Makefile` encapsula la ejecución de todas las metas de validación:

```makefile
.PHONY: qa-lint qa-unit qa-mutation qa-complexity qa-contracts qa-dast qa-chaos qa-all clean-cache

COMPOSE_FILE = docker-compose.qa.yml
SERVICE_NAME = qa-backend

qa-lint:
	@echo "🔍 Ejecutando Ruff, Mypy y Bandit (SAST)..."
	docker compose -f $(COMPOSE_FILE) run --rm $(SERVICE_NAME) bash -c "uv sync && uv run ruff check . && uv run mypy . && uv run bandit -r src/"

qa-complexity:
	@echo "📊 Verificando Complejidad Ciclomática (Radon)..."
	docker compose -f $(COMPOSE_FILE) run --rm $(SERVICE_NAME) bash -c "uv sync && uv run radon cc src/ -s -nb && uv run radon mi src/ -s"

qa-unit:
	@echo "🧪 Ejecutando Pruebas Unitarias Aisladas (Pytest con cobertura >=95%)..."
	docker compose -f $(COMPOSE_FILE) run --rm $(SERVICE_NAME) bash -c "uv sync && uv run pytest --cov=src --cov-fail-under=95"

qa-mutation:
	@echo "👽 Ejecutando Pruebas de Mutación (Mutmut)..."
	docker compose -f $(COMPOSE_FILE) run --rm $(SERVICE_NAME) bash -c "uv sync && uv run mutmut run"

qa-contracts:
	@echo "📑 Fuzzing y Verificación de Contratos OpenAPI (Schemathesis)..."
	docker compose -f $(COMPOSE_FILE) up -d api
	docker compose -f $(COMPOSE_FILE) run --rm $(SERVICE_NAME) bash -c "uv sync && uv run schemathesis run http://api:8000/openapi.json"

qa-dast:
	@echo "🛡️ Escaneo Dinámico de Seguridad (OWASP ZAP)..."
	docker compose -f $(COMPOSE_FILE) up -d api
	docker compose -f $(COMPOSE_FILE) run --rm zap zap-baseline.py -t http://api:8000 -r zap-report.html

qa-chaos:
	@echo "🌪️ Certificación de Resiliencia y Caos (Pumba + Locust + Prometheus)..."
	docker compose -f $(COMPOSE_FILE) --profile chaos up --abort-on-container-exit stress_test

qa-all: qa-lint qa-complexity qa-unit qa-mutation
	@echo "✅ Pipeline QA Backend completado exitosamente."

clean-cache:
	@echo "🧹 Limpiando volúmenes de caché de uv y contenedores..."
	docker compose -f $(COMPOSE_FILE) down -v
	docker compose -f $(COMPOSE_FILE) --profile chaos down -v
```

---

## 7. Ejemplos de Implementación de Pruebas

### A. Prueba Unitaria con Mocking Estricto (`tests/test_auth.unit.py`)
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.main import app
from src.database import get_db

def test_registro_usuario_exitoso(client):
    """Verifica el registro sin tocar base de datos real mediante mocks"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = None  # No hay usuario previo
    mock_session.execute.return_value = mock_result
    
    async def mock_flush(): pass
    mock_session.flush = mock_flush

    app.dependency_overrides[get_db] = lambda: mock_session

    payload = {
        "nombre": "Carlos Perez",
        "cedula": "V-18765432",
        "correo": "carlos@example.com",
        "telefono": "+584141234567",
        "password": "PasswordSeguro123!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO"
    }
    headers = {"Idempotency-Key": "e3c88688-66a9-4673-987d-8703c3d0b284"}

    response = client.post("/api/auth/register", json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["es_activo"] is False
    assert response.json()["rol"] == "FANTASMA"

    app.dependency_overrides = {}
```

### B. Escenario BDD de Comportamiento (`test/api_test.feature`)
```gherkin
Feature: Flujos Críticos de la API de Condominio

  Background:
    * url 'http://api:8000'
    * configure headers = { 'Content-Type': 'application/json' }

  Scenario: Healthcheck responde con status healthy
    Given path '/health'
    When method get
    Then status 200
    And match response == { status: 'healthy' }

  Scenario: Petición sin Idempotency-Key en registro debe ser rechazada con 422
    Given path '/api/auth/register'
    And request { nombre: "Sin Clave", correo: "test@test.com" }
    When method post
    Then status 422
```

### C. Ataque de Caos y Estrés con Locust (`tests/locustfile.py`)
```python
from locust import HttpUser, task, between

class CondominioStressUser(HttpUser):
    wait_time = between(1, 2)

    @task(3)
    def check_health(self):
        self.client.get("/health")

    @task(2)
    def check_unauthenticated_me(self):
        with self.client.get("/api/auth/me", catch_response=True) as response:
            if response.status_code == 401:
                response.success()  # 401 es la respuesta esperada sin token

    @task(1)
    def invalid_login(self):
        payload = {"correo": "inexistente@correo.com", "password": "wrong"}
        self.client.post("/api/auth/login", json=payload)
```
