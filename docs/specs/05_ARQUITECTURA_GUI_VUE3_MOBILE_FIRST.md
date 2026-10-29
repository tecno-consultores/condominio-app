# 🎨 Especificación 05: Arquitectura GUI Vue 3 Mobile-First y Ergonomía Nivel 11X

**Estado:** Especificación Canónica para el Inicio de la Fase 2 (Hitos 5, 6, 7 y 8)  
**Ecosistema:** Vue 3 (Composition API `<script setup lang="ts">`) + Vite + Pinia + Vue Router + TypeScript Strict

---

## 1. Principios Arquitectónicos para Empezar la GUI de la Forma Correcta

Para evitar los defectos clásicos de proyectos SPA generados por IA (mocks desconectados, colisiones visuales en móvil, pérdida de datos en stores al fallar la red y componentes sin pruebas), la GUI de **Condominio App** se construirá bajo **6 leyes de ingeniería**:

### 1.1. Geometría Visual y Ergonomía In-Flow (Anti-JSDOM)
- **El Problema:** `jsdom` en Vitest siempre devuelve `0x0` en `getBoundingClientRect()`. Si se usa `position: fixed` sin reserva de flujo, la **Bottom Navigation Bar** móvil o un footer fijo oculta el botón `"Enviar Reporte"` o el botón flotante (FAB `"Pagar / Reportar"`).
- **La Solución Obligatoria (`AppShellLayout.vue`):**
  1. **Móvil (`< 768px`):** Muestra `BottomNavBar.vue` de altura fija (`4rem` / `64px`). El contenedor `<main class="app-main">` declara obligatoriamente `display: flex; flex-direction: column; min-height: 100dvh; padding-bottom: calc(4.5rem + env(safe-area-inset-bottom));`.
  2. **Escritorio (`>= 768px`):** Oculta `BottomNavBar.vue` y muestra `SidebarNav.vue` lateral izquierdo (`260px`), liberando el `padding-bottom` del `<main>`.
  3. **Botón Flotante (FAB `"Pagar / Reportar"`):** En móvil se posiciona en `bottom: calc(5rem + env(safe-area-inset-bottom)); right: 1rem;` para nunca colisionar con la barra inferior ni con el último ítem de las listas.
  4. **Footer Legal/Versión:** Siempre **in-flow** dentro de `<main>` con `margin-top: auto`. **Prohibido** usar `position: fixed` en footers.

### 1.2. Manejo de Errores No Destructivo en Pinia (Anti-Destructive Catch)
- **Prohibido** vaciar listas o estados (`recibos.value = []`, `resumen.value = null`) dentro del bloque `catch` de una acción de Pinia cuando ya existen datos válidos en memoria.
- Cada store de Pinia expondrá el contrato estándar:
  ```typescript
  export interface AsyncStoreState<T> {
    data: T | null;
    isLoading: boolean;
    isStale: boolean;
    errorMessage: string | null;
    lastUpdatedAt: number | null;
  }
  ```
- Si una petición falla por micro-corte de red móvil, `data` se conserva intacto, `isStale` pasa a `true` y se muestra un banner discreto (`StaleDataBanner.vue`) indicando que se muestran los últimos datos conocidos.

### 1.3. Seguridad Cliente por Diseño (`frontend/src/utils/security.ts`)
1. **Anti-XSS (`escapeHtml`):** Sanitización obligatoria de cualquier texto dinámico antes de renderizar en tooltips o vistas enriquecidas. Prohibido el uso de `v-html` sin sanitización estricta.
2. **Anti-Prototype Pollution (`sanitizeObject`):** Todo payload JSON externo dinámico se normaliza con `Object.create(null)` descartando claves `__proto__`, `constructor` y `prototype`.
3. **Idempotencia de Mutaciones (`useIdempotency.ts`):**
   - Composable que genera un `Idempotency-Key` (`crypto.randomUUID()`) al iniciar una intención de envío (registro, reporte de pago, nueva incidencia).
   - Mientras la petición está en vuelo (`isSubmitting = true`), el botón se bloquea (`:disabled="isSubmitting"`, `aria-busy="true"`).
   - Si falla por timeout de red, el reintento reutiliza la **misma** `Idempotency-Key` para que KeyDB en el backend garantice ejecución única; solo al completarse con éxito o cambiar los datos del formulario se rota la clave.
