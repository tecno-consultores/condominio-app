#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
# Propósito: Extracción y actualización limpia (--code-only) de grafos semánticos AST (Graphify).
# Purga nodos heredados antes de reconstruir y opera bajo Rule Zero (sinfallas/remote-graphify).

LC_ALL=C
set -euo pipefail

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  echo "Uso: ./scripts/actualizar-grafos-graphify.sh [--all|--force|<stack>]"
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${QA_REPO_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
IMAGE_NAME="${GRAPHIFY_IMAGE:-sinfallas/remote-graphify@sha256:08aa6a6fc5e72f25bb6a37da632932fe295ba0d72fd971ae5b365eeea3f778b0}"
FORCE_ALL=false

if [ "${1:-}" = "--all" ] || [ "${1:-}" = "--force" ]; then
  FORCE_ALL=true
  shift
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "❌ Error: Docker no está instalado o no se encuentra en el PATH." >&2
  exit 1
fi

extract_graph_in_dir() {
  local target_dir="$1"
  local log_file
  log_file="$(mktemp /tmp/graphify_ast.XXXXXX.log)"

  rm -rf -- \
    "${target_dir}/graphify-out/graph.json" \
    "${target_dir}/graphify-out/manifest.json" \
    "${target_dir}/graphify-out/GRAPH_REPORT.md" \
    "${target_dir}/graphify-out/graph.html" \
    "${target_dir}/graphify-out/cache" \
    "${target_dir}/graphify-out/20"* \
    "${target_dir}/graphify-out/.graphify_"* \
    2>/dev/null || true

  if ! docker run --rm \
    -e OLLAMA_BASE_URL="" \
    -v "${target_dir}:/app" \
    -w /app \
    "${IMAGE_NAME}" \
    sh -c "graphify extract . --code-only && graphify cluster-only ." >"${log_file}" 2>&1; then
    echo "❌ [Graphify AST] Error al extraer el grafo en '${target_dir}':" >&2
    cat "${log_file}" >&2
    rm -f -- "${log_file}"
    return 1
  fi
  rm -f -- "${log_file}"

  docker run --rm \
    -v "${target_dir}:/work" \
    "${IMAGE_NAME}" \
    sh -c "rm -rf /work/graphify-out/cache /work/graphify-out/20* /work/graphify-out/.graphify_* /work/graphify-out/.cloud-cta-shown 2>/dev/null || true; chown -R $(id -u):$(id -g) /work/graphify-out 2>/dev/null || true" >/dev/null 2>&1 || true
}

stack_needs_update() {
  local target_dir="$1"
  local rel_name="$2"
  local graph_file="${target_dir}/graphify-out/graph.json"

  if [ "${FORCE_ALL}" = true ] || [ ! -s "${graph_file}" ]; then
    return 0
  fi

  local newer_files
  newer_files=$(find "${target_dir}" -maxdepth 4 \
    \( -name node_modules -o -name .git -o -name dist -o -name coverage -o -name graphify-out -o -name .venv -o -name artifacts \) -prune \
    -o -type f \( -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.py' -o -name '*.vue' -o -name '*.sh' \) \
    -newer "${graph_file}" -print -quit 2>/dev/null || true)
  if [ -n "${newer_files}" ]; then
    return 0
  fi

  if command -v git >/dev/null 2>&1 && [ -d "${REPO_ROOT}/.git" ]; then
    local git_code_changes
    git_code_changes=$(git -C "${REPO_ROOT}" status --porcelain "${rel_name}" 2>/dev/null |
      grep -vE '(\.md$|graphify-out/)' || true)
    if [ -n "${git_code_changes}" ]; then
      return 0
    fi
  fi

  return 1
}

if [ $# -ge 1 ] && [ -d "${REPO_ROOT}/$1" ]; then
  extract_graph_in_dir "${REPO_ROOT}/$1"
  echo "✔ [Graphify AST] Grafo semántico actualizado para '$1' -> $1/graphify-out/graph.json."
  exit 0
fi

STACKS=()
for s in backend frontend; do
  if [ -d "${REPO_ROOT}/${s}" ]; then
    STACKS+=("${s}")
  fi
done

UPDATED=()
SKIPPED=()

if stack_needs_update "${REPO_ROOT}" "."; then
  extract_graph_in_dir "${REPO_ROOT}"
  UPDATED+=("root")
else
  SKIPPED+=("root")
fi

for s in "${STACKS[@]}"; do
  if stack_needs_update "${REPO_ROOT}/${s}" "${s}"; then
    extract_graph_in_dir "${REPO_ROOT}/${s}"
    UPDATED+=("${s}")
  else
    SKIPPED+=("${s}")
  fi
done

echo "✔ [Graphify AST] Actualizados: ${#UPDATED[@]} (${UPDATED[*]:-ninguno}) | Omitidos sin cambios de código: ${#SKIPPED[@]} (${SKIPPED[*]:-ninguno})."
exit 0
