#!/usr/bin/env bats
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
# Suite BATS para certificar backend/docker-entrypoint.sh (CONTAINER_ROLE=api|worker y --healthcheck).

REPO_ROOT="$(cd "$(dirname "${BATS_TEST_FILENAME}")/.." && pwd)"

setup() {
  load '/opt/bats-libs/bats-support/load.bash'
  load '/opt/bats-libs/bats-assert/load.bash'

  MOCK_BIN="${BATS_TEST_TMPDIR}/bin"
  CALL_LOG="${BATS_TEST_TMPDIR}/calls.log"
  mkdir -p "${MOCK_BIN}"
  : >"${CALL_LOG}"

  cat >"${MOCK_BIN}/python" <<EOF
#!/usr/bin/env bash
printf 'python %s\n' "\$*" >> "${CALL_LOG}"
exit 0
EOF
  cat >"${MOCK_BIN}/uvicorn" <<EOF
#!/usr/bin/env bash
printf 'uvicorn %s\n' "\$*" >> "${CALL_LOG}"
exit 0
EOF
  chmod +x "${MOCK_BIN}/python" "${MOCK_BIN}/uvicorn"
}

@test "docker-entrypoint.sh muestra ayuda y ejecuta comando personalizado" {
  run bash "${REPO_ROOT}/backend/docker-entrypoint.sh" --help
  assert_success
  assert_output --partial "Uso: docker-entrypoint.sh"

  run env PATH="${MOCK_BIN}:${PATH}" bash "${REPO_ROOT}/backend/docker-entrypoint.sh" echo "hola-entrypoint"
  assert_success
  assert_output "hola-entrypoint"
}

@test "docker-entrypoint.sh arranca y verifica salud para CONTAINER_ROLE=api y worker" {
  run env CONTAINER_ROLE=api PATH="${MOCK_BIN}:${PATH}" bash "${REPO_ROOT}/backend/docker-entrypoint.sh" --healthcheck
  assert_success
  run env CONTAINER_ROLE=worker PATH="${MOCK_BIN}:${PATH}" bash "${REPO_ROOT}/backend/docker-entrypoint.sh" --healthcheck
  assert_success
  run env CONTAINER_ROLE=api PATH="${MOCK_BIN}:${PATH}" bash "${REPO_ROOT}/backend/docker-entrypoint.sh"
  assert_success
  run env CONTAINER_ROLE=worker PATH="${MOCK_BIN}:${PATH}" bash "${REPO_ROOT}/backend/docker-entrypoint.sh"
  assert_success

  run cat "${CALL_LOG}"
  assert_output --partial "http.client.HTTPConnection"
  assert_output --partial "python -m src.worker --check-health"
  assert_output --partial "uvicorn src.main:app --host 0.0.0.0 --port 8000 --proxy-headers"
  assert_output --partial "python -m src.worker"
}

@test "docker-entrypoint.sh rechaza CONTAINER_ROLE invalido en healthcheck" {
  run env CONTAINER_ROLE=desconocido bash "${REPO_ROOT}/backend/docker-entrypoint.sh" --healthcheck
  assert_failure
  assert_output --partial "CONTAINER_ROLE inválido para healthcheck"
}

@test "docker-entrypoint.sh rechaza CONTAINER_ROLE invalido en arranque" {
  run env CONTAINER_ROLE=desconocido bash "${REPO_ROOT}/backend/docker-entrypoint.sh"
  assert_failure
  assert_output --partial "CONTAINER_ROLE inválido"
}
