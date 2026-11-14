# 🧪 Bitácora de Pruebas y Validación (TESTING.md) — Frontend Vue 3

**Proyecto:** Condominio App (`frontend/`)  
**Estándar:** Gobernanza y Calidad Nivel 11X (`Rule Zero` — 100% Docker Efímero)

---

## 1. Cobertura en Pruebas Unitarias Aisladas (Vitest >= 95%)

Cada componente `.vue`, store de Pinia, guardia de enrutamiento y utilidad de seguridad cuenta con su suite unitaria dedicada (`*.unit.ts`), cumpliendo la **Invariante de Cero Componentes UI Huérfanos** (`make qa-orphans`):

- `src/utils/security.unit.ts`:
  - Sanitización Anti-XSS (`escapeHtml`, `sanitizeUntrustedText`).
  - Prevención de Prototype Pollution (`sanitizeObject`).
  - Prevención de Open Redirect (`isSafeRedirectUrl`).
  - Validación de cuota de carga $\le 2\text{ MB}$ y tipos MIME permitidos (`validateProofFileUpload`).
  - Generación de `Idempotency-Key` (`generateIdempotencyKey`).
- `src/composables/useIdempotency.unit.ts`:
  - Reutilización de la misma `Idempotency-Key` tras fallos de red/timeout, rotación al completarse con éxito y bloqueo de envíos concurrentes (`isSubmitting`).
- `src/services/apiClient.unit.ts`:
  - Envío automático de `credentials: 'include'`, `X-CSRF-Token` sincronizado por cookie/cabecera/JSON en métodos mutantes, `Idempotency-Key`, reintento controlado (`single-flight` `401` con `POST /api/auth/refresh` y limpieza uniforme ante sesión expirada) y transformación de errores HTTP (`401`, `422`, `500`) y de red en `ApiError`.
- `src/stores/authStore.unit.ts`:
  - Autenticación, hidratación inicial de sesión (`GET /api/auth/me` incluyendo `cedula`, `telefono`, `unidad_activa_id`), rotación/cierre (`POST /api/auth/refresh`, `POST /api/auth/logout`), registro de Usuarios Fantasma, getters (`isAuthenticated`, `isGhostUser`, `isActiveUser`, `userRole`) y **Manejo de Errores No Destructivo** (`isStale = true` preservando `data` ante caídas de red, unificado mediante `StaleDataBanner` en los 5 stores).
- `src/router/index.unit.ts`:
  - Guardias de navegación con hidratación inicial de sesión antes de redirigir, rutas públicas (`/login`, `/register`), ruta de contención fantasma (`/espera-aprobacion`), apertura nativa `<dialog>` con `showModal()` sin `:open`, `autofocus`, `closedby="any"` y cierre backdrop drag-safe (`pointerdown`/`pointerup`) en los 4 modales (`VoteReceiptModal`, `RejectPaymentModal`, `ReceiptBreakdownModal`, `ContextualHelpModal`), migración total de contraste `#0284c7` → `#0369a1` (`5.93:1`), `@media (forced-colors: active)` en `App.vue`, filtrado RBAC + rutas de tesorería en `SidebarNav.vue`, periodo dinámico + `ownUnitId` en `DashboardView.vue` y rutas protegidas por rol (`meta.roles`).
- `src/components/layout/*.unit.ts`:
  - `AppShellLayout.unit.ts` (contenedor fluido `container-type: inline-size` y `max-inline-size: 76rem`), `BottomNavBar.unit.ts` (adaptación `@media (pointer: coarse)`), `SidebarNav.unit.ts`, `AppFooter.unit.ts` y `StaleDataBanner.unit.ts`.
- `src/stores/financeStore.unit.ts` y `src/components/finance/*.unit.ts` (Hitos 6 y 10):
  - `financeStore.unit.ts` (conversión USD/VES, cobertura de abono parcial vs pago total, catch no destructivo en resumen, pagos en revisión, fondos patrimoniales, facturación trimodal LPH, desglose de recibos, emisión/verificación de certificados de solvencia y Candado Contable).
  - `ClosingBanner.unit.ts`, `AnnouncementsCarousel.unit.ts`, `CollectionTrafficLight.unit.ts`, `ExpensesDonutChart.unit.ts`, `RejectPaymentModal.unit.ts` y `ReceiptBreakdownModal.unit.ts`.
- `src/views/auth/*.unit.ts` y `src/views/finance/*.unit.ts` (Hitos 5, 6 y 10):
  - `LoginView.unit.ts`, `RegisterView.unit.ts`, `PendingApprovalView.unit.ts`, `DashboardView.unit.ts`, `PaymentWizardView.unit.ts`, `TreasuryPaymentsView.unit.ts`, `TreasuryClosingView.unit.ts`, `BillingGeneratorView.unit.ts` y `SolvencyCertificateView.unit.ts`.
