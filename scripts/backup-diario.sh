#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors
# Propósito: Respaldo diario no destructivo de PostgreSQL 17 (pg_dump) y MinIO S3 (mc mirror)
# con cifrado opcional AES-256-PBKDF2, sumas SHA-256, rotación y alerta al >= 75% de disco (APSC-DV-001090).

LC_ALL=C
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

mostrar_ayuda() {
  cat <<'EOF'
Uso: ./scripts/backup-diario.sh [opciones]

Genera respaldos comprimidos e íntegros (SHA-256, cifrado opcional AES-256-PBKDF2)
de PostgreSQL 17 y del almacenamiento de objetos MinIO S3 desde el despliegue
productivo docker-compose.yml.

Opciones:
  --backup-dir <ruta>       Directorio destino de respaldos (por defecto BACKUP_DIR o ./backups).
  --retention-days <días>   Días de retención antes de rotar archivos antiguos (por defecto 30).
  -q, --quiet               Suprime salida informativa estándar (mantiene alertas de disco/error).
  -h, --help                Muestra esta ayuda y finaliza.
EOF
}

QUIET=false
BACKUP_DIR_ARG=""
RETENTION_ARG=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    -h | --help)
      mostrar_ayuda
      exit 0
      ;;
    -q | --quiet)
      QUIET=true
      shift
      ;;
    --backup-dir)
      [ "$#" -ge 2 ] || {
        echo "❌ --backup-dir requiere un argumento." >&2
        exit 1
      }
      BACKUP_DIR_ARG="$2"
      shift 2
      ;;
    --retention-days)
      [ "$#" -ge 2 ] || {
        echo "❌ --retention-days requiere un argumento." >&2
        exit 1
      }
      RETENTION_ARG="$2"
      shift 2
      ;;
    *)
      echo "❌ Opción desconocida: $1" >&2
      exit 1
      ;;
  esac
done

cargar_env_seguro() {
  local env_file="$1"
  [ -f "${env_file}" ] || return 0
  while IFS= read -r line || [ -n "${line}" ]; do
    line="${line%$'\r'}"
    case "${line}" in
      "" | \#*) continue ;;
    esac
    if [[ "${line}" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      local key="${BASH_REMATCH[1]}"
      local val="${BASH_REMATCH[2]}"
      val="${val#\"}"
      val="${val%\"}"
      val="${val#\'}"
      val="${val%\'}"
      if [ -z "${!key+x}" ]; then
        export "${key}=${val}"
      fi
    fi
  done <"${env_file}"
}

verificar_uso_disco() {
  local target_dir="$1"
  local uso_pct
  uso_pct=$(df -P "${target_dir}" 2>/dev/null | awk 'NR==2 {gsub("%", "", $5); print $5}')
  if [[ "${uso_pct:-0}" =~ ^[0-9]+$ ]] && [ "${uso_pct}" -ge 75 ]; then
    echo "⚠️ [APSC-DV-001090] Alerta de almacenamiento: el volumen de respaldos supera el ${uso_pct}% (>= 75%)." >&2
  fi
}

cifrar_y_firmar() {
  local archivo_origen="$1"
  local archivo_final="${archivo_origen}"
  if [ -n "${BACKUP_PASSPHRASE:-}" ]; then
    if ! command -v openssl >/dev/null 2>&1; then
      echo "❌ Se definió BACKUP_PASSPHRASE pero openssl no está disponible." >&2
      exit 1
    fi
    archivo_final="${archivo_origen}.enc"
    openssl enc -aes-256-cbc -pbkdf2 -iter 100000 -salt \
      -in "${archivo_origen}" -out "${archivo_final}" -pass env:BACKUP_PASSPHRASE
    rm -f -- "${archivo_origen}"
  fi
  sha256sum "${archivo_final}" >"${archivo_final}.sha256"
  printf '%s\n' "${archivo_final}"
}

cargar_env_seguro "${REPO_ROOT}/.env"

BACKUP_DIR="${BACKUP_DIR_ARG:-${BACKUP_DIR:-${REPO_ROOT}/backups}}"
RETENTION_DAYS="${RETENTION_ARG:-${BACKUP_RETENTION_DAYS:-30}}"
POSTGRES_USER="${POSTGRES_USER:-condominio_admin}"
POSTGRES_DB="${POSTGRES_DB:-condominio_db}"
MINIO_ROOT_USER="${MINIO_ROOT_USER:-}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-}"
MINIO_BUCKET="${MINIO_BUCKET:-condominio-media}"
COMPOSE_FILE="${COMPOSE_FILE:-${REPO_ROOT}/docker-compose.yml}"
MC_IMAGE="minio/mc:RELEASE.2025-02-15T09-17-07Z"
COMPOSE_PROJECT="${COMPOSE_PROJECT_NAME:-$(basename "${REPO_ROOT}")}"

if ! [[ "${RETENTION_DAYS}" =~ ^[0-9]+$ ]]; then
  echo "❌ BACKUP_RETENTION_DAYS debe ser un entero no negativo." >&2
  exit 1
fi

mkdir -p -- "${BACKUP_DIR}"
chmod 700 "${BACKUP_DIR}" || true
verificar_uso_disco "${BACKUP_DIR}"

FECHA="$(date +%Y%m%d_%H%M%S)"
PG_RAW="${BACKUP_DIR}/pg17_${FECHA}.dump.gz"
MINIO_STAGING="${BACKUP_DIR}/.staging_minio_${FECHA}"
MINIO_RAW="${BACKUP_DIR}/minio_${FECHA}.tar.gz"

cleanup_staging() {
  rm -rf -- "${MINIO_STAGING}" 2>/dev/null || true
}
trap cleanup_staging EXIT

# 1. Respaldo lógico consistente PostgreSQL 17
docker compose -f "${COMPOSE_FILE}" exec -T postgres \
  pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --format=custom --no-owner --no-acl |
  gzip -9 >"${PG_RAW}"
PG_FINAL="$(cifrar_y_firmar "${PG_RAW}")"

# 2. Espejo e empaquetado del bucket MinIO S3 (usando red Docker interna de compose)
mkdir -p -- "${MINIO_STAGING}"
export MC_HOST_prod="http://${MINIO_ROOT_USER}:${MINIO_ROOT_PASSWORD}@minio:9000"
docker run --rm --network "${COMPOSE_PROJECT}_backend_net" \
  -v "${MINIO_STAGING}:/backup_out" \
  -e MC_HOST_prod \
  "${MC_IMAGE}" mirror --overwrite "prod/${MINIO_BUCKET}" /backup_out >/dev/null 2>&1 || true

tar -czf "${MINIO_RAW}" -C "${MINIO_STAGING}" .
MINIO_FINAL="$(cifrar_y_firmar "${MINIO_RAW}")"
cleanup_staging

# 3. Rotación por ventana de retención
find "${BACKUP_DIR}" -maxdepth 1 -type f \
  \( -name "pg17_*" -o -name "minio_*" \) \
  -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true

if [ "${QUIET}" = false ]; then
  echo "✔ [Backup 11X] Respaldos generados: $(basename "${PG_FINAL}"), $(basename "${MINIO_FINAL}") (retención ${RETENTION_DAYS}d)."
fi
exit 0
