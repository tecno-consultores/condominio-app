# ⚙️ Especificación 12: Gobernanza Thin-Repo, Infraestructura Productiva Docker, Worker Real y CI/CD Nivel 11X

**Estado:** Especificación Formal Activa (Hito 16 ejecutándose; Hito 18 planificado)  
**Ecosistema:** `@sinfallas/mcp-qa-11x` (`v2.20.3+`), Docker Multi-Stage, Trivy, Graphify AST (`--code-only`), GitHub Actions y Lefthook  
**Origen de Auditoría:** Diagnóstico integral de gobernanza, despliegue y pipelines CI/CD (2026-11-13)

---

## 1. Gobernanza Thin-Repo v2.20.3 e Higiene del Grafo AST (Hito 16)

### 1.1. Arquitectura Thin-Repo en `.agents/`
- El repositorio adopta la arquitectura **Thin-Repo**: las 5 skills corporativas (`qa-11x-architect`, `qa-11x-docker-certifier`, `docker-trivy-keydb-hardening`, `graphify-ast-navigator`, `refactoring-ui`) y sus reglas canónicas se consumen globalmente desde la instalación `@sinfallas/mcp-qa-11x`, manteniendo en `.agents/rules/` únicamente `domain_condominio_app_rules.md`.
- Todos los scripts locales en `.agents/scripts/` (`certify_task_completion.sh`, `verify_roadmap_consistency.py`, `verify_docs_invariants.py`, `verify_alembic_orm_parity.py`, `verify_zero_orphan_vue_components.py`, `verify_no_orphan_api_endpoints.py`, `verify_topological_health.py`, `inspect_blast_radius.py`, `verify_json_no_duplicate_keys.py`) se sincronizan mediante `npx -y @sinfallas/mcp-qa-11x@latest install-skill --init-agents --include-scripts --reconcile` sin conservar archivos `.bak` ni respaldos en `.agents/backups/`.

### 1.2. Grafo Semántico AST (`--code-only`) Fuera de Git
- Los directorios `graphify-out/`, `backend/graphify-out/` y `frontend/graphify-out/` son artefactos derivados locales excluidos del control de versiones en `.gitignore`.
- La generación y refresco incremental se realiza exclusivamente mediante `./scripts/actualizar-grafos-graphify.sh` sobre contenedores efímeros `sinfallas/remote-graphify:latest` con bandera `--code-only` (evitando contaminar el grafo con encabezados Markdown como `Added`) y corrigiendo automáticamente la propiedad UID/GID del usuario del host.
- Queda prohibido definir servicios daemon HTTP `graphify-mcp` en puerto `:8080` dentro de `docker-compose.qa.yml` (*Zero Background Daemon Rule*).

### 1.3. Supply-Chain Zero-Trust, Scripts No Destructivos y CI/CD
- **Zero-Trust NPM / pnpm (Control `SEC-09`):** raíz (`/.npmrc`) y frontend (`frontend/.npmrc`) declaran explícitamente `ignore-scripts=true` junto a `frontend/pnpm-workspace.yaml` (`dangerouslyAllowAllBuilds: false`).
- **Idempotencia en Karate Labs BDD (`QA-KARATE-IDEMP`):** `backend/test/api_test.feature` prohíbe UUIDs literales estáticos en cabeceras `Idempotency-Key` y en identificadores de registro (`correo`, `cedula`), inyectando siempre `java.util.UUID.randomUUID() + ''` para garantizar re-ejecutabilidad idempotente en paralelo (`threads = 5`).
- **Limpieza Segura (`scripts/limpieza.sh`):** prohíbe exigir `sudo`, prohíbe borrar archivos rastreados como `backend/zap.yaml` y prohíbe ejecutar `docker system prune -af --volumes` en el flujo normal (preservando volúmenes productivos y `graphify-out/{graph.json,GRAPH_REPORT.md,graph.html}`). Normaliza permisos de archivos creados por contenedores con Alpine efímero.
- **Orquestación Uniforme y `Rule Zero`:** se provee un `Makefile` raíz con aliases unificados (`qa-lint`, `qa-unit`, `qa-parity`, `qa-bdd`, `qa-ui-bdd`, `qa-e2e`, `qa-a11y`, `qa-perf`, `qa-lighthouse`, `qa-orphans`, `qa-infra`, `clean`); `backend/Makefile` y `frontend/Makefile` ejecutan todos los validadores Python dentro de contenedores `sinfallas/base-python-uv:3.13`, `qa-unit` en frontend incluye `pnpm run build` y los contenedores Node operan mapeados al UID/GID del usuario sin crear artefactos propiedad de `root`.
- **Lighthouse CI Compatible con ESM:** `frontend/lighthouserc.cjs` reemplaza a `lighthouserc.js` (incompatible con `"type": "module"`) y persiste reportes en disco (`.lighthouseci`) sin subir resultados a `temporary-public-storage`.
- **GitHub Actions y Hooks Endurecidos:** los 3 workflows en `.github/workflows/` declaran `permissions: contents: read`; `00-iac-audit.yml` fija la versión de `aquasecurity/trivy-action` (sin `@master`) y audita `CRITICAL,HIGH` en `config` y `fs` excluyendo `backend/.venv,frontend/node_modules,graphify-out`; `01-ci-backend.yml` ejecuta `ruff check` (sin `--fix`) y `qa-bdd`; y `lefthook.yml` usa rutas reales `backend/` y `frontend/` con `commitlint` en Bash puro sin dependencias en el host.

