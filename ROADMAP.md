# 🗺️ Control de Tareas y Roadmap — Condominio App

**Estándar de Ingeniería:** Gobernanza y Calidad Nivel 11X (`Rule Zero` — 100% Docker Efímero)  
**Especificaciones Técnicas Base:** [`docs/specs/README.md`](./docs/specs/README.md)

---

## 📊 Tabla Resumen de Hitos

| Hito | Dominio / Alcance | Especificación | Estado | Progreso |
| :--- | :--- | :--- | :--- | :--- |
| **Hito 1** | Setup Base y Modelos de Datos (Fase 1) | `02_DOMINIO_IDENTIDAD...` | ✅ Completado | `100%` |
| **Hito 2** | Autenticación, Ciclo de Vida JWT e Idempotencia (Fase 1) | `01_ARQUITECTURA_Y_SEGURIDAD...` | ✅ Completado | `100%` |
| **Hito 3** | Finanzas, Cobranzas y Candado Contable (Fase 1) | `03_DOMINIO_FINANZAS...` | ✅ Completado | `100%` |
| **Hito 3.5** | Gobernanza `.agents/`, Seguridad 11X y Specs Base (Fase 1) | `01_ARQUITECTURA_Y_SEGURIDAD...` | ✅ Completado | `100%` |
| **Hito 4** | Módulos Operativos, Estructura, Incidencias y Worker Base (Fase 1) | `04_DOMINIO_OPERACIONES...` | ✅ Completado | `100%` |
| **Hito 5** | Base Arquitectónica Frontend Vue 3 y Flujos de Identidad (Fase 2) | `05_ARQUITECTURA_GUI...` | ✅ Completado | `100%` |
| **Hito 6** | Vistas Financieras, Wizard de Pagos y Tesorería (Fase 2) | `03_DOMINIO_FINANZAS...` | ✅ Completado | `100%` |
| **Hito 7** | Vistas Administrativas, Incidencias y Conserjería (Fase 2) | `04_DOMINIO_OPERACIONES...` | ✅ Completado | `100%` |
| **Hito 9** | Ingeniería del Caos, Contratos Schemathesis y DAST ZAP (Fase 3) | `01_ARQUITECTURA_Y_SEGURIDAD...` | ✅ Completado | `100%` |
| **Hito 10** | Alícuotas, Facturación Trimodal LPH, Fondos y Solvencia (Fase 4) | `07_DOMINIO_ALICUOTAS...` | ✅ Completado | `100%` |
| **Hito 11** | Gobernanza Digital, Cartas Consulta (Art. 23 LPH) y Voto HMAC (Fase 4) | `08_DOMINIO_GOBERNANZA...` | ✅ Completado | `100%` |
| **Hito 12** | Pases QR Firmados con Anti-Replay KeyDB y Paquetería (Fase 4) | `09_DOMINIO_ACCESOS_QR...` | ✅ Completado | `100%` |
| **Hito 13** | Reserva de Áreas Sociales Vinculada a Solvencia e Inspección (Fase 4) | `09_DOMINIO_ACCESOS_QR...` | ✅ Completado | `100%` |
| **Hito 14** | Ayuda Contextual en Cada Pantalla y Manuales en Markdown (Fase 4) | `05_ARQUITECTURA_GUI...` | ✅ Completado | `100%` |
| **Hito 16** | Gobernanza Thin-Repo v2.20.3, Grafo AST `--code-only`, Saneamiento QA/CI y Docs (Fase 5) | `12_GOBERNANZA_DESPLIEGUE...` | ✅ Completado | `100%` |
| **Hito 17** | Endurecimiento `--no-dev`, Seguridad Real, Concurrencia LPH y Sesión/Modales (Fase 5) | `11_ENDURECIMIENTO_BACKEND...` | ✅ Completado | `100%` |
| **Hito 18** | Infraestructura Productiva Docker No-Root, Worker Real y Respaldos (Fase 5) | `12_GOBERNANZA_DESPLIEGUE...` | ✅ Completado | `100%` |
| **Hito 15** | Rediseño UX/UI "Hospitalidad Residencial", Tokens `OKLCH` y Transiciones (Fase 4) | `10_DISENO_UX_UI_AMIGABLE...` | ✅ Completado | `100%` |
| **Hito 8** | Certificación Integral E2E, Geometría Anti-JSDOM, WCAG 2.1 AA y Lighthouse CI (Fase 6) | `05_ARQUITECTURA_GUI...` | ✅ Completado | `100%` |
| **Hito 19** | Contención Operativa, Gobernanza v3.1.0 y Docker Hub Multi-Arch (Fase 7) | `13_REMEDIACION_INTEGRAL...` | ✅ Completado | `100%` |
| **Hito 20** | Defensa PG17 RLS Single-Condo, HKDF/JWT, KeyDB y RBAC/IDOR (Fase 7) | `13_REMEDIACION_INTEGRAL...` | ✅ Completado | `100%` |
| **Hito 21** | Exactitud Contable LPH, Idempotencia con Replay y Worker Real (Fase 7) | `13_REMEDIACION_INTEGRAL...` | ✅ Completado | `100%` |
| **Hito 22** | Rescate Frontend Mobile-First, Shell Unificado y WCAG 2.2 AA (Fase 7) | `13_REMEDIACION_INTEGRAL...` | ✅ Completado | `100%` |
| **Hito 23** | Erradicación Anti-Mock Blindness QA 11X y Docs Thin-Repo (Fase 7) | `13_REMEDIACION_INTEGRAL...` | ✅ Completado | `100%` |
| **Hito 24** | Recuperación de Contraseña, Multi-Inmueble y Estacionamientos/Maleteros (Fase 8) | `13_REMEDIACION_INTEGRAL...` | ⏳ Pendiente | `0%` |
| **Hito 25** | Motor PDF + Envío SMTP y Código QR Gráfico con Escáner de Cámara (Fase 8) | `13_REMEDIACION_INTEGRAL...` | ⏳ Pendiente | `0%` |
| **Hito 26** | Notificaciones en Vivo por WebSocket (`/ws/`) y Cierre `v1.2.0` (Fase 8) | `13_REMEDIACION_INTEGRAL...` | ⏳ Pendiente | `0%` |

- **Leyenda:**
  - `✅ Completado` = Hito certificado bajo el estándar QA Nivel 11X en contenedores Docker efímeros (`>= 95%` cobertura, 0 errores SAST/lint/complejidad, paridad Alembic↔ORM en PostgreSQL 17 y escenarios BDD Karate Labs).
  - `🚧 En Progreso` = Hito en ejecución activa con sub-tareas parcialmente completadas y trazadas en `.agents/ACTIVE_TASK.md`.
  - `⏳ Pendiente` = Hito con especificación cerrada en `docs/specs/`, listo para implementación.

---

> **🏗️ FASE 1: Backend Base, Seguridad 11X y Dominios Core (`backend/`) — `[100% COMPLETADA]`**

## ✅ Hito 1: Setup Base y Modelos de Datos
- **Especificación:** [`docs/specs/02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md`](./docs/specs/02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md)
- **Implementación:**
  - [x] Creación de `src/main.py` con instrumentación Prometheus (`/metrics` excluido del contrato OpenAPI público) y endpoint `/health`.
  - [x] Configuración de SQLAlchemy 2.0 asíncrono (`asyncpg` / `aiosqlite`) y migraciones Alembic.
  - [x] Modelado de `Usuario`, `Estructura`, `Unidad` e histórico `ContratoOcupacion`.
