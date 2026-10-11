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
