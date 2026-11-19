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
  - `AppShellLayout.unit.ts` (contenedor fluido `container-type: inline-size` y `max-inline-size: 76rem`, ruta padre unificada, `#btn-mobile-logout` en `< 768px`, `#btn-theme-toggle`), `MobileNavDrawer.unit.ts` (cajón móvil `<dialog>` Top Layer en `< 768px` con cierre y logout), `BottomNavBar.unit.ts` (adaptación `@media (pointer: coarse)`, iconos SVG y píldora activa `.bottom-nav__pill`), `SidebarNav.unit.ts` (3 secciones semánticas + iconos SVG + `#btn-sidebar-theme-toggle`), `ThemeToggleButton.unit.ts`, `AppFooter.unit.ts` y `StaleDataBanner.unit.ts`.
- `src/components/common/*.unit.ts` y `src/composables/*.unit.ts` (Hito 15 + Hito 22):
  - `CopyButton.unit.ts` (`command="--copy"` + `commandfor`, fallback `@click`, `navigator.clipboard.writeText()` + fallback `execCommand`, región viva externa `[role="status"]` con deduplicación `\u00A0` y limpieza a `2000ms`), `EmptyStateCard.unit.ts` (ilustración SVG decorativa y CTA opcional) y `SkeletonCard.unit.ts` (`aria-busy="true"`, shimmer `CLS = 0`).
  - `useThemeMode.unit.ts` (sistema `OKLCH` + `light-dark()`), `useDualRefresh.unit.ts` (`setInterval` + `clearInterval` + `[ 🔄 Refrescar ]`), `useTopLayerDialog.unit.ts` (gestión unificada `<dialog>` `.showModal()` + backdrop drag-safe) y `useViewTransition.unit.ts` (`runWithViewTransition`, detección de bug Firefox 1882408 en `canTransitionDisplay()`, `closeTopLayerDialog` con `data-closing` y respeto a `prefers-reduced-motion`).
- `src/stores/financeStore.unit.ts` y `src/components/finance/*.unit.ts` (Hitos 6 y 10):
  - `financeStore.unit.ts` (conversión USD/VES, cobertura de abono parcial vs pago total, catch no destructivo en resumen, pagos en revisión, fondos patrimoniales, facturación trimodal LPH, desglose de recibos, emisión/verificación de certificados de solvencia y Candado Contable).
  - `ClosingBanner.unit.ts`, `AnnouncementsCarousel.unit.ts`, `CollectionTrafficLight.unit.ts`, `ExpensesDonutChart.unit.ts`, `RejectPaymentModal.unit.ts` y `ReceiptBreakdownModal.unit.ts`.
- `src/views/auth/*.unit.ts` y `src/views/finance/*.unit.ts` (Hitos 5, 6, 10 y 22):
  - `LoginView.unit.ts`, `RegisterView.unit.ts`, `PendingApprovalView.unit.ts`, `NotFoundView.unit.ts` (ruta `404` `#not-found-card`), `DashboardView.unit.ts`, `PaymentWizardView.unit.ts`, `TreasuryPaymentsView.unit.ts`, `TreasuryClosingView.unit.ts`, `BillingGeneratorView.unit.ts` y `SolvencyCertificateView.unit.ts`.
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
- `src/App.unit.ts`, `src/main.unit.ts` y `src/{stores/storeErrors,utils/decimal,utils/navigationCatalog,utils/navIcons}.unit.ts`: Montaje del contenedor raíz e inicialización de aplicación, reglas globales `@media (forced-colors: active)`, extracción uniforme de errores, aritmética decimal `ROUND_HALF_UP`, catálogo agrupado de navegación e iconos SVG (`100%` cobertura en `App.vue`, `main.ts` y `navIcons.ts`).
- **Total Certificado (Hito 23 `Rule Zero`):** **44 componentes `.vue` auditados (`0` huérfanos)**, **63 suites `.unit.ts` (`226/226` tests aprobados)** con cobertura V8 medida en contenedor `qa-vue3` (**`99.03%` statements, `96.16%` branches, `98.72%` functions, `99.12%` lines**), **mutación Stryker `97.49%` MSI** (`2437` muertos, `9` timeouts, `62` sobrevivientes, `8` errores sobre `16` archivos fuente en `qa-vue3` + `ui-e2e` con `ignoreStatic: true`), `pnpm install --frozen-lockfile` (`720` entradas), `0` CVEs HIGH/CRITICAL en dependencias (`pnpm audit --audit-level=high`), `vue-tsc --noEmit` + `tsc -p tsconfig.e2e.json --noEmit`, `prettier --check` (`src/`, `e2e/`, `tokens.css`) y `eslint` (`src/` y `e2e/` con `--max-warnings 0`), build productivo Vite (`178` módulos), **`88/88` pruebas Playwright E2E aprobadas (`1.2m`)** en **4 viewports (`375x667`, `390x844`, `768x1024`, `1440x900`)** (`@axe-core/playwright` en **`23/23` vistas** claro/oscuro con reglas WCAG 2.1 AA + `best-practice` y `0` violaciones, Screenplay sin selectores crudos y **`24` snapshots PNG Linux**), **Karate UI BDD `18/18` pass** vía sidecar `chrome-cdp` (incluyendo flujos autenticados Hito 23 para `PROPIETARIO`, `TESORERO`, `CONSERJE` y `PRESIDENTE`) y **Lighthouse CI** (`3/3` corridas en `/login` y `/register`: **`99%` Performance, `100%` Accessibility, `96%` Best Practices, `CLS = 0`**).