- **Certificación QA 11X:**
  - [x] Pruebas unitarias aisladas en `tests/test_main.unit.py`, `tests/test_models.unit.py` y `tests/test_schemas.unit.py`.

## ✅ Hito 2: Autenticación, Ciclo de Vida JWT e Idempotencia
- **Especificación:** [`docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md`](./docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md), [`docs/specs/02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md`](./docs/specs/02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md)
- **Implementación:**
  - [x] Rutas `POST /api/auth/register` (creación de Usuarios Fantasma con `es_activo=False`, exigiendo `Idempotency-Key`), `POST /api/auth/login` y `GET /api/auth/me`.
  - [x] Emisión de JWT HS256 en cookie `HttpOnly` (`SameSite=Lax`) y soporte dual para encabezado `Authorization: Bearer`.
- **Certificación QA 11X:**
  - [x] Pruebas unitarias en `tests/test_auth.unit.py` y `tests/test_dependencies.unit.py` cubriendo fallos de BD, expiración/adulteración de JWT y conflictos 409 de idempotencia.

## ✅ Hito 3: Finanzas, Cobranzas y Candado Contable
- **Especificación:** [`docs/specs/03_DOMINIO_FINANZAS_COBRANZAS_Y_CANDADO.md`](./docs/specs/03_DOMINIO_FINANZAS_COBRANZAS_Y_CANDADO.md)
- **Implementación:**
  - [x] Núcleo matemático puro (`src/finanzas.py`) con aritmética `Decimal` exacta (`ROUND_HALF_UP`), conversión multimoneda USD/VES y fronteras de abono parcial vs pago total.
  - [x] Flujo idempotente `POST /api/pagos/reportar`, aprobación `PUT /api/pagos/{id}/aprobar`, rechazo auditado `PUT /api/pagos/{id}/rechazar` y listado `GET /api/pagos/revision`.
  - [x] Gestión de tasas BCV (`POST/GET /api/finanzas/tasa`), egresos (`POST /api/finanzas/egresos`), resumen (`GET /api/finanzas/resumen`) e inmutabilidad del **Candado Contable** (`POST /api/finanzas/cierre-mensual`) con `RegistroAuditoria`.
- **Certificación QA 11X:**
  - [x] Pruebas de frontera estrictas en `tests/test_finanzas_core.unit.py`, `tests/test_pagos.unit.py` y `tests/test_finanzas_router.unit.py`.

## ✅ Hito 3.5: Gobernanza `.agents/`, Endurecimiento de Seguridad 11X y Especificaciones de Dominio
- **Especificación:** [`docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md`](./docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md)
- **Implementación:**
  - [x] Gobernanza de agentes IA en `AGENTS.md`, `SECURITY.md`, `.agents/rules/` y `.agents/scripts/` (certificación de cierre, paridad Alembic↔ORM en PostgreSQL 17, cero componentes Vue huérfanos, salud topológica y radio de impacto).
  - [x] Migración de hashing de contraseñas a `PBKDF2-HMAC-SHA256` con sal criptográfica de 16 bytes (`100.000` iteraciones) y comparación en tiempo constante (`hmac.compare_digest`).
  - [x] Defensas híbridas SPA+API en `src/security.py`, `src/redis_client.py` y `src/main.py`: CSRF HMAC-SHA256, Anti-SSRF con pre-resolución DNS, lectura segura de uploads por chunks (`2 MB`), validación de `Origin` en WebSockets, claves de idempotencia aisladas (`idemp:{scope}:{key}`), periodo de gracia de `5s` para rotación de refresh tokens, `ConfigDict(extra="forbid")`, ocultamiento de `/docs` en producción y sanitización de errores `422`.
  - [x] Actualización de `backend/docker-compose.qa.yml` con **KeyDB Multi-Hilo** (`eqalpha/keydb:alpine --server-threads 2`) y **PostgreSQL 17** (`postgres:17-alpine`) para `make qa-parity`.
  - [x] Creación de manuales `docs/qa/01..04` y especificaciones base en `docs/specs/`.
- **Certificación QA 11X:**
  - [x] Suite unitaria `tests/test_security_11x.unit.py`, paridad `make qa-parity` en PostgreSQL 17 y 7 escenarios BDD iniciales en `backend/test/api_test.feature`.