4. **Cliente HTTP (`frontend/src/services/apiClient.ts`):**
   - Configurado con `withCredentials: true` para enviar automáticamente la cookie `HttpOnly` `access_token`.
   - Inyecta automáticamente `X-CSRF-Token` en métodos mutantes (`POST`, `PUT`, `DELETE`).

### 1.4. Invariante de Cero Componentes Huérfanos (`make -C frontend qa-orphans`)
- **Regla 1 a 1:** Por cada archivo `NombreComponente.vue` creado en `frontend/src/components/` o `frontend/src/views/`, se debe crear simultáneamente `NombreComponente.unit.ts`.
- Auditado mecánicamente por `python3 .agents/scripts/verify_zero_orphan_vue_components.py`.

### 1.5. Accesibilidad WCAG 2.1 AA y Selectores Deterministas para BDD/E2E
- Todos los controles interactivos deben tener `<label>` explícito o `aria-label`, contraste mínimo `4.5:1` (texto normal) / `3:1` (componentes UI), estados `:focus-visible` claros y tamaño mínimo de toque táctil de `44x44px` en móvil.
- Todos los formularios, botones y alertas críticas incluirán IDs semánticos estables para **Karate Labs UI** (`frontend/test/ui_business_flow.feature`) y **Playwright** (`frontend/e2e/*.e2e.ts`).

---

## 2. Estructura de Directorios del Frontend (`frontend/`)

```text
frontend/
├── docker-compose.qa.yml          # Orquestador efímero (qa-vue3, ui-prod, ui-e2e, karatelabs, observability, graphify)
├── Makefile                       # Metas 11X: qa-lint, qa-orphans, qa-unit, qa-mutation, qa-e2e, qa-perf, qa-bdd, qa-all
├── package.json                   # Scripts y dependencias congeladas con pnpm
├── .npmrc                         # ignore-scripts=true (Zero-Trust)
├── .eslintrc.json                 # ESLint + Vue 3 + TypeScript + SonarJS (CC <= 15) + Security
├── .prettierrc                    # Formateo estético
├── tsconfig.json                  # TypeScript strict=true
├── vite.config.ts                 # Configuración de Vite y proxy /api -> http://api:8000
├── vitest.config.ts               # Umbral innegociable >= 95% en lines, branches, functions, statements
├── playwright.config.ts           # Mobile Safari (iPhone 13) + Desktop Chrome + snapshots sin animaciones
├── stryker.conf.json              # Pruebas de mutación sobre .ts y .vue
├── lighthouserc.js                # Performance >= 0.90, Accessibility >= 0.95
├── TESTING.md                     # Bitácora viva de pruebas del Frontend
├── test/
│   └── ui_business_flow.feature   # Escenarios BDD de Karate Labs UI en Chrome Headless
├── e2e/
│   └── accessibility.e2e.ts       # Auditoría WCAG 2.1 AA con @axe-core/playwright y snapshots visuales
└── src/
    ├── main.ts
    ├── App.vue
    ├── App.unit.ts
    ├── utils/
    │   ├── security.ts            # escapeHtml, sanitizeObject
    │   └── security.unit.ts
    ├── composables/
    │   ├── useIdempotency.ts      # Generación y bloqueo de Idempotency-Key
    │   └── useIdempotency.unit.ts
    ├── services/
    │   ├── apiClient.ts           # Cliente HTTP con cookies HttpOnly, CSRF e interceptores
    │   └── apiClient.unit.ts
    ├── router/
    │   ├── index.ts               # Guardias de navegación (Auth, Usuario Fantasma -> /espera-aprobacion, RBAC)
    │   └── index.unit.ts
    ├── stores/
    │   ├── authStore.ts           # Estado de sesión, usuario actual y getters de rol
    │   ├── authStore.unit.ts
    │   ├── financeStore.ts        # Tasa del día, resumen, recibos, pagos y cierre (no destructivo)
    │   ├── financeStore.unit.ts
    │   ├── operationsStore.ts     # Incidencias ("Me Sumo"), tareas del conserje, voceros y bitácora
    │   └── operationsStore.unit.ts
    ├── components/
    │   ├── layout/
    │   │   ├── AppShellLayout.vue # Sidebar Desktop + BottomNavBar Mobile + Main In-Flow
    │   │   ├── BottomNavBar.vue
    │   │   ├── SidebarNav.vue
    │   │   └── StaleDataBanner.vue
    │   ├── finance/
    │   │   ├── ClosingBanner.vue          # Banner condicional días 1 al 10
    │   │   ├── AnnouncementsCarousel.vue  # Carrusel de comunicados
    │   │   ├── CollectionTrafficLight.vue # Semáforo de cobranza (unidad propia primero)
    │   │   ├── ExpensesDonutChart.vue     # Gráfico SVG nativo accesible (0 dependencias pesadas)
    │   │   └── RejectPaymentModal.vue     # Modal con motivo obligatorio de rechazo
    │   └── operations/
    │       ├── IncidentCard.vue           # Tarjeta con contador "🔥 X vecinos" y botón "Me Sumo"
    │       └── TaskChecklistItem.vue      # Ítem táctil para el conserje
    └── views/
        ├── auth/
        │   ├── LoginView.vue              # /login
        │   ├── RegisterView.vue           # /register
        │   └── PendingApprovalView.vue    # /espera-aprobacion
        ├── finance/
        │   ├── DashboardView.vue          # /dashboard
        │   ├── PaymentWizardView.vue      # /finanzas/reportar-pago (3 pasos)
        │   ├── TreasuryPaymentsView.vue   # /tesoreria/pagos
        │   └── TreasuryClosingView.vue    # /tesoreria/cierre
        ├── operations/
        │   ├── IncidentsFeedView.vue      # /incidencias
        │   ├── OperationsTasksView.vue    # /operaciones/tareas
        │   ├── SpokespersonGalleryView.vue# /voceros/galeria
        │   └── SecretaryLogbookView.vue   # /secretaria/bitacora
        └── admin/
            ├── AdminStructureView.vue     # /admin/estructura
            ├── AdminGhostUsersView.vue    # /admin/usuarios
            └── AdminBoardRolesView.vue    # /admin/junta
```

