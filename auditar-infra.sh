#!/usr/bin/env bash
# Licencia: MIT
# Propósito: Auditoría efímera de Infraestructura como Código (IaC) usando Trivy.

LC_ALL=C
set -e

echo "🛡️ Iniciando Auditoría de Seguridad de Infraestructura (Trivy IaC)..."

# Escáner de misconfiguraciones mapeando el repositorio al contenedor.
# ":ro" (Read-Only) garantiza que Trivy no pueda alterar el código fuente.
docker run --rm \
  -v "${PWD}:/app:ro" \
  -w /app \
  aquasec/trivy:latest config . \
  --severity HIGH,CRITICAL \
  --exit-code 1 \
  --skip-dirs backend/.venv

# Si el comando anterior no arroja Exit Code 1, pasamos a escanear vulnerabilidades (CVEs)
# en los manifiestos de dependencias expuestos en el file system.
echo "✅ IaC validado. Escaneando vulnerabilidades (CVEs) en el File System..."

docker run --rm \
  -v "${PWD}:/app:ro" \
  -w /app \
  aquasec/trivy:latest fs . \
  --severity CRITICAL \
  --exit-code 1 \
  --skip-dirs backend/.venv

echo "✅ Auditoría de Infraestructura superada. Entorno seguro."
exit 0