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
| **Hito 17** | Endurecimiento `--no-dev`, Seguridad Real, Concurrencia LPH y Sesión/Modales (Fase 5) | `11_ENDURECIMIENTO_BACKEND...` | 🚧 En Progreso | `60%` |
| **Hito 18** | Infraestructura Productiva Docker No-Root, Worker Real y Respaldos (Fase 5) | `12_GOBERNANZA_DESPLIEGUE...` | ⏳ Pendiente | `0%` |
| **Hito 15** | Rediseño UX/UI "Hospitalidad Residencial", Tokens `OKLCH` y Transiciones (Fase 4) | `10_DISENO_UX_UI_AMIGABLE...` | ⏳ Pendiente | `0%` |
| **Hito 8** | Certificación Integral E2E, Geometría Anti-JSDOM, WCAG 2.1 AA y Lighthouse CI (Fase 6) | `05_ARQUITECTURA_GUI...` | ⏳ Pendiente | `0%` |

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

> **🏛️ FASE 4: Evolución Funcional PropTech, LPH, Ayuda Contextual y UX/UI Amigable (Hitos 10 al 15) — `[EN EJECUCIÓN]`**

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

> **🔧 FASE 5: Saneamiento de Gobernanza, Endurecimiento Real y Despliegue Productivo (Hitos 16, 17 y 18 — Specs 11 y 12) — `[EN EJECUCIÓN]`**

## ✅ Hito 16: Gobernanza Thin-Repo v2.20.3, Higiene AST `--code-only`, Bloqueadores 11X y Saneamiento CI/Scripts
- **Especificación:** [`docs/specs/12_GOBERNANZA_DESPLIEGUE_PRODUCTIVO_Y_CI_11X.md`](./docs/specs/12_GOBERNANZA_DESPLIEGUE_PRODUCTIVO_Y_CI_11X.md) (Sección 1)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 16.0 (Reconciliación Thin-Repo `@sinfallas/mcp-qa-11x` v2.20.3):** Ejecutado `npx -y @sinfallas/mcp-qa-11x@latest install-skill --init-agents --include-scripts --reconcile`, podadas reglas duplicadas hacia `.agents/rules/domain_condominio_app_rules.md` y saneados enlaces en `AGENTS.md`, `.agents/README.md`, `.trivy.yaml` y `commitlint.config.js`.
  - [x] **Sub-tarea 16.1 (Remediación de 20 Bloqueadores `HIGH` — `QA-KARATE-IDEMP` y `SEC-09`):** Añadido `ignore-scripts=true` en `.npmrc` raíz y `frontend/.npmrc`, corregidos permisos de `frontend/pnpm-workspace.yaml` y reemplazados los 18 UUIDs literales en `backend/test/api_test.feature` por `java.util.UUID.randomUUID() + ''` con datos únicos por escenario.
  - [x] **Sub-tarea 16.2 (Higiene AST `--code-only`, `.gitignore` y Purga Host `Rule Zero`):** Desindexado `graphify-out/` de Git, eliminados daemons `:8080` de `docker-compose.qa.yml`, regenerado el grafo AST con `./scripts/actualizar-grafos-graphify.sh --all` (`--code-only`) y purgados artefactos locales del host mediante `clean_workspace_11x`.
  - [x] **Sub-tarea 16.3 (Saneamiento de Scripts, `Makefile`s, `lighthouserc.cjs`, `lefthook.yml` y Workflows CI):** Corregido `scripts/limpieza.sh` (sin `sudo`, sin `docker system prune --volumes` y preservando `zap.yaml`), migrado `lighthouserc.js` a `lighthouserc.cjs`, creado `Makefile` raíz, corregidos `backend/Makefile` / `frontend/Makefile` bajo `Rule Zero` (`mypy --strict`, `pnpm run build`, UID/GID no-root, sin `python3` en host), y endurecidos `auditar-infra.sh`, `lefthook.yml` y `.github/workflows/00..02`.
  - [x] **Sub-tarea 16.4 (Sincronización Documental Integral):** Creadas `Spec 11` y `Spec 12`, sincronizados `README.md`, `SECURITY.md`, `docs/qa/README.md`, `docs/ARCHITECTURE.md`, `docs/API_ROUTES.md`, `docs/MANUAL_ADMINISTRADOR_E_INSTALADOR.md`, `docs/specs/README.md`, `CHANGELOG.md`, `TESTING.md` y `backend/TESTING.md`, y certificado el gate `certify_11x_gate` (`10/10`).

