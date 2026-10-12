.PHONY: qa-lint qa-unit qa-mutation qa-complexity qa-deps qa-contracts qa-dast qa-chaos qa-infra qa-profile qa-all clean-cache

COMPOSE_FILE = docker-compose.qa.yml
SERVICE_NAME = qa-backend
# Detección automática de la ruta host para Docker-in-Docker / bind mounts
HOST_WORKSPACE ?= $(shell docker inspect $$(hostname) 2>/dev/null | grep -B1 '"Destination": "/workspace"' | grep '"Source"' | sed -E 's/.*"Source": "([^"]+)".*/\1/')
ifeq ($(HOST_WORKSPACE),)
  HOST_PWD ?= $(PWD)
else
  HOST_PWD ?= $(HOST_WORKSPACE)/condominio-app/backend
endif
export HOST_PWD

qa-lint:
	@echo "🔍 Ejecutando Ruff, Mypy y Bandit (SAST)..."
	docker compose -f $(COMPOSE_FILE) run --rm $(SERVICE_NAME) bash -c "uv sync && uv run ruff check . --fix && uv run mypy . && uv run bandit -r src/"

qa-complexity:
	@echo "📊 Verificando Complejidad Ciclomática (Radon) con gates Nivel 11X..."
	docker compose -f $(COMPOSE_FILE) run --rm $(SERVICE_NAME) bash -c "uv sync && uv run radon cc src/ -s -nb && uv run radon mi src/ -s && uv run python scripts/radon_gates.py"

qa-deps:
	@echo "🔐 Auditoría de vulnerabilidades en dependencias (uv audit)..."
	docker compose -f $(COMPOSE_FILE) run --rm $(SERVICE_NAME) bash -c "uv sync && uv audit"

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
	@set +e; docker compose -f $(COMPOSE_FILE) run --rm zap zap-baseline.py -t http://api:8000 -r zap-report.html; \
	status=$$?; set -e; \
	if [ $$status -eq 0 ] || [ $$status -eq 2 ]; then \
		echo "✅ DAST finalizado sin fallos (FAIL-NEW=0; código $$status)."; \
	else \
		exit $$status; \
	fi

qa-chaos:
	@echo "🌪️ Certificación de Resiliencia y Caos (Pumba + Locust + Prometheus)..."
	docker compose -f $(COMPOSE_FILE) --profile chaos up --abort-on-container-exit stress_test

qa-all: qa-lint qa-complexity qa-unit qa-mutation
	@echo "✅ Pipeline QA Backend completado exitosamente."

qa-infra:
	@echo "🛰️ Auditoría de Infraestructura como Código (Trivy IaC + FS) sobre el repositorio..."
	docker run --rm -v "${HOST_PWD}/..:/app:ro" -w /app aquasec/trivy:latest config . --severity HIGH,CRITICAL --exit-code 1 --skip-dirs backend/.venv
	docker run --rm -v "${HOST_PWD}/..:/app:ro" -w /app aquasec/trivy:latest fs . --severity CRITICAL --exit-code 1 --skip-dirs backend/.venv

qa-profile:
	@echo "📈 Perfilando la API con py-spy bajo carga de Locust (guardando profile.svg)..."
	docker compose -f $(COMPOSE_FILE) up -d api
	docker compose -f $(COMPOSE_FILE) run -d --name condominio_backend_profiler $(SERVICE_NAME) bash -c "uv sync -q && uv run locust -f tests/locustfile.py --headless -u 30 -r 5 -t 30s --host http://api:8000"
	@sleep 6; \
	worker=$$(docker exec condominio_backend_api python /app/scripts/find_worker.py); \
	echo "📊 Muestreando reloader/workers (PID $$worker)..."; \
	docker exec condominio_backend_api py-spy record -s --pid $$worker --duration 18 -o /app/profile.svg; \
	echo "🧹 Deteniendo generador de carga..."; \
	docker rm -f condominio_backend_profiler
	@echo "✅ Perfil de CPU guardado en profile.svg"

clean-cache:
	@echo "🧹 Limpiando volúmenes de caché de uv y contenedores..."
	docker compose -f $(COMPOSE_FILE) down -v
	docker compose -f $(COMPOSE_FILE) --profile chaos down -v
	docker compose -f $(COMPOSE_FILE) --profile graphify down -v
