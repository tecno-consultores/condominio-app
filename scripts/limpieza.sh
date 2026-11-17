#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
# Propósito: Script universal de limpieza y saneamiento de espacio de trabajo (Estándar QA 11X)
# Restringido a archivos docker-compose*.qa.yml (protege volúmenes productivos postgres_data y minio_data).

LC_ALL=C
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${QA_REPO_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
cd "${REPO_ROOT}"

mostrar_ayuda() {
  cat <<'EOF'
Uso: ./scripts/limpieza.sh [opciones]

Elimina residuos de pruebas, cachés, entornos virtuales locales, node_modules,
reportes de cobertura/seguridad y contenedores QA efímeros (*.qa.yml), preservando
los volúmenes productivos (postgres_data, minio_data), artifacts/sbom/ y los
grafos AST (graphify-out/graph.json, GRAPH_REPORT.md, graph.html, manifest.json).

Opciones:
  -q, --quiet           Modo silencioso (omite el mensaje final de resumen).
  --deep, --docker-prune
                        Purga adicional de evidencias locales (.agents/backups,
                        .agents/proposals, .qa-evidence.json) y contenedores/redes
                        Docker huérfanos (sin ejecutar docker system prune).
  -h, --help            Muestra esta ayuda y finaliza.
EOF
}

QUIET=false
DEEP_PRUNE=false
for arg in "$@"; do
  case "${arg}" in
    -q | --quiet) QUIET=true ;;
    --deep | --docker-prune) DEEP_PRUNE=true ;;
    -h | --help)
      mostrar_ayuda
      exit 0
      ;;
    *)
      echo "❌ Opción desconocida: ${arg}" >&2
      exit 1
      ;;
  esac
done

