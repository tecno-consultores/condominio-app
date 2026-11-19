# 🏢 Condominio App

[![Licencia: MIT](https://img.shields.io/badge/Licencia-MIT-blue.svg)](./LICENSE)
[![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](./backend/README.md)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](./backend/README.md)
[![Vue 3](https://img.shields.io/badge/Frontend-Vue%203-4FC08D?logo=vuedotjs&logoColor=white)](./frontend/README.md)
[![PostgreSQL 17](https://img.shields.io/badge/PostgreSQL-17%20RLS-4169E1?logo=postgresql&logoColor=white)](./docs/specs/11_ENDURECIMIENTO_BACKEND_CONCURRENCIA_Y_SEGURIDAD_REAL.md)
[![KeyDB](https://img.shields.io/badge/Cache%20%26%20Colas-KeyDB%20Multi--Hilo-D82C20?logo=redis&logoColor=white)](./docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md)
[![QA 11X](https://img.shields.io/badge/Certificaci%C3%B3n-QA%2011X%20Rule%20Zero-16A34A)](./docs/qa/README.md)
[![Docker Hub Multi-Arch](https://img.shields.io/badge/Docker%20Hub-amd64%20%7C%20arm64-2496ED?logo=docker&logoColor=white)](./docker-compose.prod.yml)

**Versión Oficial:** `v1.1.0` (Fase 7 completada) · **Licencia:** MIT · **Gobernanza:** `@sinfallas/mcp-qa-11x` `v3.1.0`

**Condominio App** es una plataforma de código abierto diseñada para administrar condominios, edificios y urbanizaciones bajo el estándar corporativo **QA Nivel 11X**. Resuelve en una arquitectura modular **Mobile-First** la cobranza multimoneda (`USD`/`VES` con tasa BCV), facturación trimodal LPH por alícuotas (Método de Hamilton), certificados digitales de solvencia e inmutabilidad del **Candado Contable**, Cartas Consulta (Art. 23 LPH) y Asambleas con voto ponderado firmado con `HMAC-SHA256`, pases de visita QR anti-replay en KeyDB, trazabilidad de paquetería en garita, reserva de áreas sociales sujeta a solvencia, activación controlada de residentes (**Usuarios Fantasma**), embudo vecinal de incidencias ("¡Me sumo!") y checklist diario de conserjería.

---

## 🐳 Despliegue Rápido con Docker Hub (`Single-Condo`)

Opere una instancia aislada por comunidad en servidores `linux/amd64` o `linux/arm64` sin compilar código fuente local, consumiendo las imágenes oficiales no-root **`sinfallas/condominio-backend`** (`CONTAINER_ROLE=api|worker`) y **`sinfallas/condominio-frontend`** (`nginx:1.27-alpine`, puerto `8080`) mediante [`docker-compose.prod.yml`](./docker-compose.prod.yml):

```bash
# 1. Copiar la plantilla productiva y restringir permisos
cp .env.example .env && chmod 600 .env
# Edite .env generando claves únicas con `openssl rand -hex 32` para SECRET_KEY,
# POSTGRES_PASSWORD, POSTGRES_APP_PASSWORD, KEYDB_PASSWORD, MINIO_ROOT_PASSWORD y ALLOWED_ORIGINS.

# 2. Descargar imágenes multi-arch firmadas y levantar la topología completa
docker compose -f docker-compose.prod.yml up -d

# 3. Aplicar migraciones PostgreSQL 17 (incluyendo RLS 0010) e inicializar Día 0 (sin exponer clave en CLI)
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
docker compose -f docker-compose.prod.yml exec -e BOOTSTRAP_ADMIN_PASSWORD="CHANGE_ME_CONTRASENA_SEGURA_MIN_12" api \
  python -m src.bootstrap --from-env
```

> [!NOTE]
> Para compilar desde fuentes locales utilice [`docker-compose.yml`](./docker-compose.yml). La guía operativa paso a paso, configuración TLS y restauración de respaldos se detalla en [`docs/MANUAL_ADMINISTRADOR_E_INSTALADOR.md`](./docs/MANUAL_ADMINISTRADOR_E_INSTALADOR.md).

---

## 🚀 Stack Tecnológico y Componentes

| Capa | Tecnología | Documentación del Componente |
| :--- | :--- | :--- |
| **Backend API & Worker** | FastAPI (Python `3.13`), SQLAlchemy `2.0` Async, Alembic (`0001..0010`), Radon Grado A, Worker AVIF/SMTP (`BLMOVE` + DLQ) | [`backend/README.md`](./backend/README.md) · [`backend/TESTING.md`](./backend/TESTING.md) |
| **Frontend GUI** | Vue `3.5` (`<script setup lang="ts">`), TypeScript Strict, Pinia `2`, Vue Router `4`, Tokens `OKLCH` + `light-dark()`, Nginx `1.27` no-root | [`frontend/README.md`](./frontend/README.md) · [`frontend/TESTING.md`](./frontend/TESTING.md) |
| **Persistencia & Estado** | PostgreSQL `17` con `ENABLE`/`FORCE ROW LEVEL SECURITY` en `27` tablas, KeyDB Multi-Hilo (`--server-threads 2`), MinIO S3 | [`docs/specs/11_ENDURECIMIENTO_BACKEND_CONCURRENCIA_Y_SEGURIDAD_REAL.md`](./docs/specs/11_ENDURECIMIENTO_BACKEND_CONCURRENCIA_Y_SEGURIDAD_REAL.md) |
| **Seguridad & Gobernanza** | Thin-Repo `.agents/` + `@sinfallas/mcp-qa-11x` `v3.1.0`, FINOS CALM `1.2`, Graphify AST `--code-only`, **22 vectores** mitigados | [`SECURITY.md`](./SECURITY.md) · [`docs/qa/README.md`](./docs/qa/README.md) |

---

## 📁 Estructura del Repositorio (Thin-Repo)

```text
condominio-app/
├── .agents/                # Gobernanza Thin-Repo v3.1.0 (reglas de dominio y scripts de compuerta 10/10)
├── .github/workflows/      # Pipelines CI/CD con pinning SHA-40 y publicación Docker Hub Multi-Arch
├── architecture/           # Modelo FINOS CALM 1.2 (qa-11x.calm.json, 7 controles obligatorios 11X)
├── artifacts/sbom/         # Inventario CycloneDX generado por scripts/generar-sbom-cyclonedx.sh (ignorado en git)
├── backend/                # API FastAPI (9 routers, 27 tablas ORM) + Worker Unificado + README.md / TESTING.md
├── frontend/               # GUI Vue 3 Mobile-First (44 componentes .vue, Screenplay E2E) + README.md / TESTING.md
├── docs/
│   ├── qa/                 # Guía Thin-Repo de la pirámide de 13 capas QA 11X (README.md)
│   ├── specs/              # Especificaciones técnicas de Dominio, Seguridad, UX/UI y Remediación (01..13)
│   ├── ARCHITECTURE.md     # Visión general de roles y máquinas de estado
│   ├── API_ROUTES.md       # Mapa de vistas GUI y endpoints REST
│   ├── MANUAL_ADMINISTRADOR_E_INSTALADOR.md
│   └── MANUAL_USUARIO_RESIDENTE.md
├── scripts/                # Scripts operativos (verificar-secretos, auditar-infra, limpieza, backup-diario, sbom, graphify)
├── test/                   # 10 suites BATS 11X con cobertura kcov >= 95%
├── Makefile                # Orquestación unificada QA 11X (Rule Zero)
├── docker-compose.yml      # Stack de compilación local no-root endurecido
├── docker-compose.prod.yml # Despliegue productivo directo desde Docker Hub multi-arch
├── AGENTS.md               # Directivas supremas para agentes de IA y desarrolladores
├── SECURITY.md             # Política de seguridad y catálogo de 22 vectores mitigados
├── TESTING.md              # Bitácora maestra de certificación QA 11X
├── ROADMAP.md              # Plan maestro de hitos (Hitos 1..26)
└── CHANGELOG.md            # Historial semántico de cambios
```

---

## 🧪 Calidad y Seguridad (Estándar Nivel 11X — `Rule Zero`)

Toda validación corre en **contenedores Docker efímeros** (`sinfallas/*`), sin instalar dependencias en el host. Consulte el detalle completo en [`docs/qa/README.md`](./docs/qa/README.md), [`backend/README.md`](./backend/README.md) y [`frontend/README.md`](./frontend/README.md):

```bash
# Auditoría raíz (Secretos, Trivy IaC/FS, Bash/BATS kcov >= 95%, FINOS CALM 1.2)
make qa-secrets qa-infra qa-bash qa-calm

# Gates del Backend (FastAPI, Radon Grado A, PostgreSQL 17 RLS, Mutmut, Karate API, Schemathesis, ZAP, Caos)
make -C backend qa-lint qa-complexity qa-deps qa-unit qa-parity qa-bdd

# Gates del Frontend (0 Huérfanos, SonarJS <= 15, Vitest >= 95%, Stryker, Playwright WCAG AA, Lighthouse, Karate UI)
make -C frontend qa-orphans qa-lint qa-unit qa-e2e qa-perf qa-bdd

# Certificación integral de cierre (10 etapas) y limpieza segura de contenedores *.qa.yml
make certify
./scripts/limpieza.sh --quiet
```

---

## 📚 Documentación, Especificaciones y Manuales

- 📐 **[`docs/specs/README.md`](./docs/specs/README.md)** — Catálogo maestro de las 13 especificaciones (`01..13`) y mapa de trazabilidad GUI ↔ API.
- 🛡️ **[`docs/qa/README.md`](./docs/qa/README.md)** — Guía Thin-Repo de las 13 capas QA 11X, FINOS CALM `1.2` y Graphify AST `--code-only`.
- 🔐 **[`SECURITY.md`](./SECURITY.md)** — Política de divulgación responsable y los **22 vectores** de seguridad híbrida mitigados.
- ⚡ **[`backend/README.md`](./backend/README.md)** — Arquitectura, invariantes (Radon Grado A, 27 tablas, 9 routers, PG17 RLS, Worker) y gates del Backend.
- 🎨 **[`frontend/README.md`](./frontend/README.md)** — Arquitectura, tokens `OKLCH` + `light-dark()`, Screenplay E2E, Stryker, Lighthouse y Karate UI.
- 📘 **[`docs/MANUAL_ADMINISTRADOR_E_INSTALADOR.md`](./docs/MANUAL_ADMINISTRADOR_E_INSTALADOR.md)** — Manual técnico de instalación, TLS, respaldos y administración de Junta.
- 🏡 **[`docs/MANUAL_USUARIO_RESIDENTE.md`](./docs/MANUAL_USUARIO_RESIDENTE.md)** — Guía práctica para propietarios, inquilinos y conserjes.
- 🗺️ **[`ROADMAP.md`](./ROADMAP.md)** · **[`TESTING.md`](./TESTING.md)** · **[`CHANGELOG.md`](./CHANGELOG.md)** · **[`AGENTS.md`](./AGENTS.md)**

---

## 📄 Licencia y Autoría

**Copyright (C) 2026 Jesús Palencia `<sinfallas@gmail.com>` (Creado en Tecno Consultores)**

Este proyecto es Software Libre distribuido bajo los términos de la licencia **MIT**. Consulte [`LICENSE`](./LICENSE) y [`AUTHORS.md`](./AUTHORS.md) para más detalles.
