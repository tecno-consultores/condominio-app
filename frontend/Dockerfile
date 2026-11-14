# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors
# Dockerfile multi-stage productivo no-root para SPA Vue 3 + Nginx endurecido (Estándar QA 11X).

FROM sinfallas/base-node-ionic:26 AS builder

ENV HOME=/tmp \
    pnpm_config_store_dir=/tmp/pnpm-store

WORKDIR /tmp/build

COPY --chown=10001:10001 .npmrc package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile --ignore-scripts

COPY --chown=10001:10001 index.html tsconfig.json vite.config.ts ./
COPY --chown=10001:10001 src ./src
RUN pnpm run build

FROM nginx:1.27-alpine AS runtime

RUN apk upgrade --no-cache \
    && rm -rf /etc/nginx/conf.d/default.conf /docker-entrypoint.d/* \
    && sed -i 's|/var/run/nginx.pid|/tmp/nginx.pid|g; s|/run/nginx.pid|/tmp/nginx.pid|g' /etc/nginx/nginx.conf \
    && sed -i '/^user /d' /etc/nginx/nginx.conf \
    && mkdir -p /var/cache/nginx /var/log/nginx /tmp/nginx_client_temp /tmp/nginx_proxy_temp \
    && chown -R 101:101 /var/cache/nginx /var/log/nginx /etc/nginx/conf.d /usr/share/nginx/html /tmp/nginx_client_temp /tmp/nginx_proxy_temp

COPY --chown=101:101 nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder --chown=101:101 /tmp/build/dist /usr/share/nginx/html

USER 101:101

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/nginx-health"]

CMD ["nginx", "-g", "daemon off;"]