---

## 2. Ejecución Efímera en Docker (`Rule Zero`)

```bash
# Desde frontend/ (o vía docker compose -f frontend/docker-compose.qa.yml)
make qa-orphans    # Verifica 0 componentes .vue sin prueba unitaria (44/44)
make qa-lint       # pnpm audit + vue-tsc + tsc -p tsconfig.e2e.json + prettier + eslint src & e2e (SonarJS CC <= 15)
make qa-unit       # Vitest + cobertura V8 (>= 95% -> 99.03% Stmts) + build Vite
make qa-mutation   # Pruebas de mutación Frontend (Stryker vía qa-vue3 + ui-e2e -> MSI 97.49%)
make qa-e2e        # Playwright Screenplay + @axe-core/playwright (WCAG 2.1 AA + best-practice) + 24 PNGs en 4 viewports
make qa-perf       # Lighthouse CI multi-corrida (Performance >= 90%, A11y >= 95%, BP >= 95%, CLS = 0)
make qa-bdd        # Karate Labs UI en Chrome Headless vía sidecar chrome-cdp (18/18 escenarios)
```

---

## 3. Suites E2E Screenplay, Accesibilidad, Regresión Visual y Karate UI (Hitos 8, 22 y 23)

- **Patrón Screenplay + Mock Stateful (`e2e/screenplay/{core,tasks,questions}.ts`, `e2e/fixtures/condominioApiMock.ts`):** Mock 1:1 con esquemas OpenAPI y RBAC reales (incluyendo rechazo `403` y ausencia matutina `404` de tasa BCV) cubriendo en `e2e/authenticated-flows.e2e.ts` el ciclo completo de contención Usuario Fantasma + activación presidencial, flujo financiero trimodal (reporte idempotente de pago, aprobación, facturación LPH + desglose, emisión/verificación y copia de solvencia `HMAC-SHA256`, Candado Contable y redirección RBAC), embudo operativo + votación ponderada y copia `HMAC-SHA256` (Art. 23 LPH), control de accesos QR Anti-Replay + reserva/cancelación estricta por morosidad, cajón móvil `< 768px`, cierre de sesión móvil, ruta `404` y contención `403` / `404` en **`mobile-375x667`, `mobile-390x844`, `tablet-768x1024` y `desktop-chromium` (`1440x900`)**.
- **Geometría Visual Anti-JSDOM (`ViewportGeometryAudit`):** Valida `scrollWidth <= innerWidth`, targets táctiles $\ge 44\times 44\text{ px}$ y no oclusión por `BottomNavBar` sobre el CTA primario, `#fab-reportar-pago` e `#app-inflow-footer` usando `getBoundingClientRect()` y `document.elementsFromPoint()`.
- **Accesibilidad WCAG 2.1 AA + Best-Practice y Regresión Visual (`e2e/accessibility.e2e.ts`, `e2e/visual-regression.e2e.ts`):** `0` violaciones `critical`/`serious` en **`23/23` vistas** y diálogos `<dialog>` Top Layer tanto en modo claro como oscuro (`light-dark()`), más **`24` snapshots PNG Linux** (incluyendo `consultation-detail-dark` y `tablet-768x1024`) en `frontend/e2e/visual-regression.e2e.ts-snapshots/` (`maxDiffPixelRatio: 0.02`).
- **Karate UI BDD (`frontend/test/ui_business_flow.feature`) y Lighthouse CI (`frontend/lighthouserc.cjs`):** **`18/18` escenarios** aprobados sobre `chrome-cdp` headless (`127.0.0.1:9222`) incluyendo geometría DOM, ruta `404` `#not-found-card`, theming nativo y flujos autenticados end-to-end para `PROPIETARIO`, `TESORERO`, `CONSERJE` y `PRESIDENTE`; Lighthouse CI certificado sobre `ui-prod` (`3/3` corridas en `/login` y `/register`: **`99%` Performance, `100%` Accessibility, `96%` Best Practices y `CLS = 0`**, manteniendo `skipAudits: ['is-on-https', 'redirects-http']` para la red interna Docker HTTP).
