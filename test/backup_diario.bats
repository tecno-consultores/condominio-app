#!/usr/bin/env bats
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
# Suite BATS para certificar scripts/backup-diario.sh (PG17 + MinIO + SSL + SHA-256 + trap + 0-byte).

REPO_ROOT="$(cd "$(dirname "${BATS_TEST_FILENAME}")/.." && pwd)"

setup() {
  load '/opt/bats-libs/bats-support/load.bash'
  load '/opt/bats-libs/bats-assert/load.bash'

  SANDBOX="${BATS_TEST_TMPDIR}/repo"
  MOCK_BIN="${BATS_TEST_TMPDIR}/bin"
  BACKUP_DEST="${BATS_TEST_TMPDIR}/backups"
  MC_ENV_LOG="${BATS_TEST_TMPDIR}/mc_env.log"

  mkdir -p "${SANDBOX}" "${MOCK_BIN}" "${BACKUP_DEST}"
  touch "${SANDBOX}/docker-compose.yml"

  cat >"${MOCK_BIN}/docker" <<EOF
#!/usr/bin/env bash
if [ "\${1:-}" = "compose" ]; then
  if [ "\${MOCK_PG_EMPTY:-0}" = "1" ]; then
    exit 0
  fi
  printf 'PGDMP_SIMULADO_CONDOMINIO_APP\n'
  exit 0
fi
if [ "\${1:-}" = "run" ]; then
  printf '%s\n' "\${MC_HOST_prod:-}" > "${MC_ENV_LOG}"
  if [ "\${MOCK_MC_FAIL:-0}" = "1" ]; then
    echo "MinIO connection refused" >&2
    exit 1
  fi
  for arg in "\$@"; do
    case "\${arg}" in
      *:/backup_out)
        host_dir="\${arg%:/backup_out}"
        mkdir -p "\${host_dir}/incidencias"
        printf 'avif-simulado' >"\${host_dir}/incidencias/foto.avif"
        ;;
    esac
  done
  exit 0
fi
exit 0
EOF
  chmod +x "${MOCK_BIN}/docker"
}

@test "backup-diario.sh --help y validacion de argumentos invalidos" {
  run env QA_REPO_ROOT="${SANDBOX}" bash "${REPO_ROOT}/scripts/backup-diario.sh" --help
  assert_success
  assert_output --partial "Uso: ./scripts/backup-diario.sh"

  run env QA_REPO_ROOT="${SANDBOX}" bash "${REPO_ROOT}/scripts/backup-diario.sh" --backup-dir
  assert_failure
  assert_output --partial "--backup-dir requiere un argumento"

  run env QA_REPO_ROOT="${SANDBOX}" bash "${REPO_ROOT}/scripts/backup-diario.sh" --retention-days
  assert_failure
  assert_output --partial "--retention-days requiere un argumento"

  run env QA_REPO_ROOT="${SANDBOX}" bash "${REPO_ROOT}/scripts/backup-diario.sh" --desconocida
  assert_failure
  assert_output --partial "Opción desconocida"

  run env QA_REPO_ROOT="${SANDBOX}" bash "${REPO_ROOT}/scripts/backup-diario.sh" \
    --backup-dir "${BACKUP_DEST}" --retention-days abc
  assert_failure
  assert_output --partial "BACKUP_RETENTION_DAYS debe ser un entero no negativo"
}

@test "backup-diario.sh genera pg17 y minio comprimidos con sha256 y rota antiguos" {
  touch -d "45 days ago" "${BACKUP_DEST}/pg17_19990101_000000.dump.gz"

  run env -u BACKUP_PASSPHRASE QA_REPO_ROOT="${SANDBOX}" PATH="${MOCK_BIN}:${PATH}" \
    bash "${REPO_ROOT}/scripts/backup-diario.sh" --backup-dir "${BACKUP_DEST}" --retention-days 30
  assert_success
  assert_output --partial "[Backup 11X] Respaldos generados:"

  [ ! -e "${BACKUP_DEST}/pg17_19990101_000000.dump.gz" ]

  pg_dump_file=$(find "${BACKUP_DEST}" -maxdepth 1 -name 'pg17_*.dump.gz' | head -n 1)
  minio_tar_file=$(find "${BACKUP_DEST}" -maxdepth 1 -name 'minio_*.tar.gz' | head -n 1)
  [ -s "${pg_dump_file}" ]
  [ -s "${pg_dump_file}.sha256" ]
  [ -s "${minio_tar_file}" ]
  [ -s "${minio_tar_file}.sha256" ]

  run sha256sum -c "${pg_dump_file}.sha256"
  assert_success
  run sha256sum -c "${minio_tar_file}.sha256"
  assert_success
}

