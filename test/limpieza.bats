#!/usr/bin/env bats
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors
# Suite BATS para certificar limpieza.sh, scripts/limpieza.sh y .gitignore (Estándar QA 11X).

REPO_ROOT="$(cd "$(dirname "${BATS_TEST_FILENAME}")/.." && pwd)"

setup() {
  load '/opt/bats-libs/bats-support/load.bash'
  load '/opt/bats-libs/bats-assert/load.bash'

  SANDBOX="${BATS_TEST_TMPDIR}/sandbox"
  MOCK_BIN="${BATS_TEST_TMPDIR}/bin"
  MOCK_HOME="${BATS_TEST_TMPDIR}/home"
  DOCKER_LOG="${BATS_TEST_TMPDIR}/docker_calls.log"

  mkdir -p "${SANDBOX}/scripts" "${MOCK_BIN}" "${MOCK_HOME}"
  cp "${REPO_ROOT}/limpieza.sh" "${SANDBOX}/limpieza.sh"
  cp "${REPO_ROOT}/scripts/limpieza.sh" "${SANDBOX}/scripts/limpieza.sh"
  chmod +x "${SANDBOX}/limpieza.sh" "${SANDBOX}/scripts/limpieza.sh"

  cat >"${MOCK_BIN}/docker" <<EOF
#!/usr/bin/env bash
printf '%s\n' "\$*" >> "${DOCKER_LOG}"
exit 0
EOF
  chmod +x "${MOCK_BIN}/docker"
  : >"${DOCKER_LOG}"
}

@test "limpieza.sh --help imprime uso y retorna 0" {
  run env HOME="${MOCK_HOME}" PATH="${MOCK_BIN}:${PATH}" bash "${SANDBOX}/limpieza.sh" --help
  assert_success
  assert_output --partial "Uso: ./limpieza.sh"
}

@test "limpieza.sh --quiet purga residuos de pruebas y preserva grafos AST y plantillas" {
  mkdir -p \
    "${SANDBOX}/backend/.venv/bin" \
    "${SANDBOX}/backend/htmlcov" \
    "${SANDBOX}/backend/.agents" \
    "${SANDBOX}/backend/tests/__pycache__" \
    "${SANDBOX}/frontend/node_modules/pkg" \
    "${SANDBOX}/frontend/dist/assets" \
    "${SANDBOX}/frontend/coverage" \
    "${SANDBOX}/graphify-out/cache" \
    "${SANDBOX}/graphify-out/20261113" \
    "${SANDBOX}/.agents"

  touch \
    "${SANDBOX}/.coverage" \
    "${SANDBOX}/backend/.venv/bin/python" \
    "${SANDBOX}/backend/htmlcov/index.html" \
    "${SANDBOX}/backend/qa.sqlite3-wal" \
    "${SANDBOX}/backend/tests/__pycache__/mod.pyc" \
    "${SANDBOX}/backend/.agents/.qa-evidence.json" \
    "${SANDBOX}/backend/zap.yaml" \
    "${SANDBOX}/frontend/node_modules/pkg/index.js" \
    "${SANDBOX}/frontend/dist/assets/app.js" \
    "${SANDBOX}/frontend/coverage/lcov.info" \
    "${SANDBOX}/zap-report.html" \
    "${SANDBOX}/profile.speedscope.json" \
    "${SANDBOX}/sbom.cyclonedx.json" \
    "${SANDBOX}/trivy-results.sarif" \
    "${SANDBOX}/graphify-out/cache/tmp.json" \
    "${SANDBOX}/graphify-out/20261113/old.json" \
    "${SANDBOX}/graphify-out/.graphify_tmp" \
    "${SANDBOX}/graphify-out/graph.json" \
    "${SANDBOX}/graphify-out/GRAPH_REPORT.md" \
    "${SANDBOX}/graphify-out/graph.html" \
    "${SANDBOX}/graphify-out/manifest.json" \
    "${SANDBOX}/.agents/ACTIVE_TASK.md" \
    "${SANDBOX}/.agents/ACTIVE_TASK.md.example"

  run env HOME="${MOCK_HOME}" PATH="${MOCK_BIN}:${PATH}" bash "${SANDBOX}/limpieza.sh" --quiet
  assert_success
  assert_output ""

  [ ! -e "${SANDBOX}/.coverage" ]
  [ ! -d "${SANDBOX}/backend/.venv" ]
  [ ! -d "${SANDBOX}/backend/htmlcov" ]
  [ ! -e "${SANDBOX}/backend/qa.sqlite3-wal" ]
  [ ! -d "${SANDBOX}/backend/tests/__pycache__" ]
  [ ! -d "${SANDBOX}/backend/.agents" ]
  [ ! -d "${SANDBOX}/frontend/node_modules" ]
  [ ! -d "${SANDBOX}/frontend/dist" ]
  [ ! -d "${SANDBOX}/frontend/coverage" ]
  [ ! -e "${SANDBOX}/zap-report.html" ]
  [ ! -e "${SANDBOX}/profile.speedscope.json" ]
  [ ! -e "${SANDBOX}/sbom.cyclonedx.json" ]
  [ ! -e "${SANDBOX}/trivy-results.sarif" ]
  [ ! -d "${SANDBOX}/graphify-out/cache" ]
  [ ! -d "${SANDBOX}/graphify-out/20261113" ]
  [ ! -e "${SANDBOX}/graphify-out/.graphify_tmp" ]

  [ -f "${SANDBOX}/graphify-out/graph.json" ]
  [ -f "${SANDBOX}/graphify-out/GRAPH_REPORT.md" ]
  [ -f "${SANDBOX}/graphify-out/graph.html" ]
  [ -f "${SANDBOX}/graphify-out/manifest.json" ]
  [ -f "${SANDBOX}/backend/zap.yaml" ]
  [ -f "${SANDBOX}/.agents/ACTIVE_TASK.md" ]
  [ -f "${SANDBOX}/.agents/ACTIVE_TASK.md.example" ]
}

