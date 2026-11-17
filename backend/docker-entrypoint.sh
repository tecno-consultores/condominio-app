#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
# Propósito: Entrypoint y healthcheck unificado consciente de rol (CONTAINER_ROLE=api|worker).

set -euo pipefail

ROLE="${CONTAINER_ROLE:-api}"

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  echo "Uso: docker-entrypoint.sh [--healthcheck|<comando...>]"
  exit 0
fi

if [ "${1:-}" = "--healthcheck" ]; then
  case "${ROLE}" in
    worker)
      exec python -m src.worker --check-health
      ;;
    api)
      exec python -c "import http.client, os; p=int(os.getenv('PORT','8000')); c=http.client.HTTPConnection('127.0.0.1', p, timeout=3); c.request('GET', '/health'); r=c.getresponse(); raise SystemExit(0 if r.status == 200 else 1)"
      ;;
    *)
      echo "❌ CONTAINER_ROLE inválido para healthcheck: '${ROLE}'" >&2
      exit 1
      ;;
  esac
fi

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

case "${ROLE}" in
  worker)
    exec python -m src.worker
    ;;
  api)
    exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers
    ;;
  *)
    echo "❌ CONTAINER_ROLE inválido: '${ROLE}' (use 'api' o 'worker')." >&2
    exit 1
    ;;
esac