## ✅ Hito 4: Módulos Operativos, Estructura, Incidencias y Tareas Asíncronas
- **Especificaciones:** [`docs/specs/02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md`](./docs/specs/02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md), [`docs/specs/04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md`](./docs/specs/04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 4.1 (Estructura, Activación de Usuarios Fantasma y Junta):** Implementados `GET /api/estructura/unidades`, `POST /api/estructura/generar`, `GET /api/usuarios/pendientes`, `PUT /api/usuarios/{id}/asignar` y `PUT /api/junta/cargos` en `backend/src/routers/administracion.py`.
  - [x] **Sub-tarea 4.2 (Embudo de Incidencias Vecinales y Cuota de 30 Fotos/Mes):** Modeladas las 7 tablas operativas en `backend/src/models.py` con migración `0002_hito4_operaciones.py`, `backend/src/routers/incidencias.py` y `backend/src/routers/operaciones.py`.
  - [x] **Sub-tarea 4.3 (Checklist del Conserje, Bitácora y Comunicados):** Implementados endpoints de plantillas, tareas diarias, actas de bitácora y comunicados protegidos con Anti-SSRF.
  - [x] **Sub-tarea 4.4 (Worker Asíncrono AVIF y Notificaciones Base):** Implementado `backend/src/worker.py` (`convertir_y_subir_avif`, `encolar_notificacion_correo`, `generar_tareas_diarias_desde_plantillas`).
  - [x] **Sub-tarea 4.5 (Certificación QA 11X del Hito 4):** Suite unitaria `tests/test_hito4_operaciones.unit.py` (159 pruebas totales, 99.83% cobertura), paridad PostgreSQL 17 (17 tablas) y 10 escenarios BDD en `backend/test/api_test.feature`.

---

> **📱 FASE 2: Frontend Vue 3 Mobile-First (`frontend/`) — `[100% COMPLETADA]`**  
> Regla rectora: cumplir [`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md) (cero componentes `.vue` huérfanos, Catch No Destructivo en Pinia y geometría in-flow Anti-JSDOM).

## ✅ Hito 5: Base Arquitectónica Frontend, Seguridad Cliente y Flujos de Identidad
- **Especificación:** [`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md) (Secciones 1, 2, 3, 5, 6 y 8)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 5.1 (Scaffolding Efímero y Orquestación QA):** Inicializado `frontend/` con Vue 3 (`<script setup lang="ts">`), Vite, Pinia, Vue Router y TypeScript Strict (`docker-compose.qa.yml`, `pnpm-workspace.yaml`, `vitest.config.ts`, `playwright.config.ts`, `stryker.conf.json`).
  - [x] **Sub-tarea 5.2 (Seguridad Cliente y Cliente HTTP Resiliente):** Implementados `security.ts`, `useIdempotency.ts` y `apiClient.ts`.
  - [x] **Sub-tarea 5.3 (Layout Mobile-First Anti-JSDOM):** Implementados `AppShellLayout.vue`, `BottomNavBar.vue`, `SidebarNav.vue`, `AppFooter.vue` y `StaleDataBanner.vue`.
  - [x] **Sub-tarea 5.4 (Store de Autenticación y Vistas de Identidad):** Implementado `useAuthStore`, guardias de navegación en `router/index.ts` y vistas `LoginView.vue`, `RegisterView.vue`, `PendingApprovalView.vue` y `DashboardView.vue`.
  - [x] **Sub-tarea 5.5 (Certificación QA 11X del Hito 5):** 15 suites Vitest (100% líneas/sentencias), 0 componentes huérfanos (`10/10`), 0 errores en `vue-tsc`/`eslint` y escenarios iniciales BDD/E2E.

## ✅ Hito 6: Vistas Financieras, Wizard de Pagos y Mesa de Tesorería
- **Especificación:** [`docs/specs/03_DOMINIO_FINANZAS_COBRANZAS_Y_CANDADO.md`](./docs/specs/03_DOMINIO_FINANZAS_COBRANZAS_Y_CANDADO.md), [`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md) (Secciones 4, 6 y 7)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 6.1 (Store Financiero No Destructivo):** Implementado `useFinanceStore` (`financeStore.ts`) preservando estado con `isStale = true`.
  - [x] **Sub-tarea 6.2 (Dashboard Financiero de Propietario):** Actualizado `DashboardView.vue` con `ClosingBanner.vue`, `AnnouncementsCarousel.vue`, `CollectionTrafficLight.vue` y `ExpensesDonutChart.vue`.
  - [x] **Sub-tarea 6.3 (Wizard de Pagos Idempotente en 3 Pasos):** Implementado `PaymentWizardView.vue` (`/finanzas/reportar-pago`).
  - [x] **Sub-tarea 6.4 (Mesa de Revisión de Pagos y Candado Contable):** Implementados `TreasuryPaymentsView.vue`, `RejectPaymentModal.vue` y `TreasuryClosingView.vue`.
  - [x] **Sub-tarea 6.5 (Certificación QA 11X del Hito 6):** 24 suites Vitest (`50/50`), 0 componentes huérfanos (`18/18`) y escenarios BDD en `frontend/test/ui_business_flow.feature`.

## ✅ Hito 7: Vistas Administrativas, Embudo de Incidencias y Conserjería
- **Especificaciones:** [`docs/specs/04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md`](./docs/specs/04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md), [`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md) (Sección 4)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 7.1 (Constructor de Estructura, Activación de Usuarios Fantasma y Junta):** Implementadas `AdminStructureView.vue`, `AdminGhostUsersView.vue` y `AdminBoardRolesView.vue` con `useOperationsStore`.
  - [x] **Sub-tarea 7.2 (Embudo de Incidencias Vecinales y Galería de Voceros):** Implementadas `IncidentsFeedView.vue` (`IncidentCard.vue`), `SpokespersonGalleryView.vue` y `SecretaryLogbookView.vue`.
  - [x] **Sub-tarea 7.3 (Checklist Operativo del Conserje):** Implementadas `OperationsTasksView.vue` y `TaskChecklistItem.vue`.
  - [x] **Sub-tarea 7.4 (Grafo AST Base y Certificación QA 11X del Hito 7):** 34 suites Vitest (`70/70`), 0 componentes huérfanos (`27/27`) y `0` violaciones topológicas AST.

---

> **🛡️ FASE 3: Resiliencia Extrema e Ingeniería del Caos Nivel 11X — `[100% COMPLETADA]`**

## ✅ Hito 9: Ingeniería del Caos, Contratos OpenAPI y DAST
- **Especificación:** [`docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md`](./docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md)
- **Certificación Ejecutada:**
  - [x] `make qa-chaos` (Pumba + Locust + Prometheus): **2.786 peticiones** bajo latencia `netem` ($500\text{ ms} \pm 50\text{ ms}$), **0 fallos** ($p99 \approx 1.4\text{ s}$).
  - [x] `make qa-contracts` (Schemathesis): **626/626 casos** OpenAPI aprobados con 0 fallos.
  - [x] `make qa-dast` (OWASP ZAP): **FAIL-NEW: 0** (66 reglas aprobadas).

---

> **🏛️ FASE 4: Evolución Funcional PropTech, LPH, Ayuda Contextual y UX/UI Amigable (Hitos 10 al 15) — `[100% COMPLETADA]`**

## ✅ Hito 10: Motor de Alícuotas, Facturación Mensual LPH, Fondos y Solvencia Digital
- **Especificaciones:** [`docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md`](./docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md), [`docs/specs/07_DOMINIO_ALICUOTAS_FACTURACION_Y_SOLVENCIA.md`](./docs/specs/07_DOMINIO_ALICUOTAS_FACTURACION_Y_SOLVENCIA.md)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 10.1 (Magic Bytes, Revocación KeyDB y Anti-Fraude Referencias):** Implementado `validate_file_magic_bytes`, `revoked_user:{id}` y bloqueo `409 Conflict` ante reutilización de `(metodo, numero_referencia)`.
  - [x] **Sub-tarea 10.2 (Migración 0003 y Modelos LPH):** Extendidos `Unidad` y `Egreso`; creados `FondoCondominio`, `ReciboItem` y `CertificadoSolvencia` (20 tablas en PostgreSQL 17).
  - [x] **Sub-tarea 10.3 (Facturación Trimodal y Solvencia HMAC):** Método de Hamilton (`prorratear_por_alicuotas`), `CUOTA_FIJA`, `PARTES_IGUALES`, acreditación de sobrepagos y firma `HMAC-SHA256` de solvencias.
  - [x] **Sub-tarea 10.4 (Paridad GUI Vue 3):** Implementados `BillingGeneratorView.vue`, `ReceiptBreakdownModal.vue`, `SolvencyCertificateView.vue` y edición de alícuota/cuota fija en `AdminStructureView.vue`.
  - [x] **Sub-tarea 10.5 (Certificación QA 11X del Hito 10):** 182 tests backend (`99.83%`), 37 suites frontend (`75` tests, `30/30` `.vue`), paridad PostgreSQL 17 y BDD Karate Labs.

## ✅ Hito 11: Gobernanza Digital, Cartas Consulta (Art. 23 LPH) y Asambleas con Voto Criptográfico
- **Especificación:** [`docs/specs/08_DOMINIO_GOBERNANZA_CARTAS_CONSULTA_Y_ASAMBLEAS.md`](./docs/specs/08_DOMINIO_GOBERNANZA_CARTAS_CONSULTA_Y_ASAMBLEAS.md)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 11.1 (Migración 0004 y Modelos de Gobernanza LPH):** Añadido `puede_votar_asamblea` en `ContratoOcupacion` y modelados `ConsultaComunitaria`, `OpcionConsulta` y `VotoConsulta` (23 tablas en PostgreSQL 17).
  - [x] **Sub-tarea 11.2 (Router de Consultas, Firma HMAC-SHA256 y Acta Automática):** Implementado `backend/src/routers/consultas.py` con voto ponderado y cierre con asiento en `BitacoraActa`.
  - [x] **Sub-tarea 11.3 (Paridad GUI Vue 3):** Implementados `useGovernanceStore`, `ConsultationsListView.vue`, `ConsultationDetailView.vue` y `VoteReceiptModal.vue`.
  - [x] **Sub-tarea 11.4 (Certificación QA 11X del Hito 11):** 190 tests backend (`99.85%`), 41 suites frontend (`83` tests, `33/33` `.vue`), paridad PostgreSQL 17 y BDD Karate Labs.

## ✅ Hito 12: Control de Acceso Peatonal/Vehicular (Pases QR Firmados) y Paquetería en Garita
- **Especificación:** [`docs/specs/09_DOMINIO_ACCESOS_QR_PAQUETERIA_Y_AMENIDADES.md`](./docs/specs/09_DOMINIO_ACCESOS_QR_PAQUETERIA_Y_AMENIDADES.md) (Secciones 1, 2.1, 2.2 y 3)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 12.1 (Migración 0005 y Modelos):** Modelados `PaseVisita` y `PaqueteRecibido` (25 tablas en PostgreSQL 17).
  - [x] **Sub-tarea 12.2 (Router de Accesos QR con Anti-Replay KeyDB y Paquetería):** Implementado `backend/src/routers/accesos.py` con nonce `qr_used:{jti}` y verificación `HMAC-SHA256`.
  - [x] **Sub-tarea 12.3 (Paridad GUI Vue 3):** Implementados `useAccessAmenitiesStore`, `VisitorPassesView.vue`, `GatehouseScannerView.vue` y `ParcelsTrackerView.vue`.
  - [x] **Sub-tarea 12.4 (Certificación QA 11X del Hito 12):** 208 tests backend (`99.83%`), 45 suites frontend (`91` tests, `36/36` `.vue`), paridad PostgreSQL 17 y `17/17` escenarios BDD API.

## ✅ Hito 13: Reserva de Áreas Sociales Vinculada a Solvencia e Inspección Post-Evento
- **Especificación:** [`docs/specs/09_DOMINIO_ACCESOS_QR_PAQUETERIA_Y_AMENIDADES.md`](./docs/specs/09_DOMINIO_ACCESOS_QR_PAQUETERIA_Y_AMENIDADES.md) (Secciones 2.3, 4 y 5)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 13.1 (Migración 0006, Modelos y Router):** Modelados `AreaSocial` y `ReservaAreaSocial` (27 tablas en PostgreSQL 17) y router `backend/src/routers/reservas.py` con bloqueo por morosidad y tarea automática de inspección.
  - [x] **Sub-tarea 13.2 (Paridad GUI Vue 3):** Implementada `AmenitiesReservationView.vue` (`/reservas/areas`).
  - [x] **Sub-tarea 13.3 (Certificación QA 11X del Hito 13):** 215 tests backend (`99.85%`), 46 suites frontend (`94` tests, `37/37` `.vue`), paridad 27 tablas y `19/19` escenarios BDD API.

## ✅ Hito 14: Ayuda Contextual en Cada Pantalla y Manuales Editables en Markdown
- **Especificación:** [`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md) (Sección 6)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 14.1 (Catálogo de Ayuda Contextual):** Implementado `screenHelpCatalog.ts` y `screenHelpCatalog.unit.ts` (100% cobertura).
  - [x] **Sub-tarea 14.2 (Modal `ContextualHelpModal.vue`):** Implementado `#dialog-contextual-help` e integrado en `AppShellLayout.vue` y vistas públicas (`38/38` `.vue`).
  - [x] **Sub-tarea 14.3 (Manual de Administrador e Instalador):** Creado `docs/MANUAL_ADMINISTRADOR_E_INSTALADOR.md`.
  - [x] **Sub-tarea 14.4 (Manual de Usuario Residente):** Creado `docs/MANUAL_USUARIO_RESIDENTE.md`.
  - [x] **Sub-tarea 14.5 (Certificación QA 11X del Hito 14):** 48 suites frontend (`108` tests, `38/38` `.vue`), 215 tests backend (`99.85%`) y Escenario 9 en `frontend/test/ui_business_flow.feature`.

---

> **🔧 FASE 5: Saneamiento de Gobernanza, Endurecimiento Real y Despliegue Productivo (Hitos 16, 17 y 18 — Specs 11 y 12) — `[100% COMPLETADA]`**

## ✅ Hito 16: Gobernanza Thin-Repo v2.20.3, Higiene AST `--code-only`, Bloqueadores 11X y Saneamiento CI/Scripts
- **Especificación:** [`docs/specs/12_GOBERNANZA_DESPLIEGUE_PRODUCTIVO_Y_CI_11X.md`](./docs/specs/12_GOBERNANZA_DESPLIEGUE_PRODUCTIVO_Y_CI_11X.md) (Sección 1)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 16.0 (Reconciliación Thin-Repo `@sinfallas/mcp-qa-11x` v2.20.3):** Ejecutado `npx -y @sinfallas/mcp-qa-11x@latest install-skill --init-agents --include-scripts --reconcile`, podadas reglas duplicadas hacia `.agents/rules/domain_condominio_app_rules.md` y saneados enlaces en `AGENTS.md`, `.agents/README.md`, `.trivy.yaml` y `commitlint.config.js`.
  - [x] **Sub-tarea 16.1 (Remediación de 20 Bloqueadores `HIGH` — `QA-KARATE-IDEMP` y `SEC-09`):** Añadido `ignore-scripts=true` en `.npmrc` raíz y `frontend/.npmrc`, corregidos permisos de `frontend/pnpm-workspace.yaml` y reemplazados los 18 UUIDs literales en `backend/test/api_test.feature` por `java.util.UUID.randomUUID() + ''` con datos únicos por escenario.
  - [x] **Sub-tarea 16.2 (Higiene AST `--code-only`, `.gitignore` y Purga Host `Rule Zero`):** Desindexado `graphify-out/` de Git, eliminados daemons `:8080` de `docker-compose.qa.yml`, regenerado el grafo AST con `./scripts/actualizar-grafos-graphify.sh --all` (`--code-only`) y purgados artefactos locales del host mediante `clean_workspace_11x`.
  - [x] **Sub-tarea 16.3 (Saneamiento de Scripts, `Makefile`s, `lighthouserc.cjs`, `lefthook.yml` y Workflows CI):** Corregido `scripts/limpieza.sh` (sin `sudo`, sin `docker system prune --volumes` y preservando `zap.yaml`), migrado `lighthouserc.js` a `lighthouserc.cjs`, creado `Makefile` raíz, corregidos `backend/Makefile` / `frontend/Makefile` bajo `Rule Zero` (`mypy --strict`, `pnpm run build`, UID/GID no-root, sin `python3` en host), y endurecidos `auditar-infra.sh`, `lefthook.yml` y `.github/workflows/00..02`.
  - [x] **Sub-tarea 16.4 (Sincronización Documental Integral):** Creadas `Spec 11` y `Spec 12`, sincronizados `README.md`, `SECURITY.md`, `docs/qa/README.md`, `docs/ARCHITECTURE.md`, `docs/API_ROUTES.md`, `docs/MANUAL_ADMINISTRADOR_E_INSTALADOR.md`, `docs/specs/README.md`, `CHANGELOG.md`, `TESTING.md` y `backend/TESTING.md`, y certificado el gate `certify_11x_gate` (`10/10`).

## ✅ Hito 17: Endurecimiento Backend (`--no-dev`), Seguridad Real, Concurrencia LPH y Sesión/Modales Frontend
- **Especificación:** [`docs/specs/11_ENDURECIMIENTO_BACKEND_CONCURRENCIA_Y_SEGURIDAD_REAL.md`](./docs/specs/11_ENDURECIMIENTO_BACKEND_CONCURRENCIA_Y_SEGURIDAD_REAL.md)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 17.1 (Empaquetado Productivo `--no-dev`, Fail-Fast Prod y KDF Estricto):** Movidos `prometheus-fastapi-instrumentator` y `prometheus-client` a `[project].dependencies` en `backend/pyproject.toml` (retirado `passlib[bcrypt]`, regenerado `uv.lock`), implementada `validate_production_security_settings()` en `backend/src/security.py` y `lifespan`, retirado el fallback `SHA-256` sin sal en `verify_password` y certificadas las pruebas unitarias y arranque `--no-dev` en Docker.
  - [x] **Sub-tarea 17.2 (Ciclo de Sesión Completo, CSRF Real, Rate-Limiting y KeyDB Fail-Closed):** Implementar `POST /api/auth/logout`, `POST /api/auth/refresh`, validación real de `X-CSRF-Token` y sincronización en `apiClient.ts`, lockout `5/15m` + anti-timing en `/login`, `cedula`/`telefono`/`unidad_activa_id` en `/api/auth/me`, fail-closed en KeyDB en producción, TTL `86400s` en idempotencia, hidratación inicial de sesión en Vue Router, expiración `401` uniforme + `StaleDataBanner` en los 5 stores, apertura real con `showModal()` sin `open` estático en los 4 `<dialog>`, rutas de tesorería + filtrado RBAC en `SidebarNav.vue` y periodo dinámico + `ownUnitId` en `DashboardView.vue`.
  - [x] **Sub-tarea 17.3 (Concurrencia Financiera, Candado Contable, Anti-IDOR y Exactitud LPH):** Exigir `Idempotency-Key` + `with_for_update()` en `PUT /api/pagos/{id}/aprobar`, validar titularidad activa `ContratoOcupacion` (anti-IDOR) en `POST /api/pagos/reportar`, bloquear `POST /api/finanzas/egresos` cuando `ReporteMensual.estado == "CERRADO"`, añadir `UniqueConstraint(unidad_id, periodo)` (`uq_recibo_unidad_periodo`) e índice único parcial `uq_pagos_metodo_ref_activo` (migración `0007_hito17_unicidad_finanzas`), extraer `src/facturacion_lph.py`, prorratear cuotas extraordinarias según modalidad `ALICUOTA`, validar `validar_suma_alicuotas` antes de cargos variables, usar `Decimal(2)/Decimal(3)` exacto en `DOS_TERCIOS` y enviar `Idempotency-Key` en `financeStore.ts` (`236/236` unitarios `99.11%`, `22/22` Karate Labs).
  - [x] **Sub-tarea 17.4 (Integridad en Gobernanza, Reservas, Administración y SQL):** Validada `fecha_cierre` (`409`) y bloqueo `.with_for_update()` al votar/cerrar consultas, incorporado `jti` UUIDv4 en `VotoConsulta`/`CertificadoSolvencia` y verificación dinámica de deuda viva en `GET /api/finanzas/solvencia/verificar/{folio}`; sustituida unicidad de `ReservaAreaSocial` por índice único parcial `uq_reserva_area_fecha_activa` (`WHERE estado != 'CANCELADA'`), implementados `PUT /api/reservas/{reserva_id}/cancelar` + `accessAmenitiesStore.cancelarReserva` + `AmenitiesReservationView.vue` y cargo atómico (`Recibo` + `ReciboItem` `DANOS_AREA_SOCIAL` + `AuditoriaRecibo`) en `FINALIZADA_CON_DANOS`; restringido `GET /api/estructura/unidades` a `UnidadPublicaResponse` para anónimos/Fantasmas, preservado histórico en `ContratoOcupacion` (`fecha_fin`), restringidos cargos de Junta a propietarios vigentes sin `fecha_fin`, eliminados `SELECT *` en RAM/N+1 y activadas políticas RLS multi-tenant PG17 (`condominio_id`, `FORCE ROW LEVEL SECURITY` en 27 tablas, migración `0008_hito17_integridad_y_rls`).
  - [x] **Sub-tarea 17.5 (Certificación QA 11X del Hito 17):** Certificadas `241/241` pruebas backend (`97.07%` global, `0 skipped` con `POSTGRES_TEST_URL` validando 27 políticas RLS PG17 y ciclo `upgrade head -> downgrade base -> upgrade head`), arranque `--no-dev`, `48/48` suites frontend (`117/117`, `99.52%` líneas, `0/38` huérfanos), `2/2` corridas Karate Labs (`23/23` escenarios) y AST Graphify (`0` violaciones topológicas).

## ✅ Hito 18: Infraestructura Productiva Docker Multi-Stage No-Root, Worker Real y Respaldos Automatizados (Completado — 100%)
- **Especificación:** [`docs/specs/12_GOBERNANZA_DESPLIEGUE_PRODUCTIVO_Y_CI_11X.md`](./docs/specs/12_GOBERNANZA_DESPLIEGUE_PRODUCTIVO_Y_CI_11X.md) (Sección 2)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 18.1 (Dockerfiles Multi-Stage No-Root y `nginx.conf` OSHP):** Crear `backend/Dockerfile` (`uv sync --frozen --no-dev`, usuario `10001`), `frontend/Dockerfile` (`nginx-unprivileged`, proxy `/api` + `/health` + cabeceras OSHP) y `docker-compose.yml` productivo (`postgres:17-alpine`, `keydb` autenticado, `minio`, `api`, `worker`, `frontend`).
  - [x] **Sub-tarea 18.2 (Worker Asíncrono Ejecutable AVIF/MinIO/SMTP y `QA-HEALTH-01`):** Implementar entrypoint `python -m src.worker` con conversión AVIF real y subida a MinIO, consumidor BLPOP SMTP en KeyDB, scheduler idempotente (`UniqueConstraint` en `TareaDiaria`) y heartbeat verificable sin mocks (`QA-HEALTH-01`).
  - [x] **Sub-tarea 18.3 (Plantilla `.env.example`, Respaldos y Certificación Trivy Prod):** Crear `.env.example` de Condominio App y `scripts/backup-diario.sh` (PostgreSQL 17 + MinIO), certificar `Trivy HIGH/CRITICAL = 0` sobre imágenes y `docker-compose.yml`, y actualizar `docs/MANUAL_ADMINISTRADOR_E_INSTALADOR.md`.

---

> **✨ CONTINUACIÓN FASE 4: UX/UI Amigable — `[100% COMPLETADA]`**

## ✅ Hito 15: Rediseño UX/UI Amigable ("Hospitalidad Residencial"), Sistema de Tokens `OKLCH`, Modo Oscuro (`light-dark()`) y Micro-Transiciones Modernas
- **Especificación:** [`docs/specs/10_DISENO_UX_UI_AMIGABLE_TRANSICIONES_Y_SISTEMA_TOKENS.md`](./docs/specs/10_DISENO_UX_UI_AMIGABLE_TRANSICIONES_Y_SISTEMA_TOKENS.md) y [`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md) (Sección 7)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 15.1 (Sistema Centralizado de Tokens `OKLCH`, Modo Claro/Oscuro `light-dark()` y Sombras de 2 Capas):** Creado `frontend/src/assets/tokens.css`, importado en `main.ts`, implementado `useThemeMode.ts` (`useThemeMode.unit.ts`), `<meta name="color-scheme" content="light dark">` en `index.html` y `ThemeToggleButton.vue` (`#btn-theme-toggle`) en `AppShellLayout.vue`, `LoginView.vue` y `RegisterView.vue`.
  - [x] **Sub-tarea 15.2 (Navegación Amigable con Iconos SVG, Agrupación Semántica y Píldora Activa):** Rediseñado `SidebarNav.vue` (3 bloques semánticos con `navIcons.ts` SVG `stroke-width: 1.75` y `#btn-sidebar-theme-toggle`) y `BottomNavBar.vue` (iconos SVG + píldora activa `.bottom-nav__pill`).
  - [x] **Sub-tarea 15.3 (Dashboard Contextual "Tu Hogar Hoy", Estados Vacíos Ilustrados y Esqueletos de Carga):** Implementados `EmptyStateCard.vue`, `SkeletonCard.vue` (`CLS = 0`), Tarjeta Hero de Solvencia (`#deuda-card` + `#hero-solvencia-badge`) y `#dashboard-quick-actions` en `DashboardView.vue`, más glifos para daltónicos en `CollectionTrafficLight.vue` y `SolvencyCertificateView.vue`.
  - [x] **Sub-tarea 15.4 (Motor de Transiciones SPA, Modales `<dialog>` en Top-Layer con `@starting-style` + Bottom Sheet Móvil y `calc-size()`):** Implementado `useViewTransition.ts` (`runWithViewTransition`, detección de bug Firefox `1882408` en `canTransitionDisplay()` y `closeTopLayerDialog` con `data-closing`), restauración de foco en `router/index.ts`, `@starting-style` + `allow-discrete` + `overlay` + *Bottom Sheet* `< 640px` en los 5 `<dialog>`, tarjetas `:has(input:checked)` + fallback `.is-selected`, expansión `calc-size(auto, size)`, stepper de `PaymentWizardView.vue` y respeto estricto a `@media (prefers-reduced-motion: reduce)`.
  - [x] **Sub-tarea 15.5 (Certificación QA 11X del Hito 15):** Remediado `GHSA-7mvr-c777-76hp` actualizando `@playwright/test@1.64.1` y `ui-e2e` a `mcr.microsoft.com/playwright:v1.64.1-jammy`; certificados **`53` suites (`126/126` unitarias, `99.22%` líneas / `98.94%` sentencias / `97.75%` funciones / `95.19%` ramas)**, `41/41` `.vue` (`0` huérfanos), build Vite (`163` módulos), **`10/10` pruebas Playwright E2E + Axe** (`mobile-chromium` + `desktop-chromium` claro/oscuro y *Bottom Sheet*), Grafo AST Graphify (`3` grafos, `4.899` nodos, `12.429` relaciones, `0` violaciones) y Escenario 11 en `frontend/test/ui_business_flow.feature`.

---

> **🏆 FASE 6: Certificación Integral E2E, Geometría Visual Anti-JSDOM, WCAG 2.1 AA y Lighthouse CI — `[100% COMPLETADA]`**

## ✅ Hito 8: Certificación E2E, Geometría Visual Anti-JSDOM, WCAG 2.1 AA y Lighthouse CI (Cobertura Total Fases 1..5)
- **Especificación:** [`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md) (Secciones 3, 7 y 8) y [`docs/specs/10_DISENO_UX_UI_AMIGABLE_TRANSICIONES_Y_SISTEMA_TOKENS.md`](./docs/specs/10_DISENO_UX_UI_AMIGABLE_TRANSICIONES_Y_SISTEMA_TOKENS.md)
- **Sub-tareas de Certificación:**
  - [x] **Sub-tarea 8.1 (Playwright Screenplay E2E, Entorno Determinista y Geometría Visual Anti-JSDOM):** Configurado `frontend/nginx.qa.conf` (`/health`, CSP/OSHP, fallback `/api/estructura/unidades`) y mock stateful (`frontend/e2e/fixtures/condominioApiMock.ts`), viewports `375x667`, `390x844` y `1440x900` en `frontend/playwright.config.ts`, arquitectura Screenplay (`frontend/e2e/screenplay/`), flujos autenticados completos de Hitos 5 al 17.4 (`frontend/e2e/authenticated-flows.e2e.ts`) y auditoría `getBoundingClientRect()` / `elementsFromPoint()` verificando `0` desbordamientos horizontales y `0` oclusiones sobre controles primarios, `#fab-reportar-pago` y `#app-inflow-footer`.
  - [x] **Sub-tarea 8.2 (Auditoría WCAG 2.1 AA, Contraste Oscuro Atómico y Regresión Visual):** Reparada asimetría transicional de contraste en tema oscuro (`AppShellLayout.vue`, `SidebarNav.vue`), certificados **`0` hallazgos `critical` o `serious`** con `@axe-core/playwright` en rutas públicas, `/espera-aprobacion`, vistas autenticadas y modales Top Layer en claro/oscuro (`light-dark()`), y generados/verificados `15` baselines PNG Linux (`maxDiffPixelRatio: 0.02`, **`51/51` pass** en Playwright).
  - [x] **Sub-tarea 8.3 (Karate UI BDD vía `chrome-cdp` y Lighthouse CI):** Sidecar `chrome-cdp` headless (`127.0.0.1:9222`) habilitado en `frontend/docker-compose.qa.yml` certificando `frontend/test/ui_business_flow.feature` (**`12/12` pass**), y `make -C frontend qa-perf` (`frontend/lighthouserc.cjs`) aprobado sobre `/login` y `/register` con **99% Performance, 100% Accessibility y 100% Best Practices** (excluyendo auditorías TLS en red interna HTTP).

---

> **🛠️ FASE 7: Remediación Integral Post-Auditoría `v1.0.0` (Hitos 19 al 23 — Spec 13) — `[100% COMPLETADA]`**  
> **Política de Distribución Aprobada:** Sin publicación en `npmjs.com` (`"private": true`); distribución exclusiva en Docker Hub mediante 2 imágenes multi-arquitectura (`linux/amd64,linux/arm64`): `sinfallas/condominio-backend` y `sinfallas/condominio-frontend` para despliegues Single-Condo con PostgreSQL 17 RLS activo.

## ✅ Hito 19: Contención Operativa, Gobernanza v3.1.0 y Docker Hub Multi-Arch
- **Especificación:** [`docs/specs/13_REMEDIACION_INTEGRAL_COMPLETITUD_FUNCIONAL_Y_DOCKERHUB_11X.md`](./docs/specs/13_REMEDIACION_INTEGRAL_COMPLETITUD_FUNCIONAL_Y_DOCKERHUB_11X.md) (Sección 2.1)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 19.1 (Blindaje de `limpieza.sh`, `backup-diario.sh`, `verificar-secretos.sh` y SBOM):** Restringir `scripts/limpieza.sh` exclusivamente a `docker-compose*.qa.yml` (protegiendo `postgres_data` y `minio_data`), consolidar scripts duplicados en raíz/subcarpetas hacia `scripts/`, mover salida de `generar-sbom-cyclonedx.sh` a `artifacts/sbom/`, eliminar `|| true` silencioso y residuos `0-byte` en `scripts/backup-diario.sh` (respetando `MINIO_USE_SSL`), propagar `MINIO_USE_SSL` a `worker` y escanear el árbol completo (incluyendo `.env.example` y tests) en `scripts/verificar-secretos.sh`.
  - [x] **Sub-tarea 19.2 (Actualización Thin-Repo QA 11X `v3.1.0`, Validadores Reales y FINOS CALM):** Sincronizar `.agents/` y `AGENTS.md` con `v3.1.0` (`QA-GIT-GATE-01` sin `git push` automático, 10 skills globales e inglés conciso en `.agents/**`), ejecutar `certify_task_completion.sh` íntegramente bajo `Rule Zero` (`sinfallas/base-python-uv:3.13`), corregir falsos positivos ciegos en `verify_no_orphan_api_endpoints.py`, `verify_topological_health.py` y `verify_docs_invariants.py` (más `.trivy.yaml` y `commitlint.config.js`), crear `architecture/qa-11x.calm.json` y regenerar los 3 grafos AST (`--code-only`) purgando nodos Markdown heredados.
  - [x] **Sub-tarea 19.3 (Manifiestos, Hooks Efímeros y CI/CD Multi-Arch hacia Docker Hub):** Completar metadatos (`MIT`, `repository`, `author`, `engines`, `packageManager`) y unificar autoría (`LICENSE`, `AUTHORS.md`, `README.md`, `AGENTS.md`); unificar Python `3.13` y deduplicar grupos `dev` en `backend/pyproject.toml`; ejecutar `lefthook` + `commitlint` en contenedor efímero; añadir `--frozen`/`--frozen-lockfile` y pinning SHA-40 en `.github/workflows/00..02.yml` (`SEC-CI-ACTION-REF`); configurar pipeline buildx multi-arch (`linux/amd64,linux/arm64`) hacia `sinfallas/condominio-backend` (`CONTAINER_ROLE=api|worker`) y `sinfallas/condominio-frontend` con `docker-compose.prod.yml`; y añadir suites BATS con `kcov >= 95%`.

## ✅ Hito 20: Defensa PG17 RLS Single-Condo, HKDF/JWT, KeyDB y RBAC/IDOR
- **Especificación:** [`docs/specs/13_REMEDIACION_INTEGRAL_COMPLETITUD_FUNCIONAL_Y_DOCKERHUB_11X.md`](./docs/specs/13_REMEDIACION_INTEGRAL_COMPLETITUD_FUNCIONAL_Y_DOCKERHUB_11X.md) (Sección 2.2)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 20.1 (PG17 RLS Runtime No-Superusuario, Migración `0010` y Paridad SQLite):** Separar usuario `condominio_admin` (migraciones) de `condominio_app` (runtime) con `SET LOCAL ROLE condominio_app_runtime`, establecer `tenant_id = ""` fail-closed en `database.py`, inyectar `condominio_id` desde JWT en `dependencies.py` y `facturacion_lph.py`, activar `PRAGMA foreign_keys=ON` en SQLite y crear migración `0010_rls_multitenant_worm_checks.py` (`UNIQUE` compuestos con `condominio_id`, índices en FKs, `CheckConstraint`, `ALTER DEFAULT PRIVILEGES` y WORM `REVOKE UPDATE, DELETE` en `auditoria_recibos` y `votos_consulta`).
  - [x] **Sub-tarea 20.2 (Subclaves `HKDF-SHA256`, TTL Revocación 7d, KeyDB Fail-Closed y Anti-SSRF):** Derivar subclaves independientes en `security.py`, exigir `typ == "access"`, alinear TTL de revocación en KeyDB (`>= 7 días`) fail-closed sin fugas `_local_revoked_*` en RAM, aislar `logout` por `sid` sin borrar bloqueos admin en `login`, subir `PBKDF2 >= 600_000` en `asyncio.to_thread` con contraseñas `8..128`, implementar lockout Lua atómico (`ip` + `correo`), bloquear `javascript:`/`//` en `ComunicadoCreate` y usar DNS asíncrono normalizando minúsculas en `accesos.py`.
  - [x] **Sub-tarea 20.3 (Middleware HTTP, Cabeceras Nginx OSHP y Cierre RBAC/IDOR):** Exigir `X-CSRF-Token` cuando haya sesión por cookie, proteger `/metrics`, preservar cabeceras OSHP/CSP dentro de `location /assets/` + `gzip on` + directorios `/tmp/nginx_*_temp` en `frontend/nginx.conf`/`Dockerfile`, bloquear escalación `VICEPRESIDENTE -> PRESIDENTE`, exigir `ContratoOcupacion.fecha_fin.is_(None)` en `_verificar_acceso_unidad` y restringir exposición horizontal en `estructura/unidades`, `finanzas/resumen`, `paqueteria`, `reservas` y `accesos/pases/mios`.

## ✅ Hito 21: Exactitud Contable LPH, Idempotencia con Replay y Worker Real
- **Especificación:** [`docs/specs/13_REMEDIACION_INTEGRAL_COMPLETITUD_FUNCIONAL_Y_DOCKERHUB_11X.md`](./docs/specs/13_REMEDIACION_INTEGRAL_COMPLETITUD_FUNCIONAL_Y_DOCKERHUB_11X.md) (Sección 2.3)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 21.1 (Desbloqueo Cross-Módulo y Cuadre Contable LPH):** Resolver el deadlock `HTTP 409` integrando cargos por daños/uso de `AreaSocial` en `facturar-periodo` vía `UPSERT` de `ReciboItem`, impedir `cierre-mensual` con pagos `EN_REVISION`, añadir `with_for_update()` + `Idempotency-Key` en `rechazar_pago`, cuadrar `Recibo` vs `ReciboItem` al cubrir con `credito_disponible_usd` + `AuditoriaRecibo`, proteger `FondoCondominio` contra saldos negativos, corregir `MAYORIA_SIMPLE > 50.0000%`, `Decimal("0.00")` falsy y acotar `Decimal` (`allow_inf_nan=False`, `le`) + mes `01..12` en `schemas.py`.
  - [x] **Sub-tarea 21.2 (Idempotencia Transaccional, Paginación y Worker Resiliente):** Implementar gestor `idemp:{condominio_id}:{usuario_id}:{scope}:{key}` con *response replay* y liberación en `4xx/5xx` en las 14 mutaciones faltantes, añadir `limit`/`offset` en los 14 listados `GET` y `response_model` en los 7 endpoints restantes, conectar subida segura de comprobantes/evidencias (`read_uploaded_file_safely` + `validate_file_magic_bytes`) con `convertir_y_subir_avif`, capturar `RedisError`/JSON inválido, migrar `BLPOP` a `BLMOVE` con backoff, respetar `PlantillaTarea.frecuencia` y desacoplar `HEALTHCHECK` por `CONTAINER_ROLE`.

## ✅ Hito 22: Rescate Frontend Mobile-First, Shell Unificado y WCAG 2.2 AA
- **Especificación:** [`docs/specs/13_REMEDIACION_INTEGRAL_COMPLETITUD_FUNCIONAL_Y_DOCKERHUB_11X.md`](./docs/specs/13_REMEDIACION_INTEGRAL_COMPLETITUD_FUNCIONAL_Y_DOCKERHUB_11X.md) (Sección 2.4)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 22.1 (Aislamiento de Sesión SPA, `apiClient` y Contratos DTO):** Resetear los 5 stores Pinia + `activeCsrfToken` al cerrar sesión/`401`, endurecer `isSafeRedirectUrl` y `generateIdempotencyKey` (`crypto.getRandomValues`), soportar `FormData` + `.delete()`/`.patch()` + `try/catch` en `apiClient.ts`, reutilizar `Idempotency-Key` en reintentos, eliminar doble escapado HTML en `{{ ... }}` y alinear todos los DTOs con `schemas.py` (`url_comprobante`, `enlace_externo`, `/api/comunicados`).
  - [x] **Sub-tarea 22.2 (Ruta Padre `<AppShellLayout>` y Navegación Móvil `< 768px`):** Agrupar todas las vistas autenticadas bajo ruta padre con `<AppShellLayout>` en `router/index.ts` (corrigiendo las 6 vistas huérfanas), añadir ruta `404` (`NotFoundView.vue`), hidratación en `/login` y `/register`, *code-splitting* dinámico y cajón móvil completo (`MobileNavDrawer.vue`) más botón accesible de **Salir / Cerrar sesión** en `< 768px`.
  - [x] **Sub-tarea 22.3 (Vistas Críticas, Tokens OKLCH e Invariantes 11X):** Desacoplar `GET /api/finanzas/tasa` con `Promise.allSettled` evitando mostrar falsa solvencia, corregir el `403` de `SolvencyCertificateView.vue`, cargar recibos reales y subida real de comprobantes en `PaymentWizardView.vue`, renderizar `<img>` en galería/incidencias, visibilizar errores en vistas admin, aplicar `String(val.value ?? '').trim()` en todos los números, erradicar UUIDs/JTIs/PKs crudos y badges catch-all invertidos (`UI-11X-02`), corregir `tokens.css:555`, `ExpensesDonutChart.vue`, `CollectionTrafficLight.vue`, `<dialog>` Top-Layer (`useTopLayerDialog.ts`), colores `OKLCH` y añadir `useDualRefresh` (`setInterval` + `[ 🔄 Refrescar ]`).

## ✅ Hito 23: Erradicación Anti-Mock Blindness QA 11X y Docs Thin-Repo
- **Especificación:** [`docs/specs/13_REMEDIACION_INTEGRAL_COMPLETITUD_FUNCIONAL_Y_DOCKERHUB_11X.md`](./docs/specs/13_REMEDIACION_INTEGRAL_COMPLETITUD_FUNCIONAL_Y_DOCKERHUB_11X.md) (Sección 2.5)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 23.1 (Suites Reales Backend, Mutmut/Radon 11X, ZAP y Locust):** Crear `.unit.py` para los 5 módulos faltantes, cubrir 27 tablas y todos los esquemas dinámicamente, migrar suites de `_mock_session` a BD real (`PRAGMA foreign_keys=ON` + HTTP PG17 real + `asyncio.gather`), exigir `radon` Grado A (`MAX_GRADE = 1`), corregir `mutmut_gates.py`, activar `zap.yaml` en `make qa-dast`, reparar `locustfile.py` + sidecar `profiler` y cubrir flujos nominales `2xx` de los 9 routers en `backend/test/api_test.feature`.
  - [x] **Sub-tarea 23.2 (Suites Frontend, Mock OpenAPI, Playwright Tablet y Karate UI):** Añadir `navIcons.unit.ts` y `main.unit.ts`, ejecutar Stryker vía `qa-vue3` + `ui-e2e` ampliando módulos (`97.49%` MSI), alinear `condominioApiMock.ts` 1:1 con OpenAPI/RBAC/`404`, cubrir `23/23` vistas en `accessibility.e2e.ts`, añadir `consultation-detail-dark` + viewport Tablet `768x1024` (`24` PNGs), incluir `e2e/` en ESLint/Prettier/`tsconfig.e2e.json` y añadir flujos autenticados reales en `frontend/test/ui_business_flow.feature`.
  - [x] **Sub-tarea 23.3 (Saneamiento Documental Integral y READMEs):** Corregir comandos rotos de restauración (`api`/`worker`, `condominio_admin`, `pg17_*.dump.gz`) y rutas reales en `MANUAL_ADMINISTRADOR_E_INSTALADOR.md`, `MANUAL_USUARIO_RESIDENTE.md`, `API_ROUTES.md` y `ARCHITECTURE.md`; sincronizar `SECURITY.md` (`22` vectores), `CHANGELOG.md`, `TESTING.md`; podar `docs/qa/*` bajo Thin-Repo; actualizar `docs/specs/01..12` y rediseñar `README.md` raíz + crear `backend/README.md` y `frontend/README.md`.

---

> **✨ FASE 8: Completitud Funcional PropTech Prometida `v1.2.0` (Hitos 24 al 26 — Spec 13) — `[0% PENDIENTE]`**

## ⏳ Hito 24: Recuperación de Contraseña, Multi-Inmueble y Estacionamientos/Maleteros
- **Especificación:** [`docs/specs/13_REMEDIACION_INTEGRAL_COMPLETITUD_FUNCIONAL_Y_DOCKERHUB_11X.md`](./docs/specs/13_REMEDIACION_INTEGRAL_COMPLETITUD_FUNCIONAL_Y_DOCKERHUB_11X.md) (Sección 3.1)
- **Sub-tareas de Implementación:**
  - [ ] **Sub-tarea 24.1 (Recuperación de Contraseña Autoservicio y Junta Directiva):** Implementar `POST /api/auth/forgot-password`, `POST /api/auth/reset-password` (token de un solo uso en KeyDB `TTL <= 900s` + envío SMTP) y `POST /api/usuarios/{id}/reset-password-temporal` con bandera `debe_cambiar_password`, revocación de sesiones previas y flujo GUI `/recuperar-clave`.
  - [ ] **Sub-tarea 24.2 (Selector de Unidad Activa `unidad_activa_id`):** Implementar `PUT /api/auth/unidad-activa` validando `ContratoOcupacion` vigente y selector global en `AppShellLayout.vue`/`SidebarNav.vue` refrescando los stores de dominio por inmueble seleccionado.
  - [ ] **Sub-tarea 24.3 (Puestos de Estacionamiento y Maleteros — Migración `0011`):** Crear migración `0011_funcionalidad_proptech_complementaria.py`, modelar y exponer endpoints CRUD para puestos de estacionamiento y maleteros vinculados a `Unidad` e integrarlos en `AdminStructureView.vue`, recibos y solvencias (con suites unitarias, PG17 y BDD).

## ⏳ Hito 25: Motor PDF + Envío SMTP y Código QR Gráfico con Escáner de Cámara
- **Especificación:** [`docs/specs/13_REMEDIACION_INTEGRAL_COMPLETITUD_FUNCIONAL_Y_DOCKERHUB_11X.md`](./docs/specs/13_REMEDIACION_INTEGRAL_COMPLETITUD_FUNCIONAL_Y_DOCKERHUB_11X.md) (Sección 3.2)
- **Sub-tareas de Implementación:**
  - [ ] **Sub-tarea 25.1 (Motor PDF Determinista y Distribución SMTP):** Implementar generación PDF no-root compatible con `read_only: true` para recibos (`PRELIMINAR` y `OFICIAL`) y certificados de solvencia, endpoints `GET /api/finanzas/recibos/{id}/pdf` y `GET /api/finanzas/solvencia/{id}/pdf`, envío automático vía `worker.py` y botones de descarga/reenvío en GUI.
  - [ ] **Sub-tarea 25.2 (Código QR Gráfico SVG/Canvas y Escáner de Cámara en Garita):** Renderizar matrices QR locales sin dependencias externas en `VisitorPassesView.vue` y `SolvencyCertificateView.vue`, habilitar escaneo por cámara en `GatehouseScannerView.vue` (`Permissions-Policy: camera=(self)` acotado con fallback manual accesible) y certificar con pruebas E2E, WCAG y Karate BDD.

## ⏳ Hito 26: Notificaciones en Vivo por WebSocket (`/ws/`) y Cierre `v1.2.0`
- **Especificación:** [`docs/specs/13_REMEDIACION_INTEGRAL_COMPLETITUD_FUNCIONAL_Y_DOCKERHUB_11X.md`](./docs/specs/13_REMEDIACION_INTEGRAL_COMPLETITUD_FUNCIONAL_Y_DOCKERHUB_11X.md) (Sección 3.3)
- **Sub-tareas de Implementación:**
  - [ ] **Sub-tarea 26.1 (Servidor `WS /ws/notificaciones` + Pub/Sub KeyDB):** Implementar handshake autenticado en FastAPI con `verify_websocket_origin`, validación de revocación, heartbeat `ping/pong` y publicación de eventos en tiempo real desde routers y `worker.py` vía KeyDB Pub/Sub.
  - [ ] **Sub-tarea 26.2 (Proxy Nginx/Vite, Composable `useRealtimeNotifications` y Lanzamiento `v1.2.0`):** Habilitar proxy `/ws/` en `nginx.conf`/`vite.config.ts`, integrar reconexión exponencial junto a `useDualRefresh` en SPA, certificar los 13 niveles QA 11X (incluyendo caos Pumba WS y `Trivy = 0`), sincronizar manuales y publicar tag multi-arch `v1.2.0` en Docker Hub (`sinfallas/condominio-backend` y `sinfallas/condominio-frontend`).
