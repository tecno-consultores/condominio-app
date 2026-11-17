#!/usr/bin/env bats
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
# Suite BATS para certificar .agents/scripts/certify_task_completion.sh (Rule Zero y 10/10 gates).

REPO_ROOT="$(cd "$(dirname "${BATS_TEST_FILENAME}")/.." && pwd)"

setup() {
  load '/opt/bats-libs/bats-support/load.bash'
  load '/opt/bats-libs/bats-assert/load.bash'

  SANDBOX="${BATS_TEST_TMPDIR}/repo"
  MOCK_BIN="${BATS_TEST_TMPDIR}/bin"
  mkdir -p "${SANDBOX}/scripts" "${SANDBOX}/architecture" "${SANDBOX}/test" "${MOCK_BIN}"

  touch "${SANDBOX}/architecture/qa-11x.calm.json"
  printf '#!/usr/bin/env bash\necho "✔ [Secretos] OK"\n' >"${SANDBOX}/scripts/verificar-secretos.sh"
  printf '#!/usr/bin/env bash\necho "✔ [Trivy] OK"\n' >"${SANDBOX}/scripts/auditar-infra.sh"
  chmod +x "${SANDBOX}/scripts/verificar-secretos.sh" "${SANDBOX}/scripts/auditar-infra.sh"

  git -C "${SANDBOX}" init -q
  git -C "${SANDBOX}" config user.email "qa@condominio.test"
  git -C "${SANDBOX}" config user.name "QA Bot"
  git -C "${SANDBOX}" add .
  git -C "${SANDBOX}" commit -qm "chore: init"

  cat >"${MOCK_BIN}/python3" <<'EOF'
#!/usr/bin/env bash
if [ "${MOCK_PY_FAIL:-0}" = "1" ]; then
  echo "error python simulado" >&2
  exit 1
fi
echo "✔ [Mock Python] $(basename "${1:-script}") OK"
EOF
  cat >"${MOCK_BIN}/node" <<'EOF'
#!/usr/bin/env bash
cat >/dev/null
printf 'architecture/qa-11x.calm.json|10|14|7'
EOF
  chmod +x "${MOCK_BIN}/python3" "${MOCK_BIN}/node"
}

@test "certify_task_completion.sh --help, opcion invalida y sin docker fuera de contenedor" {
  run bash "${REPO_ROOT}/.agents/scripts/certify_task_completion.sh" --help
  assert_success
  assert_output --partial "Uso:"

  run bash "${REPO_ROOT}/.agents/scripts/certify_task_completion.sh" --bad-flag
  assert_failure
  assert_output --partial "Opción no reconocida"

  run env QA_REPO_ROOT="${SANDBOX}" QA11X_DOCKERENV_PATH="/nonexistent" PATH="${MOCK_BIN}:/usr/bin:/bin" \
    bash "${REPO_ROOT}/.agents/scripts/certify_task_completion.sh"
  assert_failure
  assert_output --partial "Docker no está disponible"
}

@test "certify_task_completion.sh aprueba 10/10 con --strict, detecta DOCS_ONLY, SYNC y bloquea incumplimientos" {
  # 1. Árbol limpio -> 10/10 PASS
  run env QA_REPO_ROOT="${SANDBOX}" QA11X_DOCKERENV_PATH="/.dockerenv" PATH="${MOCK_BIN}:/usr/bin:/bin" \
    bash "${REPO_ROOT}/.agents/scripts/certify_task_completion.sh" --strict
  assert_success
  assert_output --partial "[PASS] CERTIFY-STATE | 10/10 PASS, 0 SKIPPED, 0 FAIL"

  # 2. Fast-path DOCS_ONLY
  printf '# Doc\n' >"${SANDBOX}/README.md"
  run env QA_REPO_ROOT="${SANDBOX}" QA11X_DOCKERENV_PATH="/.dockerenv" PATH="${MOCK_BIN}:/usr/bin:/bin" \
    bash "${REPO_ROOT}/.agents/scripts/certify_task_completion.sh"
  assert_success
  assert_output --partial "[Doc Fast-Path]"

  # 3. Código + test + doc sincronizados
  printf '#!/usr/bin/env bash\necho ok\n' >"${SANDBOX}/scripts/demo.sh"
  printf '# test\n' >"${SANDBOX}/test/demo.bats"
  run env QA_REPO_ROOT="${SANDBOX}" QA11X_DOCKERENV_PATH="/.dockerenv" PATH="${MOCK_BIN}:/usr/bin:/bin" \
    bash "${REPO_ROOT}/.agents/scripts/certify_task_completion.sh" --strict
  assert_success
  assert_output --partial "[Doc & Test Sync]"

  # 4. Código sin test ni doc -> falla Gate 10
  rm -f "${SANDBOX}/README.md" "${SANDBOX}/test/demo.bats"
  run env QA_REPO_ROOT="${SANDBOX}" QA11X_DOCKERENV_PATH="/.dockerenv" PATH="${MOCK_BIN}:/usr/bin:/bin" \
    bash "${REPO_ROOT}/.agents/scripts/certify_task_completion.sh"
  assert_failure
  assert_output --partial "GATE 10/10 FAILED"

  # 5. --strict bloquea cuando hay gates SKIPPED (secretos, trivy y calm)
  rm -f "${SANDBOX}/scripts/demo.sh" "${SANDBOX}/scripts/verificar-secretos.sh" "${SANDBOX}/scripts/auditar-infra.sh" "${SANDBOX}/architecture/qa-11x.calm.json"
  git -C "${SANDBOX}" add -A
  git -C "${SANDBOX}" commit -qm "chore: clean before strict skip test"
  run env QA_REPO_ROOT="${SANDBOX}" QA11X_DOCKERENV_PATH="/.dockerenv" QA11X_STRICT=1 PATH="${MOCK_BIN}:/usr/bin:/bin" \
    bash "${REPO_ROOT}/.agents/scripts/certify_task_completion.sh"
  assert_failure
  assert_output --partial "Certificación bloqueada"

  # 6. Modo docker fuera de /.dockerenv + GITHUB_ACTIONS=true con commit docs en HEAD~1..HEAD
  printf '# release\n' >"${SANDBOX}/README.md"
  git -C "${SANDBOX}" add README.md
  git -C "${SANDBOX}" commit -qm "docs: release notes"
  cat >"${MOCK_BIN}/docker" <<'EOF'
#!/usr/bin/env bash
echo "✔ [Docker Python] OK"
EOF
  chmod +x "${MOCK_BIN}/docker"
  run env QA_REPO_ROOT="${SANDBOX}" QA11X_DOCKERENV_PATH="/nonexistent" GITHUB_ACTIONS="true" PATH="${MOCK_BIN}:/usr/bin:/bin" \
    bash "${REPO_ROOT}/.agents/scripts/certify_task_completion.sh"
  assert_success
  assert_output --partial "[WARN] CERTIFY-STATE | 7/10 PASS, 3 SKIPPED, 0 FAIL"
}
