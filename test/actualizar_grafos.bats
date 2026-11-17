#!/usr/bin/env bats
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
# Suite BATS para certificar scripts/actualizar-grafos-graphify.sh (Rule Zero, --all, incremental, error).

REPO_ROOT="$(cd "$(dirname "${BATS_TEST_FILENAME}")/.." && pwd)"

setup() {
  load '/opt/bats-libs/bats-support/load.bash'
  load '/opt/bats-libs/bats-assert/load.bash'

  SANDBOX="${BATS_TEST_TMPDIR}/repo"
  MOCK_BIN="${BATS_TEST_TMPDIR}/bin"
  mkdir -p "${SANDBOX}/backend/src" "${SANDBOX}/frontend/src" "${MOCK_BIN}"
  git -C "${SANDBOX}" init -q
  git -C "${SANDBOX}" config user.email "qa@condominio.test"
  git -C "${SANDBOX}" config user.name "QA Bot"

  cat >"${MOCK_BIN}/docker" <<'EOF'
#!/usr/bin/env bash
if [ "${MOCK_GRAPHIFY_FAIL:-0}" = "1" ] && [[ "$*" == *"extract"* ]]; then
  echo "graphify error simulado" >&2
  exit 1
fi
for arg in "$@"; do
  case "${arg}" in
    *:/app)
      host_dir="${arg%:/app}"
      mkdir -p "${host_dir}/graphify-out"
      printf '{"nodes":[],"links":[]}\n' >"${host_dir}/graphify-out/graph.json"
      ;;
  esac
done
exit 0
EOF
  chmod +x "${MOCK_BIN}/docker"
}

@test "actualizar-grafos-graphify.sh --help y error sin docker" {
  run env QA_REPO_ROOT="${SANDBOX}" bash "${REPO_ROOT}/scripts/actualizar-grafos-graphify.sh" --help
  assert_success
  assert_output --partial "Uso: ./scripts/actualizar-grafos-graphify.sh"

  EMPTY_BIN="${BATS_TEST_TMPDIR}/empty_bin"
  mkdir -p "${EMPTY_BIN}"
  for cmd in env bash dirname cat rm mktemp find grep sort git mkdir touch; do
    cmd_path="$(command -v "${cmd}" || true)"
    [ -n "${cmd_path}" ] && ln -sf "${cmd_path}" "${EMPTY_BIN}/${cmd}"
  done
  run env QA_REPO_ROOT="${SANDBOX}" PATH="${EMPTY_BIN}" bash "${REPO_ROOT}/scripts/actualizar-grafos-graphify.sh" --all
  assert_failure
  assert_output --partial "Docker no está instalado"
}

@test "actualizar-grafos-graphify.sh reconstruye --all, omite sin cambios y detecta newer" {
  run env QA_REPO_ROOT="${SANDBOX}" PATH="${MOCK_BIN}:${PATH}" \
    bash "${REPO_ROOT}/scripts/actualizar-grafos-graphify.sh" --all
  assert_success
  assert_output --partial "Actualizados: 3 (root backend frontend)"
  [ -s "${SANDBOX}/graphify-out/graph.json" ]

  touch "${SANDBOX}/backend/src/a.py" "${SANDBOX}/frontend/src/a.ts"
  git -C "${SANDBOX}" add .
  git -C "${SANDBOX}" commit -qm "chore: base"
  touch -d "+2 seconds" "${SANDBOX}/graphify-out/graph.json" "${SANDBOX}/backend/graphify-out/graph.json" "${SANDBOX}/frontend/graphify-out/graph.json"

  run env QA_REPO_ROOT="${SANDBOX}" PATH="${MOCK_BIN}:${PATH}" \
    bash "${REPO_ROOT}/scripts/actualizar-grafos-graphify.sh"
  assert_success
  assert_output --partial "Omitidos sin cambios de código: 3 (root backend frontend)"

  touch -d "+5 seconds" "${SANDBOX}/backend/src/a.py"
  run env QA_REPO_ROOT="${SANDBOX}" PATH="${MOCK_BIN}:${PATH}" \
    bash "${REPO_ROOT}/scripts/actualizar-grafos-graphify.sh"
  assert_success
  assert_output --partial "backend"
}

@test "actualizar-grafos-graphify.sh detecta cambio por git status y actualiza stack puntual" {
  run env QA_REPO_ROOT="${SANDBOX}" PATH="${MOCK_BIN}:${PATH}" \
    bash "${REPO_ROOT}/scripts/actualizar-grafos-graphify.sh" --all
  assert_success

  touch "${SANDBOX}/backend/src/a.py"
  git -C "${SANDBOX}" add .
  git -C "${SANDBOX}" commit -qm "chore: base"
  touch -d "+10 seconds" "${SANDBOX}/graphify-out/graph.json" "${SANDBOX}/backend/graphify-out/graph.json" "${SANDBOX}/frontend/graphify-out/graph.json"

  printf 'print("dirty")\n' >"${SANDBOX}/backend/src/dirty.py"
  touch -d "-20 seconds" "${SANDBOX}/backend/src/dirty.py"
  run env QA_REPO_ROOT="${SANDBOX}" PATH="${MOCK_BIN}:${PATH}" \
    bash "${REPO_ROOT}/scripts/actualizar-grafos-graphify.sh"
  assert_success
  assert_output --partial "backend"

  run env QA_REPO_ROOT="${SANDBOX}" PATH="${MOCK_BIN}:${PATH}" \
    bash "${REPO_ROOT}/scripts/actualizar-grafos-graphify.sh" frontend
  assert_success
  assert_output --partial "actualizado para 'frontend'"
}

@test "actualizar-grafos-graphify.sh reporta error y limpia log temporal ante fallo de extraccion" {
  run env QA_REPO_ROOT="${SANDBOX}" MOCK_GRAPHIFY_FAIL=1 PATH="${MOCK_BIN}:${PATH}" \
    bash "${REPO_ROOT}/scripts/actualizar-grafos-graphify.sh" backend
  assert_failure
  assert_output --partial "Error al extraer el grafo"
}
