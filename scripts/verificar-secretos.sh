#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
# Propósito: Detección preventiva de credenciales y secretos hardcodeados en todo el árbol del repositorio
# (incluyendo .env.example y suites de prueba), ejecutando siempre desde REPO_ROOT.

LC_ALL=C
set -euo pipefail

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  echo "Uso: ./scripts/verificar-secretos.sh [archivo ...]"
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${QA_REPO_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
cd "${REPO_ROOT}"

TARGET_FILES=("$@")

# Bloquear de inmediato si .env o variantes reales (.env.*) fueron añadidas al índice de Git
if command -v git >/dev/null 2>&1; then
  TRACKED_ENV="$(git ls-files '.env' '.env.*' 2>/dev/null | grep -Ev '\.(example|sample|template)$' || true)"
  if [ -n "${TRACKED_ENV}" ]; then
    echo "🚨 ERROR CRÍTICO: Archivo sensible trackeado en Git (${TRACKED_ENV}). Ejecute 'git rm --cached'." >&2
    exit 1
  fi
fi

if [ "${#TARGET_FILES[@]}" -eq 0 ]; then
  RAW_TRACKED="$(git ls-files 2>/dev/null || true)"
  RAW_UNTRACKED="$(git ls-files --others --exclude-standard 2>/dev/null || true)"
  while IFS= read -r line; do
    [ -n "${line}" ] && TARGET_FILES+=("${line}")
  done < <(printf '%s\n%s\n' "${RAW_TRACKED}" "${RAW_UNTRACKED}" | sort -u)
fi

if [ "${#TARGET_FILES[@]}" -eq 0 ]; then
  echo "✔ [Secretos] 0 archivos para escanear."
  exit 0
fi

FILTERED_FILES=()
for file in "${TARGET_FILES[@]}"; do
  [ -n "${file}" ] || continue
  rel_file="${file#"${REPO_ROOT}/"}"
  if [ -f "${file}" ] &&
    [[ ! "${rel_file}" =~ \.(png|jpg|jpeg|gif|webp|avif|ico|pdf|woff2?|ttf|eot|pyc|lock)$ ]] &&
    [[ ! "${rel_file}" =~ (^|/)(pnpm-lock\.yaml|uv\.lock)$ ]] &&
    [[ "${rel_file}" != "scripts/verificar-secretos.sh" ]]; then
    FILTERED_FILES+=("${file}")
  fi
done

if [ "${#FILTERED_FILES[@]}" -eq 0 ]; then
  echo "✔ [Secretos] 0 archivos textuales sujetos a escaneo."
  exit 0
fi

SECRET_REGEX='-----BEGIN (RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----|((npm|ghp|gho|ghu|ghs)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|glpat-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16})|(password|passwd|secret|api_key|token)[=:] *["'\'']?[A-Za-z0-9_/-]{16,}["'\'']?'
PLACEHOLDER_REGEX='(TU_TOKEN|tu_clave_aqui|tu_token_aqui|CHANGE[_-]?ME|EXAMPLE_ONLY|example_placeholder|YOUR_TOKEN_EXAMPLE|TU_TOKEN_EXAMPLE|sk-proj-placeholder|placeholder|dummy|00000000|test-load-token|mock|fake|ephemeral|xxxxxx|123456|<[^>]+>|https?://(127\.0\.0\.1|localhost|0\.0\.0\.0|\[::1\]|([a-z0-9-]+\.)?example\.(com|org|net))|env\.|process\.env|os\.environ|\$\{|PasswordErroneo123!|SecurePassword123!|Clave(Segura|Inicial|Tenant|Rls|Torre|Default)[A-Za-z0-9!]+|qr-seed-token-|csrf-(rotado|body|cookie)-)'

MATCHED_FILES=()
for f in "${FILTERED_FILES[@]}"; do
  HITS=$(grep -niE -e "${SECRET_REGEX}" -- "$f" 2>/dev/null | grep -viE -e "${PLACEHOLDER_REGEX}" || true)
  if [ -n "${HITS}" ]; then
    MATCHED_FILES+=("$f")
  fi
done

if [ "${#MATCHED_FILES[@]}" -gt 0 ]; then
  echo "🚨 ERROR: Posible secreto o clave privada hardcodeada detectada en:" >&2
  for mfile in "${MATCHED_FILES[@]}"; do
    echo "  - ${mfile}" >&2
  done
  exit 1
fi

echo "✔ [Secretos] 0 secretos expuestos (${#FILTERED_FILES[@]} archivos escaneados)."
exit 0
