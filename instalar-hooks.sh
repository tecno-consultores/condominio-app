#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
# Propósito: Instalar hooks Git locales con ejecución efímera Docker (Rule Zero, sin binario lefthook en host).

LC_ALL=C
set -euo pipefail

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  echo "Uso: ./instalar-hooks.sh"
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${QA_REPO_ROOT:-${SCRIPT_DIR}}"
HOOKS_DIR="${REPO_ROOT}/.git/hooks"
NODE_QA_IMAGE="${QA_NODE_IMAGE:-sinfallas/base-node-ionic:26@sha256:275f3d8bbfef87f4e836e4f77d92c0d199821154079b050eaef53ce33ae6de60}"

if [ ! -d "${HOOKS_DIR}" ]; then
  echo "❌ [ERROR] No existe el directorio '${HOOKS_DIR}'. Inicializa Git primero." >&2
  exit 1
fi

cat >"${HOOKS_DIR}/pre-commit" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "${REPO_ROOT}"
./scripts/verificar-secretos.sh
EOF

cat >"${HOOKS_DIR}/commit-msg" <<EOF
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="\$(git rev-parse --show-toplevel)"
MSG_FILE="\$1"
docker run --rm -i \\
  -u "\$(id -u):\$(id -g)" \\
  -e HOME=/tmp \\
  -v "\${REPO_ROOT}:/repo:ro" \\
  -v "condominio_hooks_pnpm:/pnpm" \\
  -w /tmp \\
  "${NODE_QA_IMAGE}" \\
  bash -c 'mkdir -p /tmp/cl && cp /repo/package.json /repo/pnpm-lock.yaml /repo/commitlint.config.js /tmp/cl/ && cd /tmp/cl && pnpm_config_store_dir=/pnpm pnpm install --frozen-lockfile --ignore-scripts --silent && ./node_modules/.bin/commitlint --config /tmp/cl/commitlint.config.js' <"\${MSG_FILE}"
EOF

cat >"${HOOKS_DIR}/pre-push" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "${REPO_ROOT}"
./scripts/auditar-infra.sh
EOF

chmod 0755 "${HOOKS_DIR}/pre-commit" "${HOOKS_DIR}/commit-msg" "${HOOKS_DIR}/pre-push"
echo "✅ Hooks Git efímeros (pre-commit, commit-msg con commitlint Docker, pre-push Trivy) instalados en ${HOOKS_DIR}."
exit 0
