#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
# Propósito: Compuerta de certificación 11X (10/10) bajo Rule Zero estricto (sinfallas/base-python-uv:3.13).

LC_ALL=C
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${QA_REPO_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
cd "${REPO_ROOT}"

PY_DOCKER_IMAGE="${QA_PYTHON_IMAGE:-sinfallas/base-python-uv:3.13@sha256:1594cbb33269c6a535a8ae5242b07a5866aa519d00975868f0a0d03fdc3bc155}"
QA_DOCKERENV_FILE="${QA11X_DOCKERENV_PATH:-/.dockerenv}"
STRICT_MODE=false

if [ "${QA11X_STRICT:-0}" = "1" ] || [ "${QA11X_STRICT:-}" = "true" ]; then
  STRICT_MODE=true
fi

for arg in "$@"; do
  case "${arg}" in
    --strict)
      STRICT_MODE=true
      ;;
    -h | --help)
      printf 'Uso: %s [--strict]\n' "$0"
      exit 0
      ;;
    *)
      printf '❌ Opción no reconocida: %s\n' "${arg}" >&2
      exit 1
      ;;
  esac
done

PASS_COUNT=0
SKIPPED_COUNT=0
FAIL_COUNT=0

# shellcheck disable=SC2329
run_py_rule_zero() {
  if [ -f "${QA_DOCKERENV_FILE}" ]; then
    python3 "$@"
    return $?
  fi

  if ! command -v docker >/dev/null 2>&1; then
    printf '❌ [Rule Zero] Docker no está disponible para ejecutar Python en contenedor efímero.\n' >&2
    return 1
  fi

  local -a container_args=()
  local arg
  for arg in "$@"; do
    case "${arg}" in
      "${REPO_ROOT}")
        container_args+=("/app")
        ;;
      "${REPO_ROOT}/"*)
        container_args+=("/app/${arg#"${REPO_ROOT}/"}")
        ;;
      *)
        container_args+=("${arg}")
        ;;
    esac
  done

  docker run --rm --network none \
    -u "$(id -u):$(id -g)" \
    -e HOME=/tmp \
    -v "${REPO_ROOT}:/app:ro" \
    -w /app \
    "${PY_DOCKER_IMAGE}" python3 "${container_args[@]}"
}

run_gate() {
  local gate_num="$1"
  local gate_name="$2"
  shift 2

  printf '[%s/10] ' "${gate_num}"
  local out
  local rc=0
  out="$("$@" 2>&1)" || rc=$?

  if [ "${rc}" -eq 20 ]; then
    SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
    printf '%s\n' "${out}"
    return 0
  fi

  if [ "${rc}" -ne 0 ]; then
    FAIL_COUNT=$((FAIL_COUNT + 1))
    printf '❌ [GATE %s/10 FAILED] %s (rc=%s)\n' "${gate_num}" "${gate_name}" "${rc}" >&2
    if [ -n "${out}" ]; then
      printf '%s\n' "${out}" >&2
    fi
    exit "${rc}"
  fi

  PASS_COUNT=$((PASS_COUNT + 1))
  printf '%s\n' "${out}"
}

# shellcheck disable=SC2329
gate_01_secrets() {
  if [ -f "${REPO_ROOT}/scripts/verificar-secretos.sh" ]; then
    QA_REPO_ROOT="${REPO_ROOT}" bash "${REPO_ROOT}/scripts/verificar-secretos.sh"
    return $?
  fi
  printf '⚠️ [SKIPPED] Script scripts/verificar-secretos.sh no encontrado.\n'
  return 20
}

# shellcheck disable=SC2329
gate_02_trivy() {
  if [ -f "${REPO_ROOT}/scripts/auditar-infra.sh" ]; then
    QA_REPO_ROOT="${REPO_ROOT}" bash "${REPO_ROOT}/scripts/auditar-infra.sh"
    return $?
  fi
  printf '⚠️ [SKIPPED] Script scripts/auditar-infra.sh no encontrado.\n'
  return 20
}

# shellcheck disable=SC2329
gate_08_calm() {
  if [ -f "${SCRIPT_DIR}/validate_calm_architecture.sh" ] && [ -f "${REPO_ROOT}/architecture/qa-11x.calm.json" ]; then
    QA_REPO_ROOT="${REPO_ROOT}" bash "${SCRIPT_DIR}/validate_calm_architecture.sh"
    return $?
  fi
  printf '⚠️ [SKIPPED] Modelo CALM o validador no encontrado.\n'
  return 20
}