---

## 2. Infraestructura Productiva Docker Multi-Stage, Worker Real y Respaldos (Hito 18)

> **Objetivo:** Materializar el despliegue productivo documentado en `docs/MANUAL_ADMINISTRADOR_E_INSTALADOR.md` y `docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md` cumpliendo `Trivy HIGH/CRITICAL = 0` y `QA-HEALTH-01`.

### 2.1. Contenedores Multi-Stage No-Root (`backend/Dockerfile` y `frontend/Dockerfile`)
- **`backend/Dockerfile`:**
  - Etapa `builder` con `uv sync --frozen --no-dev` sobre Python 3.13.
  - Etapa `runtime` minimalista con usuario dedicado no-root (`appuser`, UID `10001`), sin herramientas de compilación ni dependencias `dev`, ejecutando `uvicorn src.main:app` (o `python -m src.worker` para el servicio worker) y `HEALTHCHECK` HTTP sobre `/health`.
- **`frontend/Dockerfile` y `frontend/nginx.conf`:**
  - Etapa `builder` Node/pnpm compilando `dist/` mediante `pnpm install --frozen-lockfile && pnpm run build`.
  - Etapa `runtime` basada en Nginx no-root (`nginxinc/nginx-unprivileged:alpine` en puerto `8080`), sirviendo estáticos SPA (`try_files $uri $uri/ /index.html`), proxy inverso `/api/` y `/health` hacia `api:8000` e inyección de cabeceras OSHP (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy`).

### 2.2. Orquestador Productivo (`docker-compose.yml`), `.env.example` y Respaldos
- **`docker-compose.yml` en la raíz:** define la topología completa (`postgres` 17 con volumen persistente, `keydb` multi-hilo con `--requirepass`, `minio` con volumen persistente, `api`, `worker`, `frontend`), redes aisladas (`backend_net` interna y `frontend_net` pública) y `healthcheck`s en cada servicio, sin puertos expuestos de BD ni KeyDB hacia el exterior.
- **`.env.example` de Condominio App:** plantilla con los nombres de variables reales consumidas por el backend (`APP_ENV`, `SECRET_KEY`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL`, `REDIS_URL`, `ALLOWED_ORIGINS`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_BUCKET`).
- **`scripts/backup-diario.sh`:** respaldo cifrado/comprimido no destructivo de PostgreSQL 17 (`pg_dump --format=custom`) y espejo de bucket MinIO (`mc mirror`) con rotación configurable.

### 2.3. Worker Asíncrono Ejecutable y Contrato de Salud (`QA-HEALTH-01`)
- **`backend/src/worker.py` (`python -m src.worker`):**
  - Conversión real de imágenes a AVIF (`Pillow` / `pillow-avif-plugin`) y carga autenticada hacia MinIO S3 (con fallback controlado en pruebas unitarias herméticas).
  - Consumidor asíncrono BLPOP sobre `queue:notifications` en KeyDB con envío SMTP TLS configurable y reintentos acotados.
  - Scheduler diario idempotente para `generar_tareas_diarias_desde_plantillas` respaldado por `UniqueConstraint("plantilla_id", "fecha")` en `TareaDiaria`.
  - Supervisor de tareas `asyncio` que verifica `task.exception()` sin silenciar fallos y actualiza un archivo/clave de *heartbeat* verificable en `HEALTHCHECK` (`QA-HEALTH-01`), certificado mediante prueba de arranque productivo con `Settings` por defecto sin mockear el loop principal.

---

## 3. Contratos de Verificación y Sincronización Documental

- Cada sub-tarea de los Hitos 16 y 18 exige actualización simétrica de `docs/MANUAL_ADMINISTRADOR_E_INSTALADOR.md`, `SECURITY.md`, `ARCHITECTURE.md`, `API_ROUTES.md`, `README.md`, `TESTING.md`, `ROADMAP.md` y `CHANGELOG.md`.
- Los pipelines y scripts deben aprobar `./scripts/verificar-secretos.sh`, `./scripts/auditar-infra.sh` (`HIGH/CRITICAL = 0`), `verify_roadmap_consistency.py`, `verify_docs_invariants.py`, `run_ephemeral_qa` y `certify_11x_gate` (`10/10`).
