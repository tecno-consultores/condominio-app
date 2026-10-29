# 🗺️ Control de Tareas y Roadmap — Condominio App

**Estándar de Ingeniería:** Gobernanza y Calidad Nivel 11X (`Rule Zero` — 100% Docker Efímero)  
**Especificaciones Técnicas Base:** [`docs/specs/README.md`](./docs/specs/README.md)

---

## 📊 Estado General del Proyecto

- **Fase 1 (Backend FastAPI & Seguridad 11X):** En curso — Hitos 1, 2, 3 y 3.5 **`[COMPLETADOS]`**; Hito 4 pendiente.
- **Fase 2 (Frontend Vue 3 Mobile-First):** Lista para iniciar con especificaciones completas (`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`) — Hitos 5, 6 y 7 pendientes.
- **Fase 3 (Integración E2E, Accesibilidad y Caos Nivel 11X):** Parcial — Hito 9 **`[COMPLETADO]`**; Hito 8 pendiente tras Fase 2.
- **Leyenda:**
  - `[COMPLETADO]` = Hito certificado bajo el estándar QA Nivel 11X en contenedores Docker efímeros (`>= 95%` cobertura, 0 errores SAST/lint/complejidad, paridad Alembic↔ORM en PostgreSQL 17 y escenarios BDD Karate Labs).
  - `[PENDIENTE]` = Hito con especificación cerrada en `docs/specs/`, listo para implementación.

---

## 🏗️ FASE 1: Backend Base, Seguridad 11X y Dominios Core (`backend/`)

### Hito 1: Setup Base y Modelos de Datos `[COMPLETADO]`
- **Especificación:** [`docs/specs/02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md`](./docs/specs/02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md)
- **Implementación:**
  - [x] Creación de `src/main.py` con instrumentación Prometheus (`/metrics` excluido del contrato OpenAPI público) y endpoint `/health`.
  - [x] Configuración de SQLAlchemy 2.0 asíncrono (`asyncpg` / `aiosqlite`) y migraciones Alembic.
  - [x] Modelado de `Usuario`, `Estructura`, `Unidad` e histórico `ContratoOcupacion`.
- **Certificación QA 11X:**
  - [x] Pruebas unitarias aisladas en `tests/test_main.unit.py`, `tests/test_models.unit.py` y `tests/test_schemas.unit.py`.

### Hito 2: Autenticación, Ciclo de Vida JWT e Idempotencia `[COMPLETADO]`
- **Especificación:** [`docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md`](./docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md), [`docs/specs/02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md`](./docs/specs/02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md)
- **Implementación:**
  - [x] Rutas `POST /api/auth/register` (creación de Usuarios Fantasma con `es_activo=False`, exigiendo `Idempotency-Key`), `POST /api/auth/login` y `GET /api/auth/me`.
  - [x] Emisión de JWT HS256 en cookie `HttpOnly` (`SameSite=Lax`) y soporte dual para encabezado `Authorization: Bearer`.
- **Certificación QA 11X:**
  - [x] Pruebas unitarias en `tests/test_auth.unit.py` y `tests/test_dependencies.unit.py` cubriendo fallos de BD, expiración/adulteración de JWT y conflictos 409 de idempotencia.

### Hito 3: Finanzas, Cobranzas y Candado Contable `[COMPLETADO]`
- **Especificación:** [`docs/specs/03_DOMINIO_FINANZAS_COBRANZAS_Y_CANDADO.md`](./docs/specs/03_DOMINIO_FINANZAS_COBRANZAS_Y_CANDADO.md)
- **Implementación:**
  - [x] Núcleo matemático puro (`src/finanzas.py`) con aritmética `Decimal` exacta (`ROUND_HALF_UP`), conversión multimoneda USD/VES y fronteras de abono parcial vs pago total.
  - [x] Flujo idempotente `POST /api/pagos/reportar`, aprobación `PUT /api/pagos/{id}/aprobar`, rechazo auditado `PUT /api/pagos/{id}/rechazar` y listado `GET /api/pagos/revision`.
  - [x] Gestión de tasas BCV (`POST/GET /api/finanzas/tasa`), egresos (`POST /api/finanzas/egresos`), resumen (`GET /api/finanzas/resumen`) e inmutabilidad del **Candado Contable** (`POST /api/finanzas/cierre-mensual`) con `RegistroAuditoria`.
- **Certificación QA 11X:**
  - [x] Pruebas de frontera estrictas en `tests/test_finanzas_core.unit.py`, `tests/test_pagos.unit.py` y `tests/test_finanzas_router.unit.py`.

