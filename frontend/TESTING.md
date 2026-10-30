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
  - Envío automático de `credentials: 'include'`, `X-CSRF-Token` en métodos mutantes, `Idempotency-Key` y transformación de errores HTTP (`401`, `422`, `500`) y de red en `ApiError`.
- `src/stores/authStore.unit.ts`:
  - Autenticación, registro de Usuarios Fantasma, getters (`isAuthenticated`, `isGhostUser`, `isActiveUser`, `userRole`) y **Manejo de Errores No Destructivo** (`isStale = true` preservando `data` ante caídas de red).
- `src/router/index.unit.ts`:
  - Guardias de navegación para rutas públicas (`/login`, `/register`), ruta de contención fantasma (`/espera-aprobacion`) y rutas protegidas por rol (`meta.roles`).
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
- `src/App.unit.ts`: Montaje del contenedor raíz.
- **Total Certificado (Hitos 5, 6, 7 y 10):** **30 componentes `.vue` auditados (0 huérfanos)**, **37 suites `.unit.ts` (75/75 tests aprobados)** con **99.84% líneas/sentencias, 98.26% funciones y 95.37% ramas**.

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
