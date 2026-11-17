# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
# Dockerfile multi-stage productivo no-root multi-arch para API FastAPI y Worker (CONTAINER_ROLE=api|worker).

FROM sinfallas/base-python-uv:3.13@sha256:1594cbb33269c6a535a8ae5242b07a5866aa519d00975868f0a0d03fdc3bc155 AS uv-bin

FROM python:3.13-slim-bookworm AS builder

COPY --from=uv-bin /usr/local/bin/uv /usr/local/bin/uv

ENV HOME=/tmp \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_PREFERENCE=only-system \
    UV_PROJECT_ENVIRONMENT=/opt/venv

RUN groupadd -g 10001 appgroup \
    && useradd -u 10001 -g appgroup -s /usr/sbin/nologin -d /build -M appbuilder \
    && mkdir -p /opt/venv /build \
    && chown 10001:10001 /opt/venv /build

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
    PATH="/opt/venv/bin:${PATH}" \
    CONTAINER_ROLE=api

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
COPY --chown=10001:10001 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["/usr/local/bin/docker-entrypoint.sh", "--healthcheck"]

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