### Hito 3.5: Gobernanza `.agents/`, Endurecimiento de Seguridad 11X y Especificaciones de Dominio `[COMPLETADO]`
- **Especificación:** [`docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md`](./docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md)
- **Implementación:**
  - [x] Gobernanza de agentes IA en `AGENTS.md`, `SECURITY.md`, `.agents/rules/` (6 directivas), `.agents/skills/` (3 skills) y `.agents/scripts/` (certificación de cierre, paridad Alembic↔ORM en PostgreSQL 17, cero componentes Vue huérfanos, salud topológica y radio de impacto).
  - [x] Migración de hashing de contraseñas a `PBKDF2-HMAC-SHA256` con sal criptográfica de 16 bytes (100.000 iteraciones) y comparación en tiempo constante (`hmac.compare_digest`).
  - [x] Defensas híbridas SPA+API en `src/security.py`, `src/redis_client.py` y `src/main.py`: CSRF HMAC-SHA256 (`generate_csrf_token`/`validate_csrf_token`), Anti-SSRF con pre-resolución DNS (`validate_safe_outgoing_url`), lectura segura de uploads por chunks con cuota de 2 MB (`read_uploaded_file_safely`), validación de `Origin` en WebSockets (`verify_websocket_origin`), claves de idempotencia aisladas por alcance (`idemp:{scope}:{key}`), periodo de gracia de 5s para rotación de refresh tokens, bloqueo de Mass Assignment (`ConfigDict(extra="forbid")`), ocultamiento de `/docs` en producción y sanitización de errores 422.
  - [x] Actualización de `backend/docker-compose.qa.yml` con **KeyDB Multi-Hilo** (`eqalpha/keydb:alpine --server-threads 2`) y **PostgreSQL 17** (`postgres:17-alpine`) para el gate `make qa-parity`.
  - [x] Creación de los manuales `docs/qa/01..04` y de las 6 especificaciones de dominio y GUI en `docs/specs/`.
- **Certificación QA 11X:**
  - [x] Suite unitaria `tests/test_security_11x.unit.py`, paridad `make qa-parity` en PostgreSQL 17 y 7 escenarios BDD en `backend/test/api_test.feature`.

### Hito 4: Módulos Operativos, Estructura, Incidencias y Tareas Asíncronas `[PENDIENTE]`
- **Especificaciones:** [`docs/specs/02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md`](./docs/specs/02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md), [`docs/specs/04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md`](./docs/specs/04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md)
- **Sub-tareas de Implementación:**
  - [ ] **Sub-tarea 4.1 (Estructura y Activación de Usuarios Fantasma):** Implementar endpoints `POST /api/estructuras`, `GET /api/estructuras`, `POST /api/unidades`, `GET /api/usuarios/pendientes` y `PUT /api/usuarios/{id}/aprobar` (asignación de `Unidad`, creación de `ContratoOcupacion` activo, activación `es_activo=True` y registro en `RegistroAuditoria`).
  - [ ] **Sub-tarea 4.2 (Embudo de Incidencias Vecinales y Cuota de Fotos):** Modelar `Incidencia`, `ApoyoIncidencia` (`UNIQUE(incidencia_id, usuario_id)`) y `EvidenciaIncidencia` con su migración Alembic verificada en PostgreSQL 17 (`make qa-parity`). Implementar `GET/POST /api/incidencias`, `POST /api/incidencias/{id}/me-sumo` (transición a `PRIORITARIA` al alcanzar umbral $\ge 5$ apoyos) y control estricto de cuota de **30 fotos/mes calendario** para el rol `VOCERO` con `read_uploaded_file_safely` (máx. 2 MB, HTTP 413/429).
  - [ ] **Sub-tarea 4.3 (Checklist del Conserje y Cronjob Diario):** Modelar `PlantillaTarea` y `TareaConserje` (`UNIQUE(plantilla_id, fecha_asignacion)`). Implementar el generador idempotente diario, `GET /api/tareas/hoy` y `PUT /api/tareas/{id}/completar`.
  - [ ] **Sub-tarea 4.4 (Worker Asíncrono AVIF, Webhooks Seguros y Notificaciones):** Integrar cola asíncrona sobre KeyDB para conversión de evidencias a formato AVIF en MinIO y envío de notificaciones validando cualquier webhook saliente con `validate_safe_outgoing_url` (Anti-SSRF).
  - [ ] **Sub-tarea 4.5 (Certificación QA 11X del Hito 4):** Pruebas unitarias (`>= 95%`), paridad `make qa-parity` en PostgreSQL 17, contratos Schemathesis y nuevos escenarios BDD en `backend/test/api_test.feature`.

---

## 📱 FASE 2: Frontend Vue 3 Mobile-First (`frontend/`)