@test "limpieza.sh --deep --quiet depura respaldos locales y evita docker system prune" {
  mkdir -p "${SANDBOX}/.agents/backups" "${SANDBOX}/.agents/proposals"
  touch "${SANDBOX}/.agents/backups/a.bak" "${SANDBOX}/.agents/proposals/p.md" "${SANDBOX}/.agents/.qa-evidence.json"

  run env HOME="${MOCK_HOME}" PATH="${MOCK_BIN}:${PATH}" bash "${SANDBOX}/limpieza.sh" --deep --quiet
  assert_success

  [ ! -d "${SANDBOX}/.agents/backups" ]
  [ ! -d "${SANDBOX}/.agents/proposals" ]
  [ ! -e "${SANDBOX}/.agents/.qa-evidence.json" ]

  run cat "${DOCKER_LOG}"
  assert_output --partial "container prune -f"
  assert_output --partial "network prune -f"
  refute_output --partial "system prune"
}

@test ".gitignore excluye artefactos efímeros y conserva plantillas y archivos fuente" {
  GIT_SANDBOX="${BATS_TEST_TMPDIR}/gitrepo"
  mkdir -p "${GIT_SANDBOX}"
  cp "${REPO_ROOT}/.gitignore" "${GIT_SANDBOX}/.gitignore"
  git -C "${GIT_SANDBOX}" init -q

  for ignored in \
    ".env" \
    ".env.production" \
    ".agents/ACTIVE_TASK.md" \
    "backend/.agents/.qa-evidence.json" \
    "backend/.venv/pyvenv.cfg" \
    "frontend/node_modules/pkg/index.js" \
    "frontend/dist/index.html" \
    "backend/qa.db-wal" \
    "zap-report.html" \
    "sbom.cyclonedx.json" \
    "trivy-results.sarif" \
    "graphify-out/graph.json" \
    "frontend/reports/mutation.html" \
    "error.log" \
    "archivo.swp"; do
    run git -C "${GIT_SANDBOX}" check-ignore -q "${ignored}"
    assert_success
  done

  for tracked in \
    ".env.example" \
    ".agents/ACTIVE_TASK.md.example" \
    "backend/zap.yaml" \
    "backend/alembic/env.py" \
    "limpieza.sh" \
    "scripts/limpieza.sh" \
    "test/limpieza.bats"; do
    run git -C "${GIT_SANDBOX}" check-ignore -q "${tracked}"
    assert_failure
  done
}
