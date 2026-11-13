.PHONY: qa-infra qa-secrets qa-lint qa-unit qa-parity qa-bdd qa-e2e qa-perf qa-all clean-cache

# ==============================================================================
# MAKEFILE RAÍZ UNIFICADO — CONDOMINIO APP (ESTÁNDAR CORPORATIVO 11X)
# ==============================================================================

qa-secrets:
	@echo "🔐 Escaneando secretos y credenciales en el repositorio..."
	./scripts/verificar-secretos.sh

qa-infra:
	@echo "🛰️ Ejecutando auditoría Trivy IaC + File System (HIGH/CRITICAL)..."
	./scripts/auditar-infra.sh

qa-lint:
	$(MAKE) -C backend qa-lint
	$(MAKE) -C frontend qa-lint

qa-unit:
	$(MAKE) -C backend qa-unit
	$(MAKE) -C frontend qa-orphans qa-unit

qa-parity:
	$(MAKE) -C backend qa-parity

qa-bdd:
	$(MAKE) -C backend qa-bdd

qa-e2e:
	$(MAKE) -C frontend qa-e2e

qa-perf:
	$(MAKE) -C frontend qa-perf

qa-all: qa-secrets qa-infra qa-lint qa-unit qa-parity qa-bdd
	@echo "✅ Suite unificada QA 11X completada exitosamente."

clean-cache:
	./scripts/limpieza.sh