> **Regla Rectora para Fase 2:** Toda la implementación de la GUI debe seguir estrictamente [`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md) y [`.agents/rules/frontend_parity_and_closure.md`](./.agents/rules/frontend_parity_and_closure.md). Queda prohibido dejar componentes `.vue` huérfanos (`make qa-orphans`), destruir estado en Pinia ante errores HTTP o solapar `BottomNavBar`, FAB y `AppFooter`.

### Hito 5: Base Arquitectónica Frontend, Seguridad Cliente y Flujos de Identidad `[PENDIENTE]`
- **Especificación:** [`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md) (Secciones 1, 2, 3, 5, 6 y 8)
- **Sub-tareas de Implementación:**
  - [ ] **Sub-tarea 5.1 (Scaffolding Efímero y Orquestación QA):** Inicializar `frontend/` con Vue 3 (`<script setup lang="ts">`), Vite, Tailwind CSS, Pinia y Vue Router. Configurar `frontend/Makefile` y `frontend/docker-compose.qa.yml` utilizando `sinfallas/base-node-ionic:26` y `sinfallas/qa-frontend:26` con los gates `qa-lint`, `qa-unit`, `qa-orphans`, `qa-e2e`, `qa-ui-bdd` y `qa-lighthouse`.
  - [ ] **Sub-tarea 5.2 (Seguridad Cliente y Cliente HTTP Resiliente):** Implementar `frontend/src/utils/security.ts` (`generateIdempotencyKey`, `isSafeRedirectUrl`, `sanitizeUntrustedText`, `validateProofFileUpload`) y `frontend/src/services/api.ts` con `credentials: 'include'`, inyección automática de `X-CSRF-Token` y gestión del ciclo de vida del `Idempotency-Key` (reutilización en reintentos de red vs regeneración tras 4xx).
  - [ ] **Sub-tarea 5.3 (Layout Mobile-First Anti-JSDOM):** Implementar `AppShell.vue`, `BottomNavBar.vue` (`h-16`, máx. 4 ítems por rol con área táctil $\ge 48 \times 48\text{ px}$), `DesktopSidebar.vue` y `AppFooter.vue` (en flujo normal del documento, nunca `position: fixed`), aplicando `pb-24` en `<main>` para evitar solapamientos.
  - [ ] **Sub-tarea 5.4 (Store de Autenticación y Vistas de Identidad):** Implementar `useAuthStore` con manejo de errores no destructivo, Navigation Guards en `router/index.ts` (validando `redirect` con `isSafeRedirectUrl`) y vistas `LoginView.vue` (`/login`), `RegistroView.vue` (`/registro`) y `EsperaAprobacionView.vue` (`/espera-aprobacion` para Usuarios Fantasma).
  - [ ] **Sub-tarea 5.5 (Certificación QA 11X del Hito 5):** Cobertura `>= 95%` en Vitest (`security.unit.ts`, `auth.store.unit.ts`), 0 componentes huérfanos (`make qa-orphans`), complejidad cognitiva SonarJS $\le 15$ y escenarios iniciales en `frontend/test/ui_business_flow.feature`.

