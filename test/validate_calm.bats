#!/usr/bin/env bats
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
# Suite BATS para certificar .agents/scripts/validate_calm_architecture.sh.

REPO_ROOT="$(cd "$(dirname "${BATS_TEST_FILENAME}")/.." && pwd)"

setup() {
  load '/opt/bats-libs/bats-support/load.bash'
  load '/opt/bats-libs/bats-assert/load.bash'

  SANDBOX="${BATS_TEST_TMPDIR}/repo"
  MOCK_BIN="${BATS_TEST_TMPDIR}/bin"
  mkdir -p "${SANDBOX}/architecture" "${MOCK_BIN}"
  cp "${REPO_ROOT}/architecture/qa-11x.calm.json" "${SANDBOX}/architecture/qa-11x.calm.json"

  cat >"${MOCK_BIN}/node" <<'EOF'
#!/usr/bin/env bash
cat >/dev/null
if [ "${MOCK_NODE_FAIL:-0}" = "1" ]; then
  echo "violacion calm simulada" >&2
  exit 1
fi
printf '%s|10|14|7' "${ARCH_INPUT:-architecture/qa-11x.calm.json}"
EOF
  cat >"${MOCK_BIN}/calm" <<'EOF'
#!/usr/bin/env bash
if [ "${MOCK_CALM_CMD_FAIL:-0}" = "1" ]; then
  echo "calm cli error" >&2
  exit 1
fi
if [ "${MOCK_CALM_WARN:-0}" = "1" ]; then
  printf '{"hasErrors":false,"hasWarnings":true}\n'
  exit 0
fi
printf '{"hasErrors":false,"hasWarnings":false}\n'
EOF
  chmod +x "${MOCK_BIN}/node" "${MOCK_BIN}/calm"
}

@test "validate_calm_architecture.sh --help y errores de argumentos" {
  run bash "${REPO_ROOT}/.agents/scripts/validate_calm_architecture.sh" --help
  assert_success
  assert_output --partial "Uso: validate_calm_architecture.sh"

  run bash "${REPO_ROOT}/.agents/scripts/validate_calm_architecture.sh" --arch
  assert_failure
  assert_output --partial "Falta argumento"

  run bash "${REPO_ROOT}/.agents/scripts/validate_calm_architecture.sh" --invalida
  assert_failure
  assert_output --partial "Argumento no soportado"
}

@test "validate_calm_architecture.sh ejecuta inner_exec en contenedor y docker run fuera de contenedor" {
  # Dentro de contenedor sin CLI docker -> inner_exec directo
  run env QA_REPO_ROOT="${SANDBOX}" QA11X_DOCKERENV_PATH="/.dockerenv" PATH="${MOCK_BIN}:/usr/bin:/bin" \
    bash "${REPO_ROOT}/.agents/scripts/validate_calm_architecture.sh" --arch=architecture/qa-11x.calm.json
  assert_success
  assert_output --partial "validado (10 nodos, 14 relaciones, 7 controles)"

  # Fallo de calm CLI
  run env QA_REPO_ROOT="${SANDBOX}" QA11X_DOCKERENV_PATH="/.dockerenv" MOCK_CALM_CMD_FAIL=1 PATH="${MOCK_BIN}:/usr/bin:/bin" \
    bash "${REPO_ROOT}/.agents/scripts/validate_calm_architecture.sh" --arch architecture/qa-11x.calm.json
  assert_failure
  assert_output --partial "Falló @finos/calm-cli"

  # Fuera de contenedor sin docker -> error Rule Zero
  run env QA_REPO_ROOT="${SANDBOX}" QA11X_DOCKERENV_PATH="/nonexistent" PATH="${MOCK_BIN}:/usr/bin:/bin" \
    bash "${REPO_ROOT}/.agents/scripts/validate_calm_architecture.sh"
  assert_failure
  assert_output --partial "Docker requerido bajo Regla Cero"

  # Con docker mockeado -> ejecuta docker run
  cat >"${MOCK_BIN}/docker" <<'EOF'
#!/usr/bin/env bash
echo "✅ [CALM] architecture/qa-11x.calm.json validado (10 nodos, 14 relaciones, 7 controles)"
EOF
  chmod +x "${MOCK_BIN}/docker"
  run env QA_REPO_ROOT="${SANDBOX}" PATH="${MOCK_BIN}:/usr/bin:/bin" \
    bash "${REPO_ROOT}/.agents/scripts/validate_calm_architecture.sh"
  assert_success
  assert_output --partial "validado (10 nodos"
}
