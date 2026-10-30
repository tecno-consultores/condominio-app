#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors
# Propósito: Purga profunda integral del monorepo Condominio App (Backend FastAPI + Frontend Vue 3, Nivel 11X).

LC_ALL=C

if [[ "$EUID" != "0" ]]; then
        echo "ERROR: debe ser root. Ejecuta con sudo ./limpieza.sh"
        exit 1
fi

clear
echo "Iniciando purga profunda integral de Condominio App (Backend + Frontend, Nivel 11X)..."

# Artefactos globales y de backend
rm -f .coverage backend/.coverage
rm -rf .mypy_cache backend/.mypy_cache
rm -rf .pytest_cache backend/.pytest_cache
rm -rf .ruff_cache backend/.ruff_cache
rm -rf .tox backend/.tox
rm -rf .schemathesis backend/.schemathesis
rm -rf .uv/ backend/.uv/
rm -rf dist backend/dist frontend/dist
rm -rf htmlcov/ backend/htmlcov/
rm -rf backend/tests/__pycache__ backend/src/*/__pycache__ backend/scripts/*/__pycache__
rm -rf target/ backend/target/ backend/test/target/ frontend/target/ frontend/test/target/
rm -f zap-report.html backend/zap-report.html
rm -f chaos-report.html backend/chaos-report.html
rm -f zap.yaml backend/zap.yaml
rm -f profile.svg backend/profile.svg
rm -rf prometheus_data/ backend/prometheus_data/ frontend/prometheus_data/
rm -rf .venv backend/.venv

# Artefactos de frontend Vue 3
rm -rf node_modules frontend/node_modules
rm -rf frontend/.nuxt
rm -rf test-results/ frontend/test-results/
rm -rf playwright-report/ frontend/playwright-report/
rm -rf blob-report/ frontend/blob-report/
rm -rf coverage/ frontend/coverage/
rm -rf .stryker-tmp/ frontend/.stryker-tmp/
rm -rf lhci-reports/ frontend/lhci-reports/
rm -rf .lighthouseci/ frontend/.lighthouseci/
rm -rf .lhcache/ frontend/.lhcache/
rm -f *.log backend/*.log frontend/*.log

chown -R "${SUDO_USER:-$USER}:${SUDO_USER:-$USER}" . 2>/dev/null || true

docker compose -f backend/docker-compose.qa.yml down -v 2>/dev/null || true
docker compose -f backend/docker-compose.qa.yml --profile chaos down -v 2>/dev/null || true
docker compose -f backend/docker-compose.qa.yml --profile graphify down -v 2>/dev/null || true
docker compose -f frontend/docker-compose.qa.yml down -v 2>/dev/null || true
docker compose -f frontend/docker-compose.qa.yml --profile observability down -v 2>/dev/null || true
docker compose -f frontend/docker-compose.qa.yml --profile graphify down -v 2>/dev/null || true

docker system prune -af --volumes

echo "Purga integral de caché, reportes, imágenes y contenedores finalizada exitosamente."
exit 0