## 🚧 Hito 17: Endurecimiento Backend (`--no-dev`), Seguridad Real, Concurrencia LPH y Sesión/Modales Frontend
- **Especificación:** [`docs/specs/11_ENDURECIMIENTO_BACKEND_CONCURRENCIA_Y_SEGURIDAD_REAL.md`](./docs/specs/11_ENDURECIMIENTO_BACKEND_CONCURRENCIA_Y_SEGURIDAD_REAL.md)
- **Sub-tareas de Implementación:**
  - [x] **Sub-tarea 17.1 (Empaquetado Productivo `--no-dev`, Fail-Fast Prod y KDF Estricto):** Movidos `prometheus-fastapi-instrumentator` y `prometheus-client` a `[project].dependencies` en `backend/pyproject.toml` (retirado `passlib[bcrypt]`, regenerado `uv.lock`), implementada `validate_production_security_settings()` en `backend/src/security.py` y `lifespan`, retirado el fallback `SHA-256` sin sal en `verify_password` y certificadas las pruebas unitarias y arranque `--no-dev` en Docker.
  - [x] **Sub-tarea 17.2 (Ciclo de Sesión Completo, CSRF Real, Rate-Limiting y KeyDB Fail-Closed):** Implementar `POST /api/auth/logout`, `POST /api/auth/refresh`, validación real de `X-CSRF-Token` y sincronización en `apiClient.ts`, lockout `5/15m` + anti-timing en `/login`, `cedula`/`telefono`/`unidad_activa_id` en `/api/auth/me`, fail-closed en KeyDB en producción, TTL `86400s` en idempotencia, hidratación inicial de sesión en Vue Router, expiración `401` uniforme + `StaleDataBanner` en los 5 stores, apertura real con `showModal()` sin `open` estático en los 4 `<dialog>`, rutas de tesorería + filtrado RBAC en `SidebarNav.vue` y periodo dinámico + `ownUnitId` en `DashboardView.vue`.
  - [x] **Sub-tarea 17.3 (Concurrencia Financiera, Candado Contable, Anti-IDOR y Exactitud LPH):** Exigir `Idempotency-Key` + `with_for_update()` en `PUT /api/pagos/{id}/aprobar`, validar titularidad activa `ContratoOcupacion` (anti-IDOR) en `POST /api/pagos/reportar`, bloquear `POST /api/finanzas/egresos` cuando `ReporteMensual.estado == "CERRADO"`, añadir `UniqueConstraint(unidad_id, periodo)` (`uq_recibo_unidad_periodo`) e índice único parcial `uq_pagos_metodo_ref_activo` (migración `0007_hito17_unicidad_finanzas`), extraer `src/facturacion_lph.py`, prorratear cuotas extraordinarias según modalidad `ALICUOTA`, validar `validar_suma_alicuotas` antes de cargos variables, usar `Decimal(2)/Decimal(3)` exacto en `DOS_TERCIOS` y enviar `Idempotency-Key` en `financeStore.ts` (`236/236` unitarios `99.11%`, `22/22` Karate Labs).
  - [ ] **Sub-tarea 17.4 (Integridad en Gobernanza, Reservas, Administración y SQL):** Validar `fecha_cierre` y bloqueo al cerrar consultas, reemplazar constraint de `ReservaAreaSocial` por índice único parcial + `PUT /api/reservas/{id}/cancelar` + cargo contable en `FINALIZADA_CON_DANOS`, crear DTO público restringido `GET /api/estructura/unidades`, preservar histórico de contratos y restringir Junta Directiva a propietarios, reemplazar `SELECT *` en RAM / N+1 y añadir políticas RLS en PostgreSQL 17 (`QA-PG17-RLS`).
  - [ ] **Sub-tarea 17.5 (Certificación QA 11X del Hito 17):** Suites unitarias/integración PostgreSQL 17 (`>= 95%`), escenarios BDD con usuarios activos reales en `backend/test/api_test.feature`, paridad Alembic↔ORM y refresco del Grafo AST.

## ⏳ Hito 18: Infraestructura Productiva Docker Multi-Stage No-Root, Worker Real y Respaldos Automatizados
- **Especificación:** [`docs/specs/12_GOBERNANZA_DESPLIEGUE_PRODUCTIVO_Y_CI_11X.md`](./docs/specs/12_GOBERNANZA_DESPLIEGUE_PRODUCTIVO_Y_CI_11X.md) (Sección 2)
- **Sub-tareas de Implementación:**
  - [ ] **Sub-tarea 18.1 (Dockerfiles Multi-Stage No-Root y `nginx.conf` OSHP):** Crear `backend/Dockerfile` (`uv sync --frozen --no-dev`, usuario `10001`), `frontend/Dockerfile` (`nginx-unprivileged`, proxy `/api` + `/health` + cabeceras OSHP) y `docker-compose.yml` productivo (`postgres:17-alpine`, `keydb` autenticado, `minio`, `api`, `worker`, `frontend`).
  - [ ] **Sub-tarea 18.2 (Worker Asíncrono Ejecutable AVIF/MinIO/SMTP y `QA-HEALTH-01`):** Implementar entrypoint `python -m src.worker` con conversión AVIF real y subida a MinIO, consumidor BLPOP SMTP en KeyDB, scheduler idempotente (`UniqueConstraint` en `TareaDiaria`) y heartbeat verificable sin mocks (`QA-HEALTH-01`).
  - [ ] **Sub-tarea 18.3 (Plantilla `.env.example`, Respaldos y Certificación Trivy Prod):** Crear `.env.example` de Condominio App y `scripts/backup-diario.sh` (PostgreSQL 17 + MinIO), certificar `Trivy HIGH/CRITICAL = 0` sobre imágenes y `docker-compose.yml`, y actualizar `docs/MANUAL_ADMINISTRADOR_E_INSTALADOR.md`.

