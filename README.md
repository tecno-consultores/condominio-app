# 🏢 Condominio App

**Versión Oficial:** `v1.0.0` · **Licencia:** MIT · **Certificación:** Estándar Corporativo QA Nivel 11X

**Condominio App** es una plataforma de código abierto (MIT) diseñada para modernizar y transparentar la administración de condominios, edificios y urbanizaciones bajo el estándar corporativo **Gobernanza y Calidad Nivel 11X**.

Construida con una arquitectura modular **Mobile-First**, resuelve los problemas críticos de la gestión condominal: control de pagos multimoneda (USD / VES con tasa BCV), facturación trimodal LPH por alícuotas (Método de Hamilton), certificados digitales de solvencia e inmutabilidad del **Candado Contable**, Cartas Consulta (Art. 23 LPH) y Asambleas con voto ponderado firmado con `HMAC-SHA256`, Pases de Visita QR con protección Anti-Replay en KeyDB, trazabilidad de paquetería en garita, reserva de áreas sociales vinculada a Solvencia Estricta e inspección post-evento automática, auditoría forense de rechazos, activación controlada de residentes (**Usuarios Fantasma**), embudo vecinal de incidencias ("¡Me sumo!") y checklist diario de conserjería.

---

## 🚀 Tecnologías Principales

- **Backend:** FastAPI (Python 3.13) + SQLAlchemy 2.0 Async + Alembic + PostgreSQL 17
- **Motor en Memoria (Idempotencia, Rate-Limiting & Colas):** KeyDB Multi-Hilo (`eqalpha/keydb:alpine --server-threads 2`)
- **Frontend:** Vue 3 (`<script setup lang="ts">`) + Pinia + Vue Router + CSS Nativo con Tokens `OKLCH` y `light-dark()` (Mobile-First, Anti-JSDOM Layout & WCAG 2.1 AA)
- **Almacenamiento Multimedia:** MinIO (S3 Compatible) con conversión asíncrona a formato AVIF y lectura segura por chunks ($\le 2\text{ MB}$)
- **Gobernanza IA & QA 11X:** Ecosistema Thin-Repo `.agents/` + `@sinfallas/mcp-qa-11x` (`Rule Zero`: 100% contenedores Docker efímeros `sinfallas/*`)

---

## 📁 Estructura del Repositorio

