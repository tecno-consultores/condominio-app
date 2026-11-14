# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors
# Dockerfile multi-stage productivo no-root para API FastAPI y Worker asíncrono (Estándar QA 11X).

FROM sinfallas/base-python-uv:3.13 AS builder

ENV HOME=/tmp \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

USER 0
RUN mkdir -p /opt/venv /build && chown 10001:10001 /opt/venv /build
USER 10001:10001

WORKDIR /build

COPY --chown=10001:10001 pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=10001:10001 alembic.ini ./
COPY --chown=10001:10001 alembic ./alembic
COPY --chown=10001:10001 src ./src

FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    HOME=/tmp \
    TMPDIR=/tmp \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
        /usr/local/lib/python3.13/site-packages/pip* \
        /usr/local/lib/python3.13/ensurepip \
        /usr/local/bin/pip* \
    && groupadd -g 10001 appgroup \
    && useradd -u 10001 -g appgroup -s /usr/sbin/nologin -d /app -M appuser

COPY --from=builder --chown=10001:10001 /opt/venv /opt/venv
COPY --from=builder --chown=10001:10001 /build /app

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import http.client; c=http.client.HTTPConnection('127.0.0.1', 8000, timeout=3); c.request('GET', '/health'); r=c.getresponse(); raise SystemExit(0 if r.status == 200 else 1)"]

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
