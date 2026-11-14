#!/usr/bin/env bats
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors
# Suite BATS para certificar sintaxis Bash de workflows GitHub Actions y Makefiles (Estándar QA 11X).

REPO_ROOT="$(cd "$(dirname "${BATS_TEST_FILENAME}")/.." && pwd)"

setup() {
  load '/opt/bats-libs/bats-support/load.bash'
  load '/opt/bats-libs/bats-assert/load.bash'
}

@test "workflows GitHub Actions usan sintaxis bash sin escapes Makefile y permisos minimos" {
  for wf in \
    "${REPO_ROOT}/.github/workflows/00-iac-audit.yml" \
    "${REPO_ROOT}/.github/workflows/01-ci-backend.yml" \
    "${REPO_ROOT}/.github/workflows/02-ci-frontend.yml"; do
    [ -f "${wf}" ]
    run grep -Eq '^permissions:' "${wf}"
    assert_success
    run grep -Eq 'contents:[[:space:]]*read' "${wf}"
    assert_success
  done

  run grep -En '\$\$\(' "${REPO_ROOT}"/.github/workflows/*.yml
  assert_failure
}

@test "sub-Makefiles resuelven HOST_PWD con CURDIR en lugar de PWD heredado" {
  for mk in \
    "${REPO_ROOT}/backend/Makefile" \
    "${REPO_ROOT}/frontend/Makefile"; do
    [ -f "${mk}" ]
    run grep -Fq 'HOST_PWD ?= $(CURDIR)' "${mk}"
    assert_success
  done

  run grep -Fn 'HOST_PWD ?= $(PWD)' "${REPO_ROOT}/backend/Makefile" "${REPO_ROOT}/frontend/Makefile"
  assert_failure
}
