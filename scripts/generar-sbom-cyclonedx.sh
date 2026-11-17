#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
# Propósito: Generación de SBOM / CBOM en formato CycloneDX JSON (ECMA-424)
# en artifacts/sbom/ bajo ejecución 100% en contenedor efímero Trivy (Rule Zero).

LC_ALL=C
set -euo pipefail

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  cat <<'EOF'
Uso: ./scripts/generar-sbom-cyclonedx.sh [archivo_salida_relativo]

Genera el inventario SBOM CycloneDX (ECMA-424) en contenedor Trivy no-root.
Por defecto escribe en: artifacts/sbom/sbom.cyclonedx.json
EOF
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${QA_REPO_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
OUTPUT_FILE="${1:-artifacts/sbom/sbom.cyclonedx.json}"

if [ -z "${OUTPUT_FILE}" ] || [[ "${OUTPUT_FILE}" == /* ]] || [[ "${OUTPUT_FILE}" == *".."* ]]; then
  echo "❌ ERROR: La ruta de salida debe ser relativa dentro del repositorio (recibido: '${OUTPUT_FILE}')." >&2
  exit 1
fi

mkdir -p "$(dirname "${REPO_ROOT}/${OUTPUT_FILE}")"

docker run --rm \
  -u "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e TRIVY_CACHE_DIR=/tmp/trivy-cache \
  -v "${REPO_ROOT}:/workspace" \
  -w /workspace \
  aquasec/trivy@sha256:8f6bb947dbc528902e11f2f5be52f7b519f6a39d5d148f41166f2040499768fb fs \
  --quiet \
  --skip-dirs backend/.venv,frontend/node_modules,node_modules,graphify-out,backend/graphify-out,frontend/graphify-out,artifacts \
  --format cyclonedx \
  --output "/workspace/${OUTPUT_FILE}" \
  /workspace

if [ ! -s "${REPO_ROOT}/${OUTPUT_FILE}" ]; then
  echo "❌ ERROR: El archivo SBOM '${OUTPUT_FILE}' está vacío o no fue generado." >&2
  exit 1
fi

echo "✔ [SBOM CycloneDX] Generado exitosamente en: ${OUTPUT_FILE}"
exit 0