purge_db_files() {
  local dir="$1"
  [ -d "${dir}" ] || return 0
  rm -f -- \
    "${dir}"/*.db "${dir}"/*.db-journal "${dir}"/*.db-shm "${dir}"/*.db-wal \
    "${dir}"/*.sqlite "${dir}"/*.sqlite-journal "${dir}"/*.sqlite-shm "${dir}"/*.sqlite-wal \
    "${dir}"/*.sqlite3 "${dir}"/*.sqlite3-journal "${dir}"/*.sqlite3-shm "${dir}"/*.sqlite3-wal \
    2>/dev/null || true
}

purge_dir_artifacts() {
  local dir="$1"
  [ -d "${dir}" ] || return 0

  purge_db_files "${dir}"
  purge_db_files "${dir}/test"
  purge_db_files "${dir}/tests"

  rm -f -- \
    "${dir}/.coverage" "${dir}"/.coverage.* \
    "${dir}/coverage.xml" "${dir}/coverage.json" "${dir}/lcov.info" \
    "${dir}/junit.xml" "${dir}/pytest-report.xml" "${dir}/test-report.xml" \
    "${dir}"/trivy-results* \
    "${dir}/sbom.cyclonedx.json" "${dir}"/sbom-*.cdx.json "${dir}"/sbom* \
    "${dir}"/*.cdx.json "${dir}"/*.spdx.json \
    "${dir}/mutmut-stats.json" "${dir}"/mutmut-*.json \
    "${dir}"/zap-report* "${dir}"/chaos-report* \
    "${dir}/profile.svg" "${dir}/profile.speedscope.json" \
    "${dir}/locust-report.html" "${dir}"/locust_*.csv \
    "${dir}/.dmypy.json" "${dir}/dmypy.json" \
    "${dir}/dependency-reduced-pom.xml" \
    "${dir}/.task_scratchpad.md" "${dir}"/.agents/*.scratchpad.md \
    "${dir}"/*.log "${dir}"/*.tsbuildinfo \
    "${dir}"/*.tmp "${dir}"/*.temp "${dir}"/*.bak "${dir}"/*.orig "${dir}"/*.rej \
    "${dir}"/*.swp "${dir}"/*.swo "${dir}"/*~ \
    2>/dev/null || true

  rm -rf -- \
    "${dir}/venv" "${dir}/.venv" "${dir}/ENV" "${dir}/node_modules" \
    "${dir}/.pnpm-store" "${dir}/.turbo" "${dir}/.parcel-cache" \
    "${dir}/.pytest_cache" "${dir}/.mypy_cache" "${dir}/.ruff_cache" \
    "${dir}/.hypothesis" "${dir}/.schemathesis" "${dir}/schemathesis-report" \
    "${dir}/.tox" "${dir}/.nox" "${dir}/.uv" \
    "${dir}/htmlcov" "${dir}/coverage_report" "${dir}/.bats-battery" \
    "${dir}/build" "${dir}/wheels" "${dir}/.eggs" "${dir}"/*.egg-info \
    "${dir}/mutants" "${dir}/.mutmut-cache" "${dir}/locust_reports" \
    "${dir}/target" "${dir}/test/target" "${dir}/karate.jar" \
    "${dir}/zap_out" "${dir}/.trivycache" "${dir}/prometheus_data" \
    "${dir}/dist" "${dir}/dist-ssr" "${dir}/.nuxt" "${dir}/.vite" "${dir}/.vite-ssg-temp" \
    "${dir}/coverage" "${dir}/.nyc_output" "${dir}/.eslintcache" "${dir}/.stylelintcache" \
    "${dir}/playwright-report" "${dir}/blob-report" "${dir}/test-results" "${dir}/playwright/.cache" \
    "${dir}/.lighthouseci" "${dir}/lhci-reports" "${dir}/.lhcache" \
    "${dir}/.stryker-tmp" "${dir}/reports" \
    2>/dev/null || true

  if [ "${dir}" != "." ]; then
    rm -rf -- "${dir}/.agents" 2>/dev/null || true
  fi

  # Preserva graph.json, GRAPH_REPORT.md, graph.html y manifest.json; limpia cachés intermedios
  if [ -d "${dir}/graphify-out" ]; then
    rm -rf -- "${dir}/graphify-out/cache" "${dir}/graphify-out/20"* 2>/dev/null || true
    rm -f -- "${dir}/graphify-out/.graphify_"* "${dir}/graphify-out/.cloud-cta-shown" 2>/dev/null || true
  fi
}

# 1. Detener únicamente contenedores QA efímeros (*.qa.yml), protegiendo docker-compose.yml y docker-compose.prod.yml
if command -v docker >/dev/null 2>&1; then
  while IFS= read -r compose_file; do
    [ -n "${compose_file}" ] || continue
    compose_dir="$(dirname "${compose_file}")"
    (cd "${compose_dir}" && docker compose -f "$(basename "${compose_file}")" down --remove-orphans -v >/dev/null 2>&1 || true)
  done < <(find . -maxdepth 3 -name "docker-compose*.qa.yml" \
    -not -path "*/.git/*" \
    -not -path "*/node_modules/*" 2>/dev/null)
  if [ -f "backend/docker-compose.qa.yml" ]; then
    (cd backend && docker compose -f docker-compose.qa.yml --profile chaos down --remove-orphans -v >/dev/null 2>&1 || true)
  fi
fi

# 2. Eliminación de residuos de pruebas y normalización en raíz, backend/ y frontend/
rm -f -- /tmp/graphify_ast_*.log 2>/dev/null || true
purge_dir_artifacts "."
for sub in backend frontend; do
  purge_dir_artifacts "${sub}"
done

find . -type d \( -name "__pycache__" -o -name ".pytest_cache" -o -name ".mypy_cache" -o -name ".ruff_cache" -o -name "*.egg-info" \) \
  -not -path "*/.git/*" -exec rm -rf -- {} + 2>/dev/null || true
find . -type f \( -name "*.py[cod]" -o -name "*~" -o -name "*.swp" -o -name "*.swo" -o -name "*.tmp" -o -name "*.temp" -o -name "*.bak" -o -name "*.orig" -o -name "*.rej" \) \
  -not -path "*/.git/*" -not -path "./artifacts/*" -delete 2>/dev/null || true

# 3. Fallback con contenedor efímero Alpine para artefactos creados por UID 0 o UID 10001
CURRENT_UID="$(id -u)"
CURRENT_GID="$(id -g)"
if command -v docker >/dev/null 2>&1; then
  docker run --rm -v "${REPO_ROOT}:/workspace" alpine:3.21@sha256:bc21487101ae47172509130ee1092cc273a831968d64b617776d1f69c81e42ab sh -c "\
    for d in /workspace /workspace/backend /workspace/frontend; do \
      rm -rf \"\${d}/venv\" \"\${d}/.venv\" \"\${d}/ENV\" \"\${d}/node_modules\" \
             \"\${d}/.coverage\" \"\${d}\"/.coverage.* \"\${d}/.pnpm-store\" \
             \"\${d}/.pytest_cache\" \"\${d}/.mypy_cache\" \"\${d}/.ruff_cache\" \
             \"\${d}/.hypothesis\" \"\${d}/.schemathesis\" \"\${d}/.tox\" \"\${d}/.uv\" \
             \"\${d}/htmlcov\" \"\${d}/coverage_report\" \"\${d}/mutants\" \"\${d}/.mutmut-cache\" \
             \"\${d}/target\" \"\${d}/test/target\" \"\${d}/karate.jar\" \"\${d}/.trivycache\" \
             \"\${d}/dist\" \"\${d}/dist-ssr\" \"\${d}/coverage\" \"\${d}/.vite\" \
             \"\${d}/reports\" \"\${d}/.stryker-tmp\" \"\${d}/playwright-report\" \
             \"\${d}/blob-report\" \"\${d}/test-results\" \"\${d}/.lighthouseci\" \
             \"\${d}/lhci-reports\" \"\${d}/zap_out\" 2>/dev/null || true; \
      rm -f \"\${d}\"/*.db \"\${d}\"/*.db-* \"\${d}\"/*.sqlite* 2>/dev/null || true; \
    done; \
    rm -rf /workspace/backend/.agents /workspace/frontend/.agents 2>/dev/null || true; \
    find /workspace -not -path '*/.git/*' -not -path '*/node_modules/*' \\( -user 0 -o -user 10001 \\) -exec chown ${CURRENT_UID}:${CURRENT_GID} {} + 2>/dev/null || true" >/dev/null 2>&1 || true
fi

if [ "${DEEP_PRUNE}" = true ]; then
  rm -rf -- .agents/backups .agents/proposals .agents/.qa-evidence.json \
    ./*/.agents/backups ./*/.agents/proposals ./*/.agents/.qa-evidence.json \
    "${HOME}/.cache/qa-11x-blueprints" /tmp/.qa11x_trivy_cache_* 2>/dev/null || true
  if command -v docker >/dev/null 2>&1; then
    docker container prune -f >/dev/null 2>&1 || true
    docker network prune -f >/dev/null 2>&1 || true
  fi
fi

if [ "${QUIET}" = false ]; then
  echo "✔ [Clean 11X] Contenedores QA detenidos, cachés purgados y permisos normalizados (UID ${CURRENT_UID}:${CURRENT_GID})."
fi
exit 0
