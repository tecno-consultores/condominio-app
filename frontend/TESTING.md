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
  - `AppShellLayout.unit.ts`, `BottomNavBar.unit.ts`, `SidebarNav.unit.ts`, `AppFooter.unit.ts` y `StaleDataBanner.unit.ts`.
- `src/stores/financeStore.unit.ts` y `src/components/finance/*.unit.ts` (Hito 6):
  - `financeStore.unit.ts` (conversión USD/VES, cobertura de abono parcial vs pago total, catch no destructivo en resumen y pagos en revisión, y Candado Contable).
  - `ClosingBanner.unit.ts`, `AnnouncementsCarousel.unit.ts`, `CollectionTrafficLight.unit.ts`, `ExpensesDonutChart.unit.ts` y `RejectPaymentModal.unit.ts`.
- `src/views/auth/*.unit.ts` y `src/views/finance/*.unit.ts` (Hitos 5 y 6):
  - `LoginView.unit.ts`, `RegisterView.unit.ts`, `PendingApprovalView.unit.ts`, `DashboardView.unit.ts`, `PaymentWizardView.unit.ts`, `TreasuryPaymentsView.unit.ts` y `TreasuryClosingView.unit.ts`.
- `src/App.unit.ts`: Montaje del contenedor raíz.

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
