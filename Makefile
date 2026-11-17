.PHONY: qa-infra qa-secrets qa-bash qa-calm qa-lint qa-unit qa-parity qa-bdd qa-ui-bdd qa-e2e qa-perf qa-all certify clean-cache

# ==============================================================================
# MAKEFILE RAÍZ UNIFICADO — CONDOMINIO APP (ESTÁNDAR CORPORATIVO 11X)
# ==============================================================================

export QA_UID := $(shell id -u)
export QA_GID := $(shell id -g)

qa-secrets:
	@echo "🔐 Escaneando secretos y credenciales en el repositorio..."
	./scripts/verificar-secretos.sh

qa-infra:
	@echo "🛰️ Ejecutando auditoría Trivy IaC + File System (HIGH/CRITICAL)..."
	./scripts/auditar-infra.sh

qa-calm:
	@echo "🏛️ Validando arquitectura FINOS CALM 1.2 y controles 11X..."
	./.agents/scripts/validate_calm_architecture.sh

qa-bash:
	@echo "🐚 Validando scripts Bash (shfmt, ShellCheck), BATS y cobertura kcov >= 95%..."
	@docker compose --project-directory "$(CURDIR)" -f docker-compose.qa.yml run --rm -T qa-bash bash -c 'set -euo pipefail; shopt -s globstar nullglob; shfmt -d -i 2 -ci instalar-hooks.sh scripts/*.sh .agents/scripts/*.sh backend/docker-entrypoint.sh test/*.bats && shellcheck instalar-hooks.sh scripts/*.sh .agents/scripts/*.sh backend/docker-entrypoint.sh && rm -rf /tmp/coverage_report && rc=0; kcov --bash-dont-parse-binary-dir --include-path=/app/instalar-hooks.sh,/app/scripts,/app/.agents/scripts,/app/backend/docker-entrypoint.sh --exclude-pattern=/app/test /tmp/coverage_report bats test/ >/tmp/bats-tap.log 2>/tmp/kcov-stderr.log || rc=$$?; cat /tmp/bats-tap.log; if [ "$${rc}" -ne 0 ]; then cat /tmp/kcov-stderr.log >&2; exit "$${rc}"; fi; /usr/bin/python3 -c "import json, pathlib, sys; r = pathlib.Path(\"/tmp/coverage_report\"); jf = [p for p in sorted(r.rglob(\"coverage.json\")) if not p.parent.is_symlink()]; ds = [json.loads(p.read_text()) for p in jf]; tot = sum(int(d.get(\"total_lines\", 0)) for d in ds); cov = sum(int(d.get(\"covered_lines\", 0)) for d in ds); pct = (cov * 100.0 / tot if tot > 0 else 0.0); print(\"✔ [kcov] Cobertura Bash: %.2f%% (%d/%d líneas, umbral >= 95.0%%)\" % (pct, cov, tot)); sys.exit(0 if pct >= 95.0 else 1)"'

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

qa-ui-bdd:
	$(MAKE) -C frontend qa-bdd

qa-e2e:
	$(MAKE) -C frontend qa-e2e

qa-perf:
	$(MAKE) -C frontend qa-perf

certify:
	./.agents/scripts/certify_task_completion.sh --strict

qa-all: qa-secrets qa-infra qa-bash qa-calm qa-lint qa-unit qa-parity qa-bdd qa-e2e qa-perf qa-ui-bdd
	@echo "✅ Suite unificada QA 11X completada exitosamente."

clean-cache:
	./scripts/limpieza.sh