```text
condominio-app/
├── .agents/                # Gobernanza IA Nivel 11X (rules y scripts de certificación Thin-Repo v3.1.0)
├── architecture/           # Modelo arquitectónico FINOS CALM 1.2 (qa-11x.calm.json, 7 controles 11X)
├── artifacts/sbom/         # Inventario CycloneDX generado por scripts/generar-sbom-cyclonedx.sh (ignorado en git)
├── backend/                # API FastAPI + Worker Unificado (CONTAINER_ROLE=api|worker)
│   ├── src/                # Código fuente (models, schemas, routers, finanzas, security, redis_client, worker, bootstrap)
│   ├── tests/              # Suites unitarias aisladas (test_*.unit.py, cobertura >= 95%)
│   ├── test/               # Escenarios BDD Gherkin (Karate Labs: api_test.feature)
│   ├── alembic/            # Migraciones verificadas contra PostgreSQL 17 real
│   ├── Dockerfile          # Build multi-stage Python 3.13 --no-dev multi-arch no-root (UID/GID 10001)
│   ├── docker-entrypoint.sh # Entrypoint y HEALTHCHECK consciente de rol (api | worker)
│   ├── Makefile            # Orquestación de gates QA efímeros en Docker
│   ├── docker-compose.qa.yml
│   └── TESTING.md          # Bitácora detallada de pruebas del backend
├── frontend/               # GUI Vue 3 Mobile-First + Seguridad Cliente 11X (Fase 2)
│   ├── src/                # Componentes Anti-JSDOM, vistas, stores Pinia no destructivos, router RBAC y apiClient
│   ├── test/               # Escenarios BDD UI Gherkin (Karate Labs: ui_business_flow.feature)
│   ├── e2e/                # Auditoría E2E y accesibilidad WCAG 2.1 AA (Playwright + axe-core)
│   ├── Dockerfile          # Build multi-stage Vue 3 + nginx:1.27-alpine multi-arch no-root (UID/GID 101, puerto 8080)
│   ├── nginx.conf          # Proxy inverso /api + /health + /ws + cabeceras OSHP/STIG
│   ├── Makefile            # Orquestación de gates QA frontend en Docker efímero
│   ├── docker-compose.qa.yml
│   └── TESTING.md          # Bitácora detallada de pruebas del frontend
├── docs/
│   ├── specs/              # Especificaciones técnicas de Dominio, Seguridad 11X, GUI Vue 3 y Remediación PropTech (01..13)
│   ├── qa/                 # Manuales maestros de Arquitectura, Buenas Prácticas, QA y Seguridad 11X
│   ├── ARCHITECTURE.md     # Visión general de roles y máquinas de estado
│   └── API_ROUTES.md       # Mapa de vistas (GUI) y endpoints REST
├── scripts/
│   ├── actualizar-grafos-graphify.sh # Extractor AST --code-only sin daemons (sinfallas/remote-graphify)
│   ├── auditar-infra.sh              # Escáner Trivy IaC + FS (HIGH/CRITICAL = 0, caché SHA-256)
│   ├── backup-diario.sh              # Respaldo diario PG17 + MinIO con .sha256, AES-256 opcional y alerta 75%
│   ├── generar-sbom-cyclonedx.sh     # Generador de inventario SBOM CycloneDX en artifacts/sbom/
│   ├── limpieza.sh                   # Purga efímera exclusiva de docker-compose*.qa.yml (protege volúmenes prod)
│   └── verificar-secretos.sh         # Escáner global de credenciales y llaves privadas (árbol completo)
├── test/                   # 11 suites BATS 11X con kcov >= 95% (limpieza, backup, secretos, sbom, CALM, certify, CI...)
├── Makefile                # Orquestación unificada QA 11X (qa-lint, qa-unit, qa-parity, qa-bdd, qa-infra, qa-bash)
├── .env.example            # Plantilla productiva unificada (API, PG17, KeyDB, MinIO, Worker, SMTP, Backup)
├── docker-compose.yml      # Stack de compilación local no-root endurecido (postgres, keydb, minio, api, worker, frontend)
├── docker-compose.prod.yml # Despliegue productivo directo desde Docker Hub multi-arch sin compilación local
├── .npmrc                  # Política supply-chain ignore-scripts=true
├── .trivy.yaml             # Exclusiones corporativas para Trivy IaC y File System
├── AGENTS.md               # Directivas supremas para agentes de IA y desarrolladores (Thin-Repo v3.1.0)
├── SECURITY.md             # Política de seguridad y arquitectura defensiva 11X (20+ vectores)
├── ROADMAP.md              # Plan maestro de hitos y sub-tareas (Hitos 1..26)
├── TESTING.md              # Resumen ejecutivo de certificación QA 11X
├── CHANGELOG.md            # Historial semántico de cambios
└── README.md
```

---

## 🧪 Calidad y Seguridad (Estándar Nivel 11X — `Rule Zero`)

Toda validación corre en **contenedores Docker efímeros** (`sinfallas/*`), sin instalar herramientas en el host.

```bash
# Gates del Backend (desde la raíz o backend/)
make -C backend qa-lint         # Ruff + Mypy (--strict) + Bandit (SAST)
make -C backend qa-complexity   # Radon (Complejidad Ciclomática e Índice de Mantenibilidad <= B)
make -C backend qa-deps         # Auditoría de vulnerabilidades en dependencias (uv audit)
make -C backend qa-unit         # Pruebas unitarias + cobertura (>= 95%)
make -C backend qa-parity       # Paridad real Alembic <-> ORM contra PostgreSQL 17
make -C backend qa-bdd          # Escenarios BDD en Gherkin (Karate Labs)
make -C backend qa-mutation     # Pruebas de mutación AST multi-core (Mutmut MSI >= 80%)
make -C backend qa-contracts    # Fuzzing de contratos OpenAPI (Schemathesis)
make -C backend qa-dast         # Seguridad dinámica (OWASP ZAP)
make -C backend qa-chaos        # Resiliencia y caos (Pumba + Locust + Prometheus)

# Inicialización idempotente Día 0 (CLI bajo RLS PostgreSQL 17)
# docker compose run --rm api python -m src.bootstrap --from-env

# Gates del Frontend Vue 3 Mobile-First (desde la raíz o frontend/)
make -C frontend qa-orphans     # Paridad 100% de componentes Vue sin huérfanos (0 orphans)
make -C frontend qa-lint        # Prettier + vue-tsc --noEmit + ESLint + SonarJS (complejidad <= 15)
make -C frontend qa-unit        # Vitest + Cobertura V8 (>= 95%) + Compilación Vite de producción
make -C frontend qa-mutation    # Pruebas de mutación Frontend (Stryker MSI >= 80%)
make -C frontend qa-e2e         # Playwright Screenplay E2E, Geometría Anti-JSDOM, Visual & WCAG 2.1 AA
make -C frontend qa-perf        # Auditoría Lighthouse CI (Performance >= 90%, A11y >= 95%, Best Practices >= 95%)
make -C frontend qa-bdd         # Escenarios BDD UI en Gherkin (Karate Labs + sidecar chrome-cdp)

# Orquestación unificada y limpieza desde la raíz
make qa-bash                    # shfmt, ShellCheck y suites BATS con kcov >= 95%
make qa-all
./scripts/limpieza.sh --quiet   # Purga contenedores/redes *.qa.yml sin tocar volúmenes prod ni SBOM/AST

# Gate Integral de Certificación de Cierre (.agents + @sinfallas/mcp-qa-11x v3.1.0)
./.agents/scripts/validate_calm_architecture.sh
./.agents/scripts/certify_task_completion.sh --strict
```

