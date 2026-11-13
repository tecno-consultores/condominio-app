#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors
# Wrapper unificado hacia scripts/auditar-infra.sh (evita lógica duplicada en la raíz).

LC_ALL=C
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/scripts/auditar-infra.sh" "$@"
