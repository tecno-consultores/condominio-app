#!/usr/bin/env bats
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
# Suite BATS para certificar scripts/verificar-secretos.sh (escaneo completo + fix grep -e).

REPO_ROOT="$(cd "$(dirname "${BATS_TEST_FILENAME}")/.." && pwd)"

setup() {
  load '/opt/bats-libs/bats-support/load.bash'
  load '/opt/bats-libs/bats-assert/load.bash'

  SANDBOX="${BATS_TEST_TMPDIR}/repo"
  mkdir -p "${SANDBOX}/src" "${SANDBOX}/tests"
  git -C "${SANDBOX}" init -q
  git -C "${SANDBOX}" config user.email "qa@condominio.test"
  git -C "${SANDBOX}" config user.name "QA Bot"
}

@test "verificar-secretos.sh --help y escaneo limpio con .env.example y tests" {
  run env QA_REPO_ROOT="${SANDBOX}" bash "${REPO_ROOT}/scripts/verificar-secretos.sh" --help
  assert_success
  assert_output --partial "Uso: ./scripts/verificar-secretos.sh"

  run env QA_REPO_ROOT="${SANDBOX}" bash "${REPO_ROOT}/scripts/verificar-secretos.sh"
  assert_success
  assert_output --partial "0 archivos para escanear"

  touch "${SANDBOX}/logo.png"
  git -C "${SANDBOX}" add logo.png
  run env QA_REPO_ROOT="${SANDBOX}" bash "${REPO_ROOT}/scripts/verificar-secretos.sh"
  assert_success
  assert_output --partial "0 archivos textuales sujetos a escaneo"

  printf 'POSTGRES_PASSWORD=CAMBIAR_PLACEHOLDER_REAL\n' >"${SANDBOX}/.env.example"
  printf 'password="SecurePassword123!"\n' >"${SANDBOX}/tests/sample.py"
  git -C "${SANDBOX}" add .env.example tests/sample.py
  run env QA_REPO_ROOT="${SANDBOX}" bash "${REPO_ROOT}/scripts/verificar-secretos.sh"
  assert_success
  assert_output --partial "0 secretos expuestos (2 archivos escaneados)"
}

@test "verificar-secretos.sh bloquea .env trackeado, llaves privadas (--BEGIN) y tokens en tests" {
  printf 'SECRET_KEY=solo-local\n' >"${SANDBOX}/.env"
  git -C "${SANDBOX}" add -f .env
  run env QA_REPO_ROOT="${SANDBOX}" bash "${REPO_ROOT}/scripts/verificar-secretos.sh"
  assert_failure
  assert_output --partial "Archivo sensible trackeado en Git"
  git -C "${SANDBOX}" rm --cached -q .env
  rm -f "${SANDBOX}/.env"

  # Llave privada con prefijo '--' que antes cegaba a GNU grep sin '-e'
  printf '%sBEGIN RSA PRIVATE KEY%s\n' '-----' '-----' >"${SANDBOX}/src/leaked.pem"
  printf 'ghp_%s987654\n' 'AbCdEfGhIjKlMnOpQrStUvWxYz789012' >"${SANDBOX}/tests/leaked_test.py"
  git -C "${SANDBOX}" add src/leaked.pem tests/leaked_test.py

  run env QA_REPO_ROOT="${SANDBOX}" bash "${REPO_ROOT}/scripts/verificar-secretos.sh"
  assert_failure
  assert_output --partial "src/leaked.pem"
  assert_output --partial "tests/leaked_test.py"
}