@test "backup-diario.sh cifra con AES-256-PBKDF2, respeta MINIO_USE_SSL=true y alerta disco >= 75%" {
  cat >"${MOCK_BIN}/df" <<'EOF'
#!/usr/bin/env bash
printf 'Filesystem 1024-blocks Used Available Capacity Mounted on\n'
printf '/dev/sda1 1000000 820000 180000 82%% /var/backups\n'
EOF
  chmod +x "${MOCK_BIN}/df"

  cat >"${SANDBOX}/.env" <<'EOF'
# Configuracion de prueba con linea vacia

BACKUP_PASSPHRASE=clave-cifrado-test-11x
POSTGRES_USER=condominio_admin
POSTGRES_DB=condominio_db
MINIO_ROOT_USER=condominio_minio
MINIO_ROOT_PASSWORD=minio_pass_placeholder
MINIO_BUCKET=condominio-media
MINIO_ENDPOINT=http://minio:9000
MINIO_USE_SSL=true
EOF

  run env QA_REPO_ROOT="${SANDBOX}" PATH="${MOCK_BIN}:${PATH}" \
    bash "${REPO_ROOT}/scripts/backup-diario.sh" -q --backup-dir "${BACKUP_DEST}"
  assert_success
  assert_output --partial "APSC-DV-001090"

  pg_enc_file=$(find "${BACKUP_DEST}" -maxdepth 1 -name 'pg17_*.dump.gz.enc' | head -n 1)
  [ -s "${pg_enc_file}" ]
  [ -s "${pg_enc_file}.sha256" ]

  run cat "${MC_ENV_LOG}"
  assert_output --partial "https://condominio_minio:minio_pass_placeholder@minio:9000"
}

@test "backup-diario.sh aborta ante salida 0-byte de pg_dump o fallo de mc mirror y purga parciales en trap" {
  run env -u BACKUP_PASSPHRASE QA_REPO_ROOT="${SANDBOX}" MOCK_PG_EMPTY=1 PATH="${MOCK_BIN}:${PATH}" \
    bash "${REPO_ROOT}/scripts/backup-diario.sh" --backup-dir "${BACKUP_DEST}"
  assert_failure
  assert_output --partial "salida vacía (0 bytes)"
  [ "$(find "${BACKUP_DEST}" -maxdepth 1 -type f | wc -l)" -eq 0 ]

  run env -u BACKUP_PASSPHRASE QA_REPO_ROOT="${SANDBOX}" MOCK_MC_FAIL=1 PATH="${MOCK_BIN}:${PATH}" \
    bash "${REPO_ROOT}/scripts/backup-diario.sh" --backup-dir "${BACKUP_DEST}"
  assert_failure
  assert_output --partial "MinIO connection refused"
  [ "$(find "${BACKUP_DEST}" -maxdepth 1 -type f | wc -l)" -eq 0 ]
}

@test "backup-diario.sh falla limpiamente si BACKUP_PASSPHRASE se define sin openssl" {
  NO_SSL_BIN="${BATS_TEST_TMPDIR}/no_ssl_bin"
  mkdir -p "${NO_SSL_BIN}"
  cp "${MOCK_BIN}/docker" "${NO_SSL_BIN}/docker"
  for cmd in bash dirname mkdir chmod df awk find wc date gzip rm tar sha256sum tr basename; do
    cmd_path="$(command -v "${cmd}" || true)"
    [ -n "${cmd_path}" ] && ln -sf "${cmd_path}" "${NO_SSL_BIN}/${cmd}"
  done

  run env BACKUP_PASSPHRASE="clave-sin-openssl" QA_REPO_ROOT="${SANDBOX}" PATH="${NO_SSL_BIN}" \
    bash "${REPO_ROOT}/scripts/backup-diario.sh" --backup-dir "${BACKUP_DEST}"
  assert_failure
  assert_output --partial "openssl no está disponible"
}

@test "backup-diario.sh aborta si gzip o sha256sum produce archivo de 0 bytes" {
  cat >"${MOCK_BIN}/gzip" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
  chmod +x "${MOCK_BIN}/gzip"

  run env -u BACKUP_PASSPHRASE QA_REPO_ROOT="${SANDBOX}" PATH="${MOCK_BIN}:${PATH}" \
    bash "${REPO_ROOT}/scripts/backup-diario.sh" --backup-dir "${BACKUP_DEST}"
  assert_failure
  assert_output --partial "está vacío (0 bytes)"
}
