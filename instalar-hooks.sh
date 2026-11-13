#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors
# Propósito: Inicializar hooks de Git con Lefthook sin contaminar el workspace (Rule Zero).

LC_ALL=C
set -euo pipefail

echo "🛡️ Configurando Barrera de Entrada Corporativa (Lefthook + Conventional Commits Bash)..."
echo "ℹ️  Las validaciones pre-commit, commit-msg y pre-push se ejecutan efímeramente vía Docker o Bash puro."

if ! command -v lefthook >/dev/null 2>&1; then
  echo "❌ [ERROR] 'lefthook' no está instalado en el PATH del sistema." >&2
  echo "💡 Instálelo de forma global (sin npm install local) desde https://github.com/evilmartians/lefthook/releases o con su gestor de paquetes del SO (p. ej. brew/apt/go)." >&2
  exit 1
fi

lefthook install
echo "✅ ¡Barrera activada! Todo 'git commit' y 'git push' será auditado automáticamente."
exit 0
