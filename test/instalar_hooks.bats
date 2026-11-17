#!/usr/bin/env bats
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
# Suite BATS para certificar instalar-hooks.sh (Rule Zero, sin binario lefthook en host).

REPO_ROOT="$(cd "$(dirname "${BATS_TEST_FILENAME}")/.." && pwd)"

setup() {
  load '/opt/bats-libs/bats-support/load.bash'
  load '/opt/bats-libs/bats-assert/load.bash'

  SANDBOX="${BATS_TEST_TMPDIR}/repo"
  mkdir -p "${SANDBOX}"
}

@test "instalar-hooks.sh --help y error si no existe .git/hooks" {
  run env QA_REPO_ROOT="${SANDBOX}" bash "${REPO_ROOT}/instalar-hooks.sh" --help
  assert_success
  assert_output --partial "Uso: ./instalar-hooks.sh"

  run env QA_REPO_ROOT="${SANDBOX}" bash "${REPO_ROOT}/instalar-hooks.sh"
  assert_failure
  assert_output --partial "No existe el directorio"
}

@test "instalar-hooks.sh crea shims ejecutables pre-commit, commit-msg y pre-push" {
  mkdir -p "${SANDBOX}/.git/hooks"
  run env QA_REPO_ROOT="${SANDBOX}" bash "${REPO_ROOT}/instalar-hooks.sh"
  assert_success
  assert_output --partial "Hooks Git efímeros"

  for hook in pre-commit commit-msg pre-push; do
    [ -x "${SANDBOX}/.git/hooks/${hook}" ]
  done

  run grep -Fq 'verificar-secretos.sh' "${SANDBOX}/.git/hooks/pre-commit"
  assert_success
  run grep -Fq 'commitlint.config.js' "${SANDBOX}/.git/hooks/commit-msg"
  assert_success
  run grep -Fq 'auditar-infra.sh' "${SANDBOX}/.git/hooks/pre-push"
  assert_success
}