- `src/stores/operationsStore.unit.ts`, `src/components/operations/*.unit.ts`, `src/views/operations/*.unit.ts` y `src/views/admin/*.unit.ts` (Hitos 7 y 10):
  - `operationsStore.unit.ts` (estructura, actualización de alícuota y cuota fija por unidad, activación de usuarios fantasma, cargos de junta, embudo de incidencias, checklist diario de conserjería, galería de voceros con límite de 30 fotos/mes, bitácora de secretaría y catch no destructivo).
  - `IncidentCard.unit.ts`, `TaskChecklistItem.unit.ts`, `IncidentsFeedView.unit.ts`, `OperationsTasksView.unit.ts`, `SpokespersonGalleryView.unit.ts`, `SecretaryLogbookView.unit.ts`, `AdminStructureView.unit.ts`, `AdminGhostUsersView.unit.ts` y `AdminBoardRolesView.unit.ts`.
- `src/stores/governanceStore.unit.ts`, `src/components/governance/*.unit.ts` y `src/views/governance/*.unit.ts` (Hito 11):
  - `governanceStore.unit.ts` (listado, detalle, creación idempotente de Cartas Consulta y Asambleas, emisión de voto ponderado con recibo `HMAC-SHA256`, cierre de consulta con `acta_generada_id` y catch no destructivo).
  - `VoteReceiptModal.unit.ts` (modal `<dialog closedby="any">` con recibo criptográfico verificable y cierre por backdrop), `ConsultationsListView.unit.ts` (`/consultas`) y `ConsultationDetailView.unit.ts` (`/consultas/:id` con `<progress id="quorum-progress-bar">` y escrutinio en tiempo real).
- `src/stores/accessAmenitiesStore.unit.ts` y `src/views/operations/{VisitorPassesView,GatehouseScannerView,ParcelsTrackerView,AmenitiesReservationView}.unit.ts` (Hitos 12, 13 y 17.4):
  - `accessAmenitiesStore.unit.ts` (emisión, listado, revocación y verificación en garita de Pases de Visita QR `HMAC-SHA256`, registro y confirmación de entrega de paquetería en garita, configuración de áreas sociales, solicitud de reserva con solvencia, cancelación idempotente `cancelarReserva`, inspección post-evento y catch no destructivo `isStale = true`).
  - `VisitorPassesView.unit.ts` (`/accesos/pases`), `GatehouseScannerView.unit.ts` (`/operaciones/garita-qr`), `ParcelsTrackerView.unit.ts` (`/operaciones/paqueteria`) y `AmenitiesReservationView.unit.ts` (`/reservas/areas`, incluyendo `#btn-cancelar-reserva-*`).
- `src/utils/screenHelpCatalog.unit.ts` y `src/components/layout/ContextualHelpModal.unit.ts` (Hito 14):
  - `screenHelpCatalog.unit.ts` (cobertura total de rutas públicas, financieras, operativas, gobernanza, administrativas, alias y variantes adaptadas por rol).
  - `ContextualHelpModal.unit.ts` (modal accesible `<dialog id="dialog-contextual-help" closedby="any">`, `autofocus`, región desplazable `tabindex="0"` + `:aria-label`, cierre drag-safe `pointerdown`/`pointerup`, renderizado reactivo según ruta/rol e interacción).
- `src/App.unit.ts`: Montaje del contenedor raíz y reglas globales `@media (forced-colors: active)`.
- **Total Certificado (Hitos 5 al 17.4 + Modern Web Guidance):** **38 componentes `.vue` auditados (0 huérfanos)**, **48 suites `.unit.ts` (`117/117` tests aprobados)** con **99.52% líneas, 99.25% sentencias, 97.92% funciones y 95.45% ramas**, cancelación idempotente de reservas (`cancelarReserva`), envío de `Idempotency-Key` en `aprobarPago` y `registrarEgreso` (`financeStore.ts`), `0` ocurrencias restantes de `#0284c7` tras completar la migración `#0369a1` (`5.93:1` WCAG 1.4.3 / 1.4.11) en toda `frontend/src/`, build productivo Vite (`vue-tsc`, `prettier` y `eslint --max-warnings 0` limpios) y Escenario 10 incorporado en `frontend/test/ui_business_flow.feature` (la ejecución previa con Chrome headless E2E Playwright aprobó **8/8 pruebas** en Hito 17.2/Modern Web Guidance sin re-ejecución de Playwright/Axe en Hito 17.4). *Nota de infraestructura QA:* `sinfallas/karatelabs:latest` carece de `/usr/bin/google-chrome` (impidiendo ejecutar `test/ui_business_flow.feature` en ese contenedor).

---

## 2. Ejecución Efímera en Docker (`Rule Zero`)

```bash
# Desde frontend/ (o vía docker compose -f frontend/docker-compose.qa.yml)
make qa-orphans    # Verifica 0 componentes .vue sin prueba unitaria
make qa-lint       # pnpm audit + vue-tsc --noEmit + prettier + eslint (SonarJS CC <= 15)
make qa-unit       # Vitest + cobertura V8 (>= 95% en lines, functions, branches, statements)
make qa-e2e        # Playwright + @axe-core/playwright (WCAG 2.1 AA)
make qa-bdd        # Karate Labs UI en Chrome Headless
```
