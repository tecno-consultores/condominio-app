.PHONY: qa-lint qa-unit qa-orphans qa-mutation qa-perf qa-lighthouse qa-e2e qa-a11y qa-bdd qa-ui-bdd qa-all build-ui clean-cache

# ==============================================================================
# MAKEFILE QA VUE 3 — CONDOMINIO APP (ESTÁNDAR CORPORATIVO 11X)
# ==============================================================================

COMPOSE_FILE = docker-compose.qa.yml
SERVICE_NAME = qa-vue3
E2E_SERVICE = ui-e2e
HOST_WORKSPACE ?= $(shell docker inspect $$(hostname) 2>/dev/null | grep -B1 '"Destination": "/workspace"' | grep '"Source"' | sed -E 's/.*"Source": "([^"]+)".*/\1/')
ifeq ($(HOST_WORKSPACE),)
  HOST_PWD ?= $(CURDIR)
else
  HOST_PWD ?= $(HOST_WORKSPACE)/condominio-app/frontend
endif
export HOST_PWD

NODE_USER_FLAGS = -u "$$(id -u):$$(id -g)" -e HOME=/tmp
PNPM_STORE_SETUP = if [ -w /pnpm ]; then export pnpm_config_store_dir=/pnpm; else export pnpm_config_store_dir=/tmp/pnpm-store; fi

build-ui:
	@echo "🏗️ Compilando aplicación Vue 3 / Vite para entorno E2E/Producción..."
	docker compose -f $(COMPOSE_FILE) run --rm $(NODE_USER_FLAGS) $(SERVICE_NAME) bash -c "$(PNPM_STORE_SETUP) && pnpm install && pnpm run build"
	docker compose -f $(COMPOSE_FILE) up -d --force-recreate ui-prod chrome-cdp

qa-lint:
	@echo "🔍 [11X] Ejecutando Auditoría de CVEs, Type-Check, Prettier y ESLint (SonarJS)..."
	docker compose -f $(COMPOSE_FILE) run --rm $(NODE_USER_FLAGS) $(SERVICE_NAME) bash -c "$(PNPM_STORE_SETUP) && pnpm install && pnpm run audit:deps && pnpm run type-check && pnpm run format:check && pnpm run lint"

qa-unit:
	@echo "🧪 [11X] Ejecutando Pruebas Unitarias Aisladas (Vitest >= 95%) + Build Vite..."
	docker compose -f $(COMPOSE_FILE) run --rm $(NODE_USER_FLAGS) $(SERVICE_NAME) bash -c "$(PNPM_STORE_SETUP) && pnpm install && pnpm run test:coverage && pnpm run build"

qa-orphans:
	@echo "🧩 [11X] Verificando Invariante de Cero Componentes UI Huérfanos..."
	docker run --rm -v "${HOST_PWD}/..:/workspace:ro" -w /workspace/frontend sinfallas/base-python-uv:3.13 python3 /workspace/.agents/scripts/verify_zero_orphan_vue_components.py

qa-mutation:
	@echo "👽 [11X] Ejecutando Pruebas de Mutación Frontend (Stryker)..."
	docker compose -f $(COMPOSE_FILE) run --rm $(NODE_USER_FLAGS) $(SERVICE_NAME) bash -c "$(PNPM_STORE_SETUP) && pnpm install"
	docker compose -f $(COMPOSE_FILE) run --rm $(NODE_USER_FLAGS) $(E2E_SERVICE) bash -c "./node_modules/.bin/stryker run stryker.conf.json"

qa-perf: build-ui
	@echo "⚡ [11X] Ejecutando Auditoría de Rendimiento (Lighthouse CI)..."
	docker compose -f $(COMPOSE_FILE) run --rm $(NODE_USER_FLAGS) $(E2E_SERVICE) bash -c "$(PNPM_STORE_SETUP) && ./node_modules/.bin/lhci autorun"

qa-lighthouse: qa-perf

qa-e2e: build-ui
	@echo "🎭 [11X] Ejecutando Regresión Visual, Geometría Anti-JSDOM y Accesibilidad WCAG 2.1 AA..."
	docker compose -f $(COMPOSE_FILE) run --rm $(NODE_USER_FLAGS) $(E2E_SERVICE) bash -c "$(PNPM_STORE_SETUP) && ./node_modules/.bin/playwright test"

qa-a11y: qa-e2e

qa-bdd: build-ui
	@echo "📚 [11X] Ejecutando Pruebas de Aceptación BDD (Karate UI en Chrome Headless)..."
	docker compose -f $(COMPOSE_FILE) run --rm karatelabs mvn clean test

qa-ui-bdd: qa-bdd

qa-all: qa-lint qa-orphans qa-unit qa-mutation qa-perf qa-e2e qa-bdd
	@echo "✅ Pipeline QA Frontend (Vue 3 11X) completado exitosamente."

clean-cache:
	@echo "🧹 Limpiando volúmenes de caché de pnpm y apagando redes..."
	docker compose -f $(COMPOSE_FILE) down -v