# shellcheck disable=SC2329
gate_10_doc_and_test_sync() {
  local all_changed
  local code_changes
  local exec_src_changes
  local doc_changes
  local code_count
  local test_changes
  local test_count
  local karate_changes
  local karate_status
  local doc_count
  local gate10_failed

  if [ -f "${SCRIPT_DIR}/verify_docs_invariants.py" ]; then
    run_py_rule_zero "${SCRIPT_DIR}/verify_docs_invariants.py" "${REPO_ROOT}"
  fi

  all_changed="$( (
    git -C "${REPO_ROOT}" diff --name-only HEAD 2>/dev/null || true
    git -C "${REPO_ROOT}" ls-files --others --exclude-standard 2>/dev/null || true
  ) | sort -u)"
  if [ -z "${all_changed}" ] && [ "${GITHUB_ACTIONS:-false}" = "true" ]; then
    if git -C "${REPO_ROOT}" rev-parse --verify HEAD~1 >/dev/null 2>&1; then
      all_changed=$(git -C "${REPO_ROOT}" diff --name-only HEAD~1..HEAD 2>/dev/null | sort -u || true)
    fi
  fi

  code_changes=$(printf '%s\n' "${all_changed}" | grep -E '^((backend|frontend|scripts|architecture)/|\.agents/(scripts|rules)/|((.*/)?Makefile)$|\.github/workflows/|(\.trivy\.yaml|lefthook\.yml|instalar-hooks\.sh|commitlint\.config\.js|docker-compose.*\.yml|package\.json)$)' | grep -vE '(\.md$|(^|/)graphify-out/)' || true)
  exec_src_changes=$(printf '%s\n' "${code_changes}" | grep -E '^((backend|frontend)/src/|scripts/|\.agents/scripts/|instalar-hooks\.sh$|backend/docker-entrypoint\.sh$)' | grep -vE '(\.unit\.(py|ts|tsx)|\.e2e\.ts|test_.*\.py|.*\.test\.(ts|js)|\.feature|\.bats)' || true)
  doc_changes=$(printf '%s\n' "${all_changed}" | grep -E '(\.md$|^docs/)' | grep -vE '^\.agents/(rules)/' || true)

  if [ -n "${code_changes}" ]; then
    code_count=$(printf '%s\n' "${code_changes}" | grep -c . || true)
    test_changes=$(printf '%s\n' "${all_changed}" | grep -E '(\.unit\.(py|ts|tsx)|\.e2e\.ts|test_.*\.py|.*\.test\.(ts|js)|\.feature|\.bats)' || true)
    test_count=$([ -n "${test_changes}" ] && printf '%s\n' "${test_changes}" | grep -c . || echo 0)
    karate_changes=$(printf '%s\n' "${all_changed}" | grep -E '\.feature$' || true)
    karate_status=$([ -n "${karate_changes}" ] && printf 'Karate BDD actualizado' || printf 'sin cambios .feature')
    doc_count=$([ -n "${doc_changes}" ] && printf '%s\n' "${doc_changes}" | grep -c . || echo 0)

    gate10_failed=0
    if [ -n "${exec_src_changes}" ] && [ "${test_count}" -eq 0 ]; then
      gate10_failed=1
    fi
    if [ "${doc_count}" -eq 0 ]; then
      gate10_failed=1
    fi

    if [ "${gate10_failed}" -eq 0 ]; then
      printf '✔ [Doc & Test Sync] %s archivo(s) de código/config | %s prueba(s) (%s) | %s doc(s) sincronizados.\n' \
        "${code_count}" "${test_count}" "${karate_status}" "${doc_count}"
      return 0
    fi

    printf '❌ [Doc & Test Sync] Incumplimiento detectado en %s archivo(s) modificados:\n' "${code_count}"
    while IFS= read -r line; do
      [ -n "${line}" ] && printf '  - %s\n' "${line}"
    done <<<"${code_changes}"
    if [ -n "${exec_src_changes}" ] && [ "${test_count}" -eq 0 ]; then
      printf '  ❌ ERROR: Se modificó código ejecutable pero NO hay pruebas unitarias, E2E, BATS o BDD modificadas.\n'
    fi
    if [ "${doc_count}" -eq 0 ]; then
      printf '  ❌ ERROR: Se modificó código/configuración pero NO se han actualizado docs/, CHANGELOG.md, TESTING.md o README.md.\n'
    fi
    return 1
  elif [ -n "${doc_changes}" ]; then
    doc_count=$(printf '%s\n' "${doc_changes}" | grep -c . || true)
    printf '✔ [Doc Fast-Path] Solo cambios de documentación (%s archivo(s) .md); 0 cambios de código.\n' "${doc_count}"
  else
    printf '✔ [Doc & Test Sync] Árbol de código limpio (0 cambios pendientes).\n'
  fi
}

printf '🛡️ [QA 11X Gate] Ejecutando 10 validaciones de certificación (Rule Zero)...\n'

run_gate 1 "Secret Audit" gate_01_secrets
run_gate 2 "Trivy IaC & FS" gate_02_trivy
run_gate 3 "JSON Integrity" run_py_rule_zero "${SCRIPT_DIR}/verify_json_no_duplicate_keys.py" "${REPO_ROOT}"
run_gate 4 "Zero Orphan UI Components" run_py_rule_zero "${SCRIPT_DIR}/verify_zero_orphan_vue_components.py"
run_gate 5 "No Orphan API Endpoints" run_py_rule_zero "${SCRIPT_DIR}/verify_no_orphan_api_endpoints.py" "${REPO_ROOT}"
run_gate 6 "AST Topological Health" run_py_rule_zero "${SCRIPT_DIR}/verify_topological_health.py" "${REPO_ROOT}"
run_gate 7 "ORM & Migration Parity" run_py_rule_zero "${SCRIPT_DIR}/verify_alembic_orm_parity.py"
run_gate 8 "FINOS CALM Architecture" gate_08_calm
run_gate 9 "Roadmap & ActiveTask Sync" run_py_rule_zero "${SCRIPT_DIR}/verify_roadmap_consistency.py"
run_gate 10 "Doc & Test Sync" gate_10_doc_and_test_sync

state_tag="PASS"
if [ "${SKIPPED_COUNT}" -gt 0 ]; then
  state_tag="WARN"
fi
printf '[%s] CERTIFY-STATE | %s/10 PASS, %s SKIPPED, %s FAIL\n' \
  "${state_tag}" "${PASS_COUNT}" "${SKIPPED_COUNT}" "${FAIL_COUNT}"

if [ "${STRICT_MODE}" = "true" ] && [ "${SKIPPED_COUNT}" -gt 0 ]; then
  printf '❌ [STRICT] Certificación bloqueada: %s gate(s) en estado SKIPPED.\n' "${SKIPPED_COUNT}" >&2
  exit 1
fi

printf '✅ CERTIFICACIÓN EXITOSA: El proyecto cumple con el estándar 11X\n'
exit 0