### Hito 6: Vistas Financieras, Wizard de Pagos y Mesa de Tesorería `[PENDIENTE]`
- **Especificación:** [`docs/specs/03_DOMINIO_FINANZAS_COBRANZAS_Y_CANDADO.md`](./docs/specs/03_DOMINIO_FINANZAS_COBRANZAS_Y_CANDADO.md), [`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md) (Secciones 4, 6 y 7)
- **Sub-tareas de Implementación:**
  - [ ] **Sub-tarea 6.1 (Store Financiero No Destructivo):** Implementar `useFinanzasStore` y `usePagosStore` preservando `resumen`, `tasaActiva` y `recibosPendientes` cuando ocurran errores HTTP (400/409/422/500).
  - [ ] **Sub-tarea 6.2 (Dashboard de Propietario):** Implementar `InicioView.vue` (`/inicio`) con `DeudaCard.vue` (saldo consolidado en USD y equivalente en VES según tasa BCV activa), `ComunicadosCarousel.vue`, `CierreMensualBanner.vue` y `MisRecibosView.vue` (`/finanzas/recibos`).
  - [ ] **Sub-tarea 6.3 (Wizard de Pagos Idempotente en 3 Pasos):** Implementar `PagarWizardView.vue` (`/pagar`) y `PagoWizard.vue`: Paso 1 (selección de recibo e indicador dinámico de `ABONO PARCIAL` vs `PAGO TOTAL`), Paso 2 (selección de método `ZELLE`/`PAGO_MOVIL`/`TRANSFERENCIA`/`EFECTIVO` con referencia obligatoria condicional y validación previa de comprobante $\le 2\text{ MB}$ con `validateProofFileUpload`), Paso 3 (resumen inmutable y envío con `Idempotency-Key` persistido por intento).
  - [ ] **Sub-tarea 6.4 (Mesa de Revisión de Pagos y Cierre Mensual):** Implementar `PagosRevisionView.vue` (`/admin/pagos-revision`) con aprobación en un toque y `RechazoPagoModal.vue` (motivo obligatorio $\ge 5$ caracteres), más `AdminFinanzasView.vue` (`/admin/finanzas`) con alta de tasa BCV, registro de egresos, `SemaforoCobranza.vue` y modal de confirmación reforzada para el **Candado Contable** (`POST /api/finanzas/cierre-mensual`).
  - [ ] **Sub-tarea 6.5 (Certificación QA 11X del Hito 6):** Pruebas unitarias en Vitest (`>= 95%`), verificación de cero huérfanos (`make qa-orphans`) y escenarios Karate UI del flujo financiero completo.

### Hito 7: Vistas Administrativas, Embudo de Incidencias y Conserjería `[PENDIENTE]`
- **Especificaciones:** [`docs/specs/04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md`](./docs/specs/04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md), [`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md) (Sección 4)
- **Sub-tareas de Implementación:**
  - [ ] **Sub-tarea 7.1 (Constructor de Estructura y Aprobación de Usuarios):** Implementar `EstructuraAdminView.vue` (`/admin/estructura`) y `UsuariosPendientesView.vue` (`/admin/usuarios-pendientes`) permitiendo al Presidente activar Usuarios Fantasma asignándoles Unidad y Rol.
  - [ ] **Sub-tarea 7.2 (Embudo de Incidencias Vecinales):** Implementar `IncidenciasFeedView.vue` (`/incidencias`) con `IncidenciaFeedCard.vue`, botón reactivo idempotente `MeSumoButton.vue` ("¡Me sumo!"), indicador de cuota `PhotoQuotaBadge.vue` (`fotos_usadas_mes / 30` para Voceros) y badge de estado de optimización AVIF.
  - [ ] **Sub-tarea 7.3 (Checklist Operativo del Conserje):** Implementar `ConserjeTareasView.vue` (`/conserje/tareas`) y `TareaChecklistItem.vue` con casillas táctiles de alto contraste y carga de evidencia.
  - [ ] **Sub-tarea 7.4 (Certificación QA 11X del Hito 7):** Pruebas unitarias en Vitest (`>= 95%`), paridad 100% API ↔ GUI y cero componentes huérfanos (`make qa-orphans`).

---

## 🛡️ FASE 3: Integración E2E, Accesibilidad y Caos Nivel 11X

### Hito 8: Certificación E2E, Geometría Visual Anti-JSDOM, WCAG 2.1 AA y Lighthouse CI `[PENDIENTE]`
- **Especificación:** [`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md) (Secciones 3 y 8)
- **Sub-tareas de Certificación:**
  - [ ] **Sub-tarea 8.1 (Playwright E2E y Geometría Visual Anti-JSDOM):** Ejecutar suites `.e2e.ts` en Chromium headless validando flujos de negocio y verificando con `getBoundingClientRect()` en viewports móviles (`375x667`, `390x844`) que ningún botón primario, FAB o `AppFooter` quede oculto tras el `BottomNavBar`.
  - [ ] **Sub-tarea 8.2 (Auditoría WCAG 2.1 AA y Regresión Visual):** Certificar **0 violaciones** `critical` o `serious` con `@axe-core/playwright` tanto en tema claro como en tema oscuro, y validar snapshots visuales (`maxDiffPixelRatio: 0.02`).
  - [ ] **Sub-tarea 8.3 (Karate UI y Lighthouse CI):** Certificar `make qa-ui-bdd` (`frontend/test/ui_business_flow.feature`) y `make qa-lighthouse` (Performance $\ge 90\%$, Accessibility $\ge 95\%$, Best Practices $\ge 95\%$).

### Hito 9: Ingeniería del Caos y Resiliencia Extrema `[COMPLETADO]`
- **Especificación:** [`docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md`](./docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md)
- **Certificación Ejecutada:**
  - [x] `make qa-chaos` (Pumba + Locust + Prometheus): **2.786 peticiones** contra la API bajo inyección de latencia `netem` ($500\text{ ms} \pm 50\text{ ms}$), **0 fallos**, sin bloqueos ni degradación acumulada ($p99 \approx 1.4\text{ s}$).
  - [x] `make qa-contracts` (Schemathesis): **626/626 casos** OpenAPI aprobados con 0 fallos.
  - [x] `make qa-dast` (OWASP ZAP): **FAIL-NEW: 0** (66 reglas aprobadas).