---

## 3. Contrato de Guardias de Navegación (`vue-router`)

1. **Rutas Públicas (`meta.public = true`):** `/login`, `/register`. Si el usuario ya está autenticado:
   - Si `es_activo == false` o `rol == 'FANTASMA'` -> redirige a `/espera-aprobacion`.
   - Si `es_activo == true` -> redirige a `/dashboard`.
2. **Ruta de Contención Fantasma (`/espera-aprobacion`):**
   - Accesible únicamente para usuarios autenticados con `es_activo == false`. Si un usuario ya fue activado (`es_activo == true`), redirige automáticamente a `/dashboard`.
3. **Rutas Protegidas Operativas (`meta.requiresActive = true`):**
   - Si no está autenticado -> redirige a `/login`.
   - Si `es_activo == false` -> redirige incondicionalmente a `/espera-aprobacion`.
   - Si la ruta declara `meta.roles` (ej. `['TESORERO']` para `/tesoreria/*` o `['PRESIDENTE', 'VICEPRESIDENTE']` para `/admin/*`) y el rol del usuario no coincide -> redirige a `/dashboard` con notificación de acceso restringido.

---

## 4. Contrato de Selectores Estables para Karate UI y Playwright

| Vista | Elemento | Selector Canónico |
| :--- | :--- | :--- |
| `/login` | Input correo / password / botón submit / error | `#login-correo`, `#login-password`, `#btn-login-submit`, `.banner--error` |
| `/register` | Campos de registro y selector de unidad | `#reg-nombre`, `#reg-cedula`, `#reg-correo`, `#reg-telefono`, `#reg-unidad`, `#reg-tipo-ocupante`, `#btn-register-submit` |
| `/espera-aprobacion` | Tarjeta de bloqueo fantasma | `#ghost-lock-screen`, `#btn-refresh-status`, `#btn-logout` |
| `/dashboard` | Tasa, Banner Cierre, Tabs, FAB Pagar | `#daily-rate-badge`, `#closing-banner`, `#tab-cobranza`, `#tab-gastos`, `#fab-reportar-pago` |
| `/finanzas/reportar-pago` | Pasos 1, 2, 3 y envío | `#step-1-monto`, `#select-moneda`, `#step-2-metodo`, `#input-referencia`, `#step-3-comprobante`, `#btn-submit-pago` |
| `/tesoreria/pagos` | Aprobar / Rechazar / Modal motivo | `.payment-card`, `.btn-approve-payment`, `.btn-reject-payment`, `#modal-reject-reason`, `#input-reject-motivo`, `#btn-confirm-reject` |
| `/incidencias` | Tarjeta, botón Me Sumo y Crear | `.incident-card`, `.btn-me-sumo`, `#btn-open-new-incident` |