---

> **✨ CONTINUACIÓN FASE 4: UX/UI Amigable — `[PENDIENTE]`**

## ⏳ Hito 15: Rediseño UX/UI Amigable ("Hospitalidad Residencial"), Sistema de Tokens `OKLCH`, Modo Oscuro (`light-dark()`) y Micro-Transiciones Modernas
- **Especificación:** [`docs/specs/10_DISENO_UX_UI_AMIGABLE_TRANSICIONES_Y_SISTEMA_TOKENS.md`](./docs/specs/10_DISENO_UX_UI_AMIGABLE_TRANSICIONES_Y_SISTEMA_TOKENS.md) y [`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md) (Sección 7)
- **Sub-tareas de Implementación:**
  - [ ] **Sub-tarea 15.1 (Sistema Centralizado de Tokens `OKLCH`, Modo Claro/Oscuro `light-dark()` y Sombras de 2 Capas):** Crear `frontend/src/assets/tokens.css`, importarlo en `main.ts`, implementar `useThemeMode.ts` (`useThemeMode.unit.ts`) y añadir `#btn-theme-toggle`.
  - [ ] **Sub-tarea 15.2 (Navegación Amigable con Iconos SVG, Agrupación Semántica y Píldora Activa):** Rediseñar `SidebarNav.vue` (3 bloques semánticos con iconos SVG `stroke-width: 1.75`) y `BottomNavBar.vue` (iconos SVG + píldora activa).
  - [ ] **Sub-tarea 15.3 (Dashboard Contextual "Tu Hogar Hoy", Estados Vacíos Ilustrados y Esqueletos de Carga):** Implementar `EmptyStateCard.vue`, `SkeletonCard.vue` (`CLS = 0`), Tarjeta Hero de Solvencia y `#dashboard-quick-actions` en `DashboardView.vue`, y glifos para daltónicos en `CollectionTrafficLight.vue`.
  - [ ] **Sub-tarea 15.4 (Motor de Transiciones SPA, Modales `<dialog>` en Top-Layer con `@starting-style` + Bottom Sheet Móvil y `calc-size()`):** Implementar `useViewTransition.ts` (`runWithViewTransition` y `closeTopLayerDialog` con `data-closing`), aplicar `@starting-style` + `allow-discrete` + `overlay` + Bottom Sheet móvil en todos los `<dialog>`, tarjetas `:has(input:checked)` y respeto estricto a `@media (prefers-reduced-motion: reduce)`.
  - [ ] **Sub-tarea 15.5 (Certificación QA 11X del Hito 15):** Pruebas Vitest (`>= 95%`), `make -C frontend qa-orphans` (0 huérfanos), refresco del Grafo AST y escenarios BDD en `frontend/test/ui_business_flow.feature`.

---

> **🏆 FASE 6: Certificación Integral E2E, Geometría Visual Anti-JSDOM, WCAG 2.1 AA y Lighthouse CI — `[PENDIENTE]`**

## ⏳ Hito 8: Certificación E2E, Geometría Visual Anti-JSDOM, WCAG 2.1 AA y Lighthouse CI (Cobertura Total Fases 1..5)
- **Especificación:** [`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md) (Secciones 3, 7 y 8) y [`docs/specs/10_DISENO_UX_UI_AMIGABLE_TRANSICIONES_Y_SISTEMA_TOKENS.md`](./docs/specs/10_DISENO_UX_UI_AMIGABLE_TRANSICIONES_Y_SISTEMA_TOKENS.md)
- **Sub-tareas de Certificación:**
  - [ ] **Sub-tarea 8.1 (Playwright E2E, Entorno Conectado y Geometría Visual Anti-JSDOM):** Configurar proxy `/api` o fixtures deterministas en `ui-prod`/`ui-e2e`, añadir viewports `375x667` y `390x844` en `playwright.config.ts`, ejecutar `.e2e.ts` cubriendo flujos autenticados de los Hitos 5 al 17 y verificar con `getBoundingClientRect()` que ningún botón primario, FAB o `AppFooter` quede oculto tras `BottomNavBar`.
  - [ ] **Sub-tarea 8.2 (Auditoría WCAG 2.1 AA y Regresión Visual):** Certificar **0 violaciones** `critical` o `serious` con `@axe-core/playwright` en tema claro y tema oscuro (`light-dark()`), y validar snapshots visuales (`maxDiffPixelRatio: 0.02`).
  - [ ] **Sub-tarea 8.3 (Karate UI y Lighthouse CI):** Certificar `make -C frontend qa-bdd` (`ui-bdd` sobre `frontend/test/ui_business_flow.feature`) y `make -C frontend qa-perf` (`lighthouserc.cjs`: Performance $\ge 90\%$, Accessibility $\ge 95\%$, Best Practices $\ge 95\%`).
