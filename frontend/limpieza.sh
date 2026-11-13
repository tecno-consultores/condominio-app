#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors
# Propósito: Purga segura del entorno QA de Vue 3 delegando al limpiador sin sudo (Rule Zero).

LC_ALL=C
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "🧹 Limpiando caché, builds, reportes y contenedores QA del Frontend Vue 3..."
docker compose -f "${SCRIPT_DIR}/docker-compose.qa.yml" down -v 2>/dev/null || true

"${REPO_ROOT}/scripts/limpieza.sh" "$@"
exit 0