### 🐳 Despliegue Productivo Directo desde Docker Hub (Sin Compilación Local)

Para operar una instancia **Single-Condo** en servidores `linux/amd64` o `linux/arm64` consumiendo directamente las imágenes firmadas `sinfallas/condominio-backend` (`CONTAINER_ROLE=api|worker`) y `sinfallas/condominio-frontend` (`nginx:1.27-alpine`, puerto `8080`, no-root):

```bash
cp .env.example .env            # Configurar credenciales seguras y SECRET_KEY / POSTGRES_* / KEYDB_* / MINIO_*
docker compose -f docker-compose.prod.yml up -d
```

---

## 📚 Documentación y Especificaciones (`docs/specs/`)

1. **[`docs/specs/README.md`](./docs/specs/README.md)** — Índice maestro de especificaciones técnicas y trazabilidad.
2. **[`docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md`](./docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md)** — Arquitectura de contenedores, KeyDB Multi-Hilo, las 18 defensas de seguridad híbrida SPA + API y la matriz canónica de idempotencia (`idemp:{scope}:{key}`).
3. **[`docs/specs/02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md`](./docs/specs/02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md)** — Ciclo de vida de Usuarios Fantasma, Estructura, Unidades, Contratos y matriz RBAC.
4. **[`docs/specs/03_DOMINIO_FINANZAS_COBRANZAS_Y_CANDADO.md`](./docs/specs/03_DOMINIO_FINANZAS_COBRANZAS_Y_CANDADO.md)** — Core matemático multimoneda, pagos parciales/totales, auditoría de rechazos y Candado Contable.
5. **[`docs/specs/04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md`](./docs/specs/04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md)** — Embudo de incidencias ("¡Me sumo!"), cuota de 30 fotos/mes, conserjería y worker AVIF.
6. **[`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md)** — Especificación completa de la GUI Vue 3 Mobile-First, ergonomía Anti-JSDOM, stores Pinia no destructivos y paridad 1:1 API ↔ GUI.
7. **[`docs/specs/06_INFORME_INVESTIGACION_Y_EVOLUCION_PROPIEDAD_HORIZONTAL.md`](./docs/specs/06_INFORME_INVESTIGACION_Y_EVOLUCION_PROPIEDAD_HORIZONTAL.md)** — Investigación del estado del arte PropTech LATAM y Ley de Propiedad Horizontal.
8. **[`docs/specs/07_DOMINIO_ALICUOTAS_FACTURACION_Y_SOLVENCIA.md`](./docs/specs/07_DOMINIO_ALICUOTAS_FACTURACION_Y_SOLVENCIA.md)** — Motor de Alícuotas ($\sum = 100\%$), Método del Resto Mayor (Hamilton), Fondos de Reserva, Facturación Mensual LPH, Saldo a Favor y Certificado Digital de Solvencia (`HMAC-SHA256`).
9. **[`docs/specs/08_DOMINIO_GOBERNANZA_CARTAS_CONSULTA_Y_ASAMBLEAS.md`](./docs/specs/08_DOMINIO_GOBERNANZA_CARTAS_CONSULTA_Y_ASAMBLEAS.md)** — Gobernanza Digital (Art. 23 y 24 LPH), Cartas Consulta y Asambleas, Voto Ponderado por Alícuota con firma `HMAC-SHA256` y Acta Automática.
10. **[`docs/specs/09_DOMINIO_ACCESOS_QR_PAQUETERIA_Y_AMENIDADES.md`](./docs/specs/09_DOMINIO_ACCESOS_QR_PAQUETERIA_Y_AMENIDADES.md)** — Control de Acceso QR (`HMAC-SHA256` + `jti` anti-replay en KeyDB), Paquetería en Garita y Reserva de Áreas Sociales vinculada a Solvencia.
11. **[`docs/specs/10_DISENO_UX_UI_AMIGABLE_TRANSICIONES_Y_SISTEMA_TOKENS.md`](./docs/specs/10_DISENO_UX_UI_AMIGABLE_TRANSICIONES_Y_SISTEMA_TOKENS.md)** — Diseño UX/UI de "Hospitalidad Residencial", Sistema de Tokens `OKLCH` + `light-dark()`, Navegación agrupada con SVG, Dashboard Contextual, Estados Vacíos ilustrados, `View Transitions API`, `@starting-style` + Bottom Sheet en `<dialog>` y `calc-size()`.
12. **[`docs/specs/11_ENDURECIMIENTO_BACKEND_CONCURRENCIA_Y_SEGURIDAD_REAL.md`](./docs/specs/11_ENDURECIMIENTO_BACKEND_CONCURRENCIA_Y_SEGURIDAD_REAL.md)** — Endurecimiento Backend Fase 5 (Hito 17): packaging `--no-dev`, Fail-Fast en producción, eliminación de SHA-256 sin sal, ciclo de sesión/CSRF real, bloqueo pesimista PostgreSQL (`with_for_update()`), unicidad contable LPH y aislamiento multi-tenant PostgreSQL 17 `FORCE ROW LEVEL SECURITY` en las 27 tablas.
13. **[`docs/specs/12_GOBERNANZA_DESPLIEGUE_PRODUCTIVO_Y_CI_11X.md`](./docs/specs/12_GOBERNANZA_DESPLIEGUE_PRODUCTIVO_Y_CI_11X.md)** — Gobernanza Thin-Repo, Higiene AST `--code-only` sin daemons, `Rule Zero` (`Makefile` unificado + CI/CD GitHub Actions en verde), Infraestructura Productiva Multi-Stage No-Root, Worker AVIF/SMTP (`QA-HEALTH-01`), Bootstrap Día 0 (`python -m src.bootstrap`) y Certificación `v1.0.0`.
14. **[`docs/specs/13_REMEDIACION_INTEGRAL_COMPLETITUD_FUNCIONAL_Y_DOCKERHUB_11X.md`](./docs/specs/13_REMEDIACION_INTEGRAL_COMPLETITUD_FUNCIONAL_Y_DOCKERHUB_11X.md)** — Plan maestro Post-Auditoría `v1.1.0`–`v1.2.0`: Contención Operativa, Gobernanza Thin-Repo `v3.1.0`, FINOS CALM `1.2`, CI/CD Docker Hub Multi-Arch (`Hito 19` ✅), Defensa PG17 RLS/HKDF/RBAC (`Hito 20`), Exactitud LPH (`Hito 21`), Rescate Frontend (`Hito 22`), Erradicación Anti-Mock (`Hito 23`) y Completitud Funcional PropTech (`Hitos 24–26`).

---

## 📖 Manuales de Operación y Soporte Comunitario (`docs/`)

- 📘 **[`docs/MANUAL_ADMINISTRADOR_E_INSTALADOR.md`](./docs/MANUAL_ADMINISTRADOR_E_INSTALADOR.md)** — Manual Maestro para la Junta de Condominio, Administrador y Personal Técnico: Despliegue con Docker Compose, variables de entorno, seguridad TLS/SSL, respaldos automáticos de PostgreSQL 17/MinIO, configuración de torres, alícuotas y cuotas fijas LPH, activación de usuarios, tesorería trimodal, candado contable inmutable, cartas consulta, garita QR, paquetería, amenidades y comandos de exportación a PDF.
- 🏡 **[`docs/MANUAL_USUARIO_RESIDENTE.md`](./docs/MANUAL_USUARIO_RESIDENTE.md)** — Guía Práctica en lenguaje claro para Propietarios, Inquilinos y Conserjes: Registro y activación, lectura del panel "Tu Hogar Hoy", asistente de pagos en Bs/USD en 3 pasos (con acreditación automática de saldos a favor), incidencias colaborativas con el botón "¡Me sumo!", votación en cartas consulta con recibo criptográfico, pases QR para visitas, recepción de encomiendas, reservas de áreas comunes y certificado digital de solvencia, listo para exportar a PDF y compartir por WhatsApp.

---

## 📄 Licencia y Autoría

**Copyright (C) 2026 Jesús Palencia `<sinfallas@gmail.com>` (Creado en Tecno Consultores)**

Este proyecto es Software Libre distribuido bajo los términos de la licencia **MIT**. Ver [`LICENSE`](./LICENSE) para más detalles.
