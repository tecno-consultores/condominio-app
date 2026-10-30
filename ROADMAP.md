# 🗺️ Control de Tareas y Roadmap — Condominio App

**Estándar de Ingeniería:** Gobernanza y Calidad Nivel 11X (`Rule Zero` — 100% Docker Efímero)  
**Especificaciones Técnicas Base:** [`docs/specs/README.md`](./docs/specs/README.md)

---

## 📊 Estado General del Proyecto

- **Fase 1 (Backend FastAPI & Seguridad 11X):** **`[100% COMPLETADA]`** — Hitos 1, 2, 3, 3.5 y 4 completados y certificados.
- **Fase 2 (Frontend Vue 3 Mobile-First Core):** **`[100% COMPLETADA]`** — **Hitos 5, 6 y 7 `[COMPLETADOS]`** y certificados.
- **Fase 3 (Resiliencia Extrema e Ingeniería del Caos Nivel 11X):** **`[100% COMPLETADA]`** — **Hito 9 `[COMPLETADO]`** (el **Hito 8** de Certificación E2E, Geometría Visual Anti-JSDOM, WCAG 2.1 AA y Lighthouse CI fue reubicado al cierre del Roadmap como **Fase 5** para certificar la totalidad de pantallas de las Fases 2 y 4).
- **Fase 4 (Evolución PropTech, Ley de Propiedad Horizontal, Ayuda Contextual y Manuales — Specs 05..09):** **`[EN EJECUCIÓN — HITO 10 COMPLETADO]`** — **Hito 10 `[COMPLETADO]`**; **Hito 11** siguiente en espera de implementación (junto con Hitos 12, 13 y 14).
- **Fase 5 (Certificación Integral E2E, Geometría Visual Anti-JSDOM, WCAG 2.1 AA y Lighthouse CI):** **`[PENDIENTE AL CIERRE DE FASE 4]`** — **Hito 8** ubicado al final para auditar todas las vistas del sistema.
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

