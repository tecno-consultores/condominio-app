#!/usr/bin/env bats
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors
# Suite BATS para certificar scripts/backup-diario.sh (PG17 + MinIO + SHA-256 + rotación + APSC-DV-001090).

REPO_ROOT="$(cd "$(dirname "${BATS_TEST_FILENAME}")/.." && pwd)"

setup() {
  load '/opt/bats-libs/bats-support/load.bash'
  load '/opt/bats-libs/bats-assert/load.bash'

  SANDBOX="${BATS_TEST_TMPDIR}/repo"
  MOCK_BIN="${BATS_TEST_TMPDIR}/bin"
  BACKUP_DEST="${BATS_TEST_TMPDIR}/backups"

  mkdir -p "${SANDBOX}/scripts" "${MOCK_BIN}" "${BACKUP_DEST}"
  cp "${REPO_ROOT}/scripts/backup-diario.sh" "${SANDBOX}/scripts/backup-diario.sh"
  chmod +x "${SANDBOX}/scripts/backup-diario.sh"
  touch "${SANDBOX}/docker-compose.yml"

  cat >"${MOCK_BIN}/docker" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = "compose" ]; then
  printf 'PGDMP_SIMULADO_CONDOMINIO_APP\n'
  exit 0
fi
if [ "${1:-}" = "run" ]; then
  for arg in "$@"; do
    case "${arg}" in
      *:/backup_out)
        host_dir="${arg%:/backup_out}"
        mkdir -p "${host_dir}/incidencias"
        printf 'avif-simulado' >"${host_dir}/incidencias/foto.avif"
        ;;
    esac
  done
  exit 0
fi
exit 0
EOF
  chmod +x "${MOCK_BIN}/docker"
}

@test "backup-diario.sh --help imprime instrucciones y retorna 0" {
  run bash "${SANDBOX}/scripts/backup-diario.sh" --help
  assert_success
  assert_output --partial "Uso: ./scripts/backup-diario.sh"
}

@test "backup-diario.sh rechaza días de retención no numéricos" {
  run bash "${SANDBOX}/scripts/backup-diario.sh" --backup-dir "${BACKUP_DEST}" --retention-days abc
  assert_failure
  assert_output --partial "BACKUP_RETENTION_DAYS debe ser un entero no negativo"
}

@test "backup-diario.sh genera pg17 y minio comprimidos con sha256 y rota antiguos" {
  touch -d "45 days ago" "${BACKUP_DEST}/pg17_19990101_000000.dump.gz"

  run env -u BACKUP_PASSPHRASE PATH="${MOCK_BIN}:${PATH}" \
    bash "${SANDBOX}/scripts/backup-diario.sh" --backup-dir "${BACKUP_DEST}" --retention-days 30
  assert_success
  assert_output --partial "[Backup 11X] Respaldos generados:"

  [ ! -e "${BACKUP_DEST}/pg17_19990101_000000.dump.gz" ]

  pg_dump_file=$(find "${BACKUP_DEST}" -maxdepth 1 -name 'pg17_*.dump.gz' | head -n 1)
  minio_tar_file=$(find "${BACKUP_DEST}" -maxdepth 1 -name 'minio_*.tar.gz' | head -n 1)
  [ -f "${pg_dump_file}" ]
  [ -f "${pg_dump_file}.sha256" ]
  [ -f "${minio_tar_file}" ]
  [ -f "${minio_tar_file}.sha256" ]

  run sha256sum -c "${pg_dump_file}.sha256"
  assert_success
  run sha256sum -c "${minio_tar_file}.sha256"
  assert_success
}

@test "backup-diario.sh cifra con AES-256-PBKDF2 y emite alerta de disco >= 75%" {
  if ! command -v openssl >/dev/null 2>&1; then
    skip "openssl no disponible en la imagen base"
  fi

  cat >"${MOCK_BIN}/df" <<'EOF'
#!/usr/bin/env bash
printf 'Filesystem 1024-blocks Used Available Capacity Mounted on\n'
printf '/dev/sda1 1000000 820000 180000 82%% /var/backups\n'
EOF
  chmod +x "${MOCK_BIN}/df"

  cat >"${SANDBOX}/.env" <<'EOF'
BACKUP_PASSPHRASE=clave-cifrado-test-11x
POSTGRES_USER=condominio_admin
POSTGRES_DB=condominio_db
MINIO_ROOT_USER=condominio_minio
MINIO_ROOT_PASSWORD=minio_pass_placeholder
MINIO_BUCKET=condominio-media
EOF

  run env PATH="${MOCK_BIN}:${PATH}" \
    bash "${SANDBOX}/scripts/backup-diario.sh" --backup-dir "${BACKUP_DEST}"
  assert_success
  assert_output --partial "APSC-DV-001090"

  pg_enc_file=$(find "${BACKUP_DEST}" -maxdepth 1 -name 'pg17_*.dump.gz.enc' | head -n 1)
  [ -f "${pg_enc_file}" ]
  [ -f "${pg_enc_file}.sha256" ]
}
