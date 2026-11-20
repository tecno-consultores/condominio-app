#!/usr/bin/env bats
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
# Suite BATS para certificar workflows GitHub Actions (SHA-40, concurrency, timeout) y Makefiles (-T, --frozen).

REPO_ROOT="$(cd "$(dirname "${BATS_TEST_FILENAME}")/.." && pwd)"

setup() {
  load '/opt/bats-libs/bats-support/load.bash'
  load '/opt/bats-libs/bats-assert/load.bash'
}

@test "workflows GitHub Actions cumplen permisos minimos, concurrency, timeout-minutes y QA-CI-ESCAPE-01" {
  for wf in \
    "${REPO_ROOT}/.github/workflows/00-iac-audit.yml" \
    "${REPO_ROOT}/.github/workflows/01-ci-backend.yml" \
    "${REPO_ROOT}/.github/workflows/02-ci-frontend.yml" \
    "${REPO_ROOT}/.github/workflows/03-cd-dockerhub.yml"; do
    [ -f "${wf}" ]
    run grep -Eq '^permissions:' "${wf}"
    assert_success
    run grep -Eq 'contents:[[:space:]]*read' "${wf}"
    assert_success
    run grep -Eq '^concurrency:' "${wf}"
    assert_success
    run grep -Eq 'timeout-minutes:' "${wf}"
    assert_success
  done

  run grep -En '\$\$\(' "${REPO_ROOT}"/.github/workflows/*.yml
  assert_failure
}

@test "workflows GitHub Actions fijan todas las acciones uses: con SHA-40 (SEC-CI-ACTION-REF)" {
  run bash -c '
    bad=0
    while IFS= read -r line; do
      ref="${line##*uses:}"
      ref="$(echo "${ref}" | sed -E "s/#.*//; s/^[[:space:]]+//; s/[[:space:]]+$//")"
      if ! echo "${ref}" | grep -Eq "@[0-9a-f]{40}$"; then
        echo "BAD ACTION REF: ${line}"
        bad=1
      fi
    done < <(grep -hE "^[[:space:]]*-?[[:space:]]*uses:" "'"${REPO_ROOT}"'"/.github/workflows/*.yml)
    exit "${bad}"
  '
  assert_success
}

@test "Makefiles usan CURDIR, flags -T y lockfiles estrictos (--frozen / --frozen-lockfile)" {
  for mk in \
    "${REPO_ROOT}/backend/Makefile" \
    "${REPO_ROOT}/frontend/Makefile"; do
    [ -f "${mk}" ]
    run grep -Fq 'HOST_PWD ?= $(CURDIR)' "${mk}"
    assert_success
    run grep -Fq 'run --rm -T' "${mk}"
    assert_success
  done

  run grep -Fq 'run --rm -T' "${REPO_ROOT}/Makefile"
  assert_success
  run grep -Fn '$(PWD)' "${REPO_ROOT}/Makefile" "${REPO_ROOT}/backend/Makefile" "${REPO_ROOT}/frontend/Makefile"
  assert_failure

  run grep -Fq 'uv sync --frozen' "${REPO_ROOT}/backend/Makefile"
  assert_success
  run grep -Fq 'pnpm install --frozen-lockfile' "${REPO_ROOT}/frontend/Makefile"
  assert_success
  run grep -Fq 'UI_SKIP_BUILD' "${REPO_ROOT}/frontend/Makefile"
  assert_success
}

@test "frontend/Makefile asegura node_modules bloqueados antes de qa-perf y qa-e2e bajo UI_SKIP_BUILD=1" {
  run grep -Fq 'ensure-deps:' "${REPO_ROOT}/frontend/Makefile"
  assert_success
  run grep -Fq 'pnpm install --frozen-lockfile' "${REPO_ROOT}/frontend/Makefile"
  assert_success
  run grep -Eq '^qa-perf:[[:space:]]*build-ui[[:space:]]+ensure-deps' "${REPO_ROOT}/frontend/Makefile"
  assert_success
  run grep -Eq '^qa-e2e:[[:space:]]*build-ui[[:space:]]+ensure-deps' "${REPO_ROOT}/frontend/Makefile"
  assert_success
}