### Hito 4: Módulos Operativos, Estructura, Incidencias y Tareas Asíncronas `[COMPLETADO]`
- **Especificaciones:** [`docs/specs/02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md`](./docs/specs/02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md), [`docs/specs/04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md`](./docs/specs/04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 4.1 (Estructura, Activación de Usuarios Fantasma y Junta):** Implementados `GET /api/estructura/unidades`, `POST /api/estructura/generar` (`Idempotency-Key`), `GET /api/usuarios/pendientes`, `PUT /api/usuarios/{id}/asignar` y `PUT /api/junta/cargos` (validando contrato activo de `PROPIETARIO`) en `backend/src/routers/administracion.py`.
  - [x] **Sub-tarea 4.2 (Embudo de Incidencias Vecinales y Cuota de 30 Fotos/Mes):** Modeladas las 7 tablas operativas en `backend/src/models.py` con migración `0002_hito4_operaciones.py` verificada en PostgreSQL 17. Implementados `GET /api/incidencias/abiertas`, `POST /api/incidencias/crear` y `POST /api/incidencias/{id}/adherir` en `backend/src/routers/incidencias.py`, más `POST /api/voceros/fotos` (límite estricto de 30 fotos/mes calendario devolviendo `429 Too Many Requests`) y `GET /api/voceros/galeria` en `backend/src/routers/operaciones.py`.
  - [x] **Sub-tarea 4.3 (Checklist del Conserje, Bitácora y Comunicados):** Implementados `POST /api/tareas/plantillas`, `POST /api/tareas/diarias`, `POST /api/tareas/generar-diarias`, `GET /api/tareas/diarias` y `PUT /api/tareas/{id}/completar` (con cierre automático de la incidencia vinculada), además de `POST /api/bitacora/acta`, `GET /api/bitacora/historial`, `POST /api/comunicados` (protegido con `validate_safe_outgoing_url`) y `GET /api/comunicados/recientes`.
  - [x] **Sub-tarea 4.4 (Worker Asíncrono AVIF y Notificaciones):** Implementado `backend/src/worker.py` (`convertir_y_subir_avif`, `encolar_notificacion_correo`, `generar_tareas_diarias_desde_plantillas`).
  - [x] **Sub-tarea 4.5 (Certificación QA 11X del Hito 4):** Suite unitaria `tests/test_hito4_operaciones.unit.py` (159 pruebas totales, 99.83% cobertura), paridad `make qa-parity` de las 17 tablas en PostgreSQL 17 y 10 escenarios BDD en `backend/test/api_test.feature`.

---

## 📱 FASE 2: Frontend Vue 3 Mobile-First (`frontend/`)

> **Regla Rectora para Fase 2:** Toda la implementación de la GUI debe seguir estrictamente [`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md) y [`.agents/rules/frontend_parity_and_closure.md`](./.agents/rules/frontend_parity_and_closure.md). Queda prohibido dejar componentes `.vue` huérfanos (`make qa-orphans`), destruir estado en Pinia ante errores HTTP o solapar `BottomNavBar`, FAB y `AppFooter`.

### Hito 5: Base Arquitectónica Frontend, Seguridad Cliente y Flujos de Identidad `[COMPLETADO]`
- **Especificación:** [`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md) (Secciones 1, 2, 3, 5, 6 y 8)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 5.1 (Scaffolding Efímero y Orquestación QA):** Inicializado `frontend/` con Vue 3 (`<script setup lang="ts">`), Vite, Pinia, Vue Router y TypeScript Strict. Configurados `frontend/Makefile`, `frontend/docker-compose.qa.yml` (`sinfallas/base-node-ionic:26`), `pnpm-workspace.yaml` (política Zero-Trust `allowBuilds`), `vitest.config.ts`, `playwright.config.ts`, `stryker.conf.json` y `lighthouserc.js`.
  - [x] **Sub-tarea 5.2 (Seguridad Cliente y Cliente HTTP Resiliente):** Implementados `frontend/src/utils/security.ts` (`escapeHtml`, `sanitizeUntrustedText`, `sanitizeObject`, `isSafeRedirectUrl`, `validateProofFileUpload`, `generateIdempotencyKey`), `frontend/src/composables/useIdempotency.ts` y `frontend/src/services/apiClient.ts` (`credentials: 'include'`, `X-CSRF-Token`, `Idempotency-Key` y `ApiError`).
  - [x] **Sub-tarea 5.3 (Layout Mobile-First Anti-JSDOM):** Implementados `AppShellLayout.vue`, `BottomNavBar.vue` (`4rem`, máx. 4 ítems por rol con área táctil $\ge 48 \times 48\text{ px}$), `SidebarNav.vue`, `AppFooter.vue` (en flujo normal con `margin-top: auto`) y `StaleDataBanner.vue`.
  - [x] **Sub-tarea 5.4 (Store de Autenticación y Vistas de Identidad):** Implementado `useAuthStore` con manejo de errores no destructivo (`isStale = true` conservando `data` ante caídas de red), guardias de navegación en `frontend/src/router/index.ts` y vistas `LoginView.vue` (`/login`), `RegisterView.vue` (`/register`), `PendingApprovalView.vue` (`/espera-aprobacion`) y `DashboardView.vue` (`/dashboard`).
  - [x] **Sub-tarea 5.5 (Certificación QA 11X del Hito 5):** 15 suites unitarias en Vitest con **100% de cobertura de líneas/sentencias** (`> 95%` en ramas y funciones), **0 componentes huérfanos** (`make qa-orphans`: 10/10 componentes `.vue`), 0 errores en `vue-tsc` / `eslint` (SonarJS CC $\le 15$) y escenarios BDD/E2E en `frontend/test/ui_business_flow.feature` y `frontend/e2e/accessibility.e2e.ts`.

### Hito 6: Vistas Financieras, Wizard de Pagos y Mesa de Tesorería `[COMPLETADO]`
- **Especificación:** [`docs/specs/03_DOMINIO_FINANZAS_COBRANZAS_Y_CANDADO.md`](./docs/specs/03_DOMINIO_FINANZAS_COBRANZAS_Y_CANDADO.md), [`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md) (Secciones 4, 6 y 7)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 6.1 (Store Financiero No Destructivo):** Implementado `useFinanceStore` (`useFinanzasStore`) en `frontend/src/stores/financeStore.ts` preservando `tasaActiva`, `resumen` y `pagosEnRevision` con `isStale = true` ante errores de red o bloqueos HTTP (400/409/422/500), junto con conversores multimoneda (`convertUsdToVes`, `convertVesToUsd`) y detector `determinePaymentCoverage`.
  - [x] **Sub-tarea 6.2 (Dashboard Financiero de Propietario):** Actualizado `DashboardView.vue` (`/dashboard`, alias `/inicio`) integrando `ClosingBanner.vue` (`#closing-banner`), `AnnouncementsCarousel.vue`, `CollectionTrafficLight.vue` (`#tab-cobranza` con `@container (width < 600px)` apilado y unidad propia primero) y `ExpensesDonutChart.vue` (`#tab-gastos` con SVG nativo accesible).
  - [x] **Sub-tarea 6.3 (Wizard de Pagos Idempotente en 3 Pasos):** Implementado `PaymentWizardView.vue` (`/finanzas/reportar-pago`, alias `/pagar`): Paso 1 (selección de recibo, moneda `VES`/`USD`, conversión en tiempo real e indicador `#badge-tipo-cobertura` `PAGO TOTAL` vs `ABONO PARCIAL`), Paso 2 (método `PAGO_MOVIL`/`TRANSFERENCIA`/`ZELLE`/`EFECTIVO`, referencia obligatoria condicional y validación cliente de comprobante $\le 2\text{ MB}$ con `validateProofFileUpload`), Paso 3 (resumen inmutable y envío con `Idempotency-Key` vía `useIdempotency`).
  - [x] **Sub-tarea 6.4 (Mesa de Revisión de Pagos y Candado Contable):** Implementados `TreasuryPaymentsView.vue` (`/tesoreria/pagos`, alias `/admin/pagos-revision`) con aprobación en un toque y `RejectPaymentModal.vue` (`<dialog>` nativo con motivo obligatorio $\ge 5$ caracteres), más `TreasuryClosingView.vue` (`/tesoreria/cierre`, alias `/admin/finanzas`) con alta de tasa BCV, registro de egresos y modal `<dialog>` de confirmación reforzada para el **Candado Contable** (`POST /api/finanzas/cierre-mensual`).
  - [x] **Sub-tarea 6.5 (Certificación QA 11X del Hito 6):** 24 suites unitarias en Vitest (`50/50 tests`, **99.74% líneas/sentencias, 95.62% ramas, 96.96% funciones**), **0 componentes huérfanos** (`make qa-orphans`: 18/18 componentes `.vue`) y escenarios BDD en `frontend/test/ui_business_flow.feature`.

### Hito 7: Vistas Administrativas, Embudo de Incidencias y Conserjería `[COMPLETADO]`
- **Especificaciones:** [`docs/specs/04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md`](./docs/specs/04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md), [`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md) (Sección 4)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 7.1 (Constructor de Estructura, Activación de Usuarios Fantasma y Junta):** Implementadas `AdminStructureView.vue` (`/admin/estructura`), `AdminGhostUsersView.vue` (`/admin/usuarios`, alias `/admin/usuarios-pendientes`) y `AdminBoardRolesView.vue` (`/admin/junta`) junto con `useOperationsStore` (`frontend/src/stores/operationsStore.ts`) aplicando **Catch No Destructivo** (`isStale = true`).
  - [x] **Sub-tarea 7.2 (Embudo de Incidencias Vecinales y Galería de Voceros):** Implementadas `IncidentsFeedView.vue` (`/incidencias`) con `IncidentCard.vue` y botón reactivo "¡Me sumo!", `SpokespersonGalleryView.vue` (`/voceros/galeria`) con barra de cuota mensual `fotos_usadas_mes / 30` (`#photo-quota-badge`) y distintivo AVIF, y `SecretaryLogbookView.vue` (`/secretaria/bitacora`).
  - [x] **Sub-tarea 7.3 (Checklist Operativo del Conserje):** Implementadas `OperationsTasksView.vue` (`/operaciones/tareas`, alias `/conserje/tareas`) y `TaskChecklistItem.vue` con casillas táctiles de alto contraste (`accent-color` + `color-scheme: light dark` y fallback `@supports not (accent-color: ...)`), cierre automático de incidencia vinculada y barra de progreso diario.
  - [x] **Sub-tarea 7.4 (Grafo AST, Gobernanza y Certificación QA 11X del Hito 7):** Generado Grafo de Conocimiento AST en `graphify-out/graph.json` y `graphify-out/GRAPH_REPORT.md` (**1.075 nodos, 2.464 relaciones, 59 comunidades, 0 violaciones topológicas**), creado diario determinista `ACTIVE_TASK.md`, scripts `scripts/limpieza.sh` y `frontend/limpieza.sh`, y certificadas **34 suites unitarias en Vitest (`70/70 tests`, 99.80% líneas/sentencias, 97.88% funciones, 95.73% ramas)** con **0 componentes huérfanos** (`27/27` componentes `.vue`).

---

## 🛡️ FASE 3: Resiliencia Extrema e Ingeniería del Caos Nivel 11X

### Hito 9: Ingeniería del Caos y Resiliencia Extrema `[COMPLETADO]`
- **Especificación:** [`docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md`](./docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md)
- **Certificación Ejecutada:**
  - [x] `make qa-chaos` (Pumba + Locust + Prometheus): **2.786 peticiones** contra la API bajo inyección de latencia `netem` ($500\text{ ms} \pm 50\text{ ms}$), **0 fallos**, sin bloqueos ni degradación acumulada ($p99 \approx 1.4\text{ s}$).
  - [x] `make qa-contracts` (Schemathesis): **626/626 casos** OpenAPI aprobados con 0 fallos.
  - [x] `make qa-dast` (OWASP ZAP): **FAIL-NEW: 0** (66 reglas aprobadas).

---

## 🏛️ FASE 4: Evolución Funcional PropTech, Ley de Propiedad Horizontal y Experiencia de Usuario (Hitos 10 al 14)

> **Regla Rectora para Fase 4:** Cada hito de esta fase incluye tanto el Backend (migración Alembic en PostgreSQL 17, lógica de negocio idempotente y endpoints REST) como su paridad 1:1 en el Frontend Vue 3 Mobile-First (stores Pinia con Catch No Destructivo, vistas sin huérfanos `.unit.ts` y escenarios BDD en `backend/test/api_test.feature` y `frontend/test/ui_business_flow.feature`).

### Hito 10: Mejoras Core, Motor de Alícuotas, Facturación Mensual LPH, Fondos y Solvencia Digital `[COMPLETADO]`
- **Especificaciones:** [`docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md`](./docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md), [`docs/specs/07_DOMINIO_ALICUOTAS_FACTURACION_Y_SOLVENCIA.md`](./docs/specs/07_DOMINIO_ALICUOTAS_FACTURACION_Y_SOLVENCIA.md)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 10.1 (Mejoras de Seguridad Core — Magic Bytes, Revocación KeyDB y Anti-Fraude Referencias):** Implementado `validate_file_magic_bytes` en `backend/src/security.py`, lista de revocación instantánea `revoked_user:{id}` en `backend/src/redis_client.py` / `dependencies.py` / `auth.py`, y bloqueo `HTTP 409 Conflict` ante reutilización de `(metodo, numero_referencia)` en `backend/src/routers/pagos.py`.
  - [x] **Sub-tarea 10.2 (Migración 0003 y Modelos de Alícuotas, Cuota Fija, Fondos, Desglose y Solvencia):** Extendidos `Unidad` (`alicuota`, `cuota_fija_usd`, `credito_disponible_usd`) y `Egreso` (`incidencia_id`, `es_gasto_comun`), creados modelos `FondoCondominio`, `ReciboItem` y `CertificadoSolvencia` en `backend/src/models.py`, y verificada migración `0003_hito10_alicuotas_solvencia.py` contra PostgreSQL 17 real (**20 tablas en paridad 1:1**).
  - [x] **Sub-tarea 10.3 (Facturación Trimodal: Alícuotas / Cuota Fija / Partes Iguales y Endpoints de Solvencia):** Implementados `prorratear_por_alicuotas` (Método del Resto Mayor / Hamilton), soporte para `modalidad = "CUOTA_FIJA"` (con conciliación automática de superávit/déficit hacia `FondoCondominio`) y `"PARTES_IGUALES"`, `aplicar_credito_disponible`, `calcular_excedente_pago` y firma `HMAC-SHA256` en `backend/src/finanzas.py`, acreditación automática de sobrepagos en `PUT /api/pagos/{id}/aprobar`, y endpoints `PUT /api/estructura/unidades/{id}/alicuota`, `POST/GET /api/finanzas/fondos`, `POST /api/finanzas/facturar-periodo`, `GET /api/finanzas/recibos/{id}/desglose`, `POST /api/finanzas/solvencia/{unidad_id}` y `GET /api/finanzas/solvencia/verificar/{folio}`.
  - [x] **Sub-tarea 10.4 (Paridad GUI Vue 3 — Facturación y Certificado de Solvencia):** Extendidos `useFinanceStore` y `useOperationsStore` con Catch No Destructivo, e implementados `BillingGeneratorView.vue` (`/tesoreria/facturacion`), `ReceiptBreakdownModal.vue`, `SolvencyCertificateView.vue` (`/finanzas/solvencia`) y edición de alícuota/cuota fija en `AdminStructureView.vue`.
  - [x] **Sub-tarea 10.5 (Certificación QA 11X del Hito 10):** **182 pruebas unitarias en backend (`99.83%` cobertura)**, **37 suites / 75 pruebas unitarias en frontend (`99.84%` líneas/sentencias, `98.26%` funciones, `95.37%` ramas)**, **0 componentes huérfanos (`30/30` `.vue`)**, paridad PostgreSQL 17 (`20` tablas), actualización del Grafo AST y escenarios BDD Karate Labs (`backend/test/api_test.feature` y `frontend/test/ui_business_flow.feature`).

### Hito 11: Gobernanza Digital, Cartas Consulta (Art. 23 LPH) y Asambleas con Voto Criptográfico `[COMPLETADO]`
- **Especificación:** [`docs/specs/08_DOMINIO_GOBERNANZA_CARTAS_CONSULTA_Y_ASAMBLEAS.md`](./docs/specs/08_DOMINIO_GOBERNANZA_CARTAS_CONSULTA_Y_ASAMBLEAS.md)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 11.1 (Migración 0004 y Modelos de Gobernanza LPH):** Añadido `puede_votar_asamblea` en `ContratoOcupacion` y modelados `ConsultaComunitaria`, `OpcionConsulta` y `VotoConsulta` (`UniqueConstraint("consulta_id", "unidad_id")`) en `backend/src/models.py` con migración `0004_hito11_cartas_consulta.py` verificada en PostgreSQL 17 real (**23 tablas en paridad 1:1**).
  - [x] **Sub-tarea 11.2 (Router de Consultas, Firma HMAC-SHA256 de Voto y Acta Automática):** Implementados `umbral_quorum_por_regla`, `generar_firma_voto_consulta`, `verificar_firma_voto_consulta`, `calcular_ip_hash_voto` y `evaluar_escrutinio_consulta` en `backend/src/finanzas.py`, y el router `backend/src/routers/consultas.py` (`POST /api/consultas`, `GET /api/consultas`, `GET /api/consultas/{id}`, `POST /api/consultas/{id}/votar` ponderado por `Unidad.alicuota` con recibo `HMAC-SHA256`, y `POST /api/consultas/{id}/cerrar` con generación atómica de acuerdo en `BitacoraActa`).
  - [x] **Sub-tarea 11.3 (Paridad GUI Vue 3 — Cartas Consulta y Recibo de Votación):** Implementados `useGovernanceStore` (`frontend/src/stores/governanceStore.ts`) con Catch No Destructivo, `ConsultationsListView.vue` (`/consultas`), `ConsultationDetailView.vue` (`/consultas/:id`) y `VoteReceiptModal.vue` (`<dialog closedby="any">`).
  - [x] **Sub-tarea 11.4 (Certificación QA 11X del Hito 11):** **190 pruebas unitarias en backend (`99.85%` cobertura)**, **41 suites / 83 pruebas unitarias en frontend (`99.31%` líneas, `99.06%` sentencias, `97.67%` funciones, `95.85%` ramas)**, **0 componentes huérfanos (`33/33` `.vue`)**, paridad PostgreSQL 17 (`23` tablas), actualización del Grafo AST y escenarios BDD Karate Labs (`backend/test/api_test.feature` y `frontend/test/ui_business_flow.feature`).

### Hito 12: Control de Acceso Peatonal/Vehicular (Pases QR Firmados) y Paquetería en Garita `[PENDIENTE — ESPECIFICADO]`
- **Especificación:** [`docs/specs/09_DOMINIO_ACCESOS_QR_PAQUETERIA_Y_AMENIDADES.md`](./docs/specs/09_DOMINIO_ACCESOS_QR_PAQUETERIA_Y_AMENIDADES.md) (Secciones 1, 2.1, 2.2 y 3)
- **Sub-tareas de Implementación:**
  - [ ] **Sub-tarea 12.1 (Migración 0005 y Modelos de Pases QR y Paquetería):** Modelar `PaseVisita` y `PaqueteRecibido` en `backend/src/models.py` con migración `0005_hito12_accesos_reservas.py`.
  - [ ] **Sub-tarea 12.2 (Router de Accesos QR con Nonce Anti-Replay en KeyDB y Paquetería):** Implementar `backend/src/routers/accesos.py` (`POST /api/accesos/pases`, `GET /api/accesos/pases/mios`, `DELETE /api/accesos/pases/{id}`, `POST /api/accesos/verificar-qr` con quema de `jti` en KeyDB Multi-Hilo, `POST /api/paqueteria/registrar`, `GET /api/paqueteria` y `PUT /api/paqueteria/{id}/entregar`).
  - [ ] **Sub-tarea 12.3 (Paridad GUI Vue 3 — Pases QR, Garita y Paquetería):** Implementar `useAccessAmenitiesStore`, `VisitorPassesView.vue` (`/accesos/pases`), `GatehouseScannerView.vue` (`/operaciones/garita-qr`) y `ParcelsTrackerView.vue` (`/operaciones/paqueteria`).
  - [ ] **Sub-tarea 12.4 (Certificación QA 11X del Hito 12):** Pruebas unitarias en Docker efímero, paridad PostgreSQL 17, Grafo AST y escenarios BDD Karate Labs.

### Hito 13: Reserva de Áreas Sociales Vinculada a Solvencia e Inspección Post-Evento `[PENDIENTE — ESPECIFICADO]`
- **Especificación:** [`docs/specs/09_DOMINIO_ACCESOS_QR_PAQUETERIA_Y_AMENIDADES.md`](./docs/specs/09_DOMINIO_ACCESOS_QR_PAQUETERIA_Y_AMENIDADES.md) (Secciones 2.3, 4 y 5)
- **Sub-tareas de Implementación:**
  - [ ] **Sub-tarea 13.1 (Modelos y Router de Reserva de Áreas Sociales con Bloqueo por Morosidad):** Modelar `AreaSocial` y `ReservaAreaSocial` e implementar `backend/src/routers/reservas.py` (`POST/GET /api/reservas/areas`, `POST /api/reservas/solicitar` exigiendo deuda cero en `Recibo` y creando automáticamente `TareaDiaria` de inspección post-evento, y `PUT /api/reservas/{id}/inspeccionar`).
  - [ ] **Sub-tarea 13.2 (Paridad GUI Vue 3 — Reserva de Amenidades):** Implementar `AmenitiesReservationView.vue` (`/reservas/areas`) integrada en `useAccessAmenitiesStore`.
  - [ ] **Sub-tarea 13.3 (Certificación QA 11X del Hito 13):** Pruebas unitarias ($\ge 95\%$), paridad ORM ↔ Alembic de las 24 tablas totales del sistema, Grafo AST y escenarios BDD Karate Labs.

### Hito 14: Ayuda Contextual en Cada Pantalla y Manuales Editables en Markdown (Admin/Instalador y Usuario) `[PENDIENTE — ESPECIFICADO]`
- **Especificación:** [`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md) (Sección 6)
- **Sub-tareas de Implementación:**
  - [ ] **Sub-tarea 14.1 (Catálogo de Ayuda Contextual por Ruta y Rol):** Implementar `frontend/src/utils/screenHelpCatalog.ts` con guías paso a paso, propósito y preguntas frecuentes para **todas las pantallas del sistema** (interfaces de Propietarios/Inquilinos/Conserje e interfaces de Administración/Tesorería/Secretaría/Vocería).
  - [ ] **Sub-tarea 14.2 (Componente Universal `ContextualHelpModal.vue` e Integración en Layout):** Implementar `frontend/src/components/layout/ContextualHelpModal.vue` (`#dialog-contextual-help`) y el botón `#btn-contextual-help` en `AppShellLayout.vue` y vistas públicas, cumpliendo accesibilidad WCAG 2.1 AA y prueba unitaria `ContextualHelpModal.unit.ts` (0 componentes huérfanos).
  - [ ] **Sub-tarea 14.3 (Manual Editable de Administrador e Instalador en Markdown):** Crear `docs/MANUAL_ADMINISTRADOR_E_INSTALADOR.md` (instalación con Docker, configuración de estructura, alícuotas y cuotas fijas, activación de Usuarios Fantasma, junta, tesorería, candado contable, cartas consulta, garita QR e instrucciones para exportar a PDF).
  - [ ] **Sub-tarea 14.4 (Manual Editable de Usuario Residente en Markdown):** Crear `docs/MANUAL_USUARIO_RESIDENTE.md` (registro, lectura del dashboard y recibos, reporte de pagos en Bs/USD, incidencias "¡Me sumo!", votación en cartas consulta, pases QR de visitas, paquetería, reservas y certificado de solvencia, listo para personalizar y convertir en PDF para enviar a los vecinos).
  - [ ] **Sub-tarea 14.5 (Certificación QA 11X del Hito 14):** Pruebas unitarias en Vitest ($\ge 95\%$), `make -C frontend qa-orphans`, actualización del Grafo AST y escenarios BDD UI en `frontend/test/ui_business_flow.feature`.

---

## 🏆 FASE 5: Certificación Integral E2E, Geometría Visual Anti-JSDOM, WCAG 2.1 AA y Lighthouse CI

### Hito 8: Certificación E2E, Geometría Visual Anti-JSDOM, WCAG 2.1 AA y Lighthouse CI (Cobertura Total Fases 1..4) `[PENDIENTE]`
- **Especificación:** [`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md) (Secciones 3 y 8)
- **Nota de Gobernanza:** Reubicado al cierre del Roadmap para auditar simultáneamente la totalidad de las vistas de identidad, finanzas, facturación LPH, solvencia, operaciones, gobernanza, accesos QR, reservas y ayuda contextual.
- **Sub-tareas de Certificación:**
  - [ ] **Sub-tarea 8.1 (Playwright E2E y Geometría Visual Anti-JSDOM):** Ejecutar suites `.e2e.ts` en Chromium headless validando flujos de negocio de los Hitos 5 al 14 y verificando con `getBoundingClientRect()` en viewports móviles (`375x667`, `390x844`) que ningún botón primario, FAB o `AppFooter` quede oculto tras el `BottomNavBar`.
  - [ ] **Sub-tarea 8.2 (Auditoría WCAG 2.1 AA y Regresión Visual):** Certificar **0 violaciones** `critical` o `serious` con `@axe-core/playwright` tanto en tema claro como en tema oscuro, y validar snapshots visuales (`maxDiffPixelRatio: 0.02`).
  - [ ] **Sub-tarea 8.3 (Karate UI y Lighthouse CI):** Certificar `make qa-ui-bdd` (`frontend/test/ui_business_flow.feature`) y `make qa-lighthouse` (Performance $\ge 90\%$, Accessibility $\ge 95\%$, Best Practices $\ge 95\%$).
