# 🎨 Especificación 05: Arquitectura GUI Vue 3 Mobile-First y Ergonomía Nivel 11X

**Estado:** Hitos 5, 6 y 7 Completados en `frontend/` (100% Vistas Auth, Finanzas/Tesorería, Operaciones/Incidencias/Conserjería y Administración implementadas con 0 componentes huérfanos) / Hito 8 (Certificación E2E/Lighthouse) pendiente  
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
| `/operaciones/tareas` | Progreso diario y casillas de conserjería | `#daily-tasks-progress`, `#task-check-{id}`, `#btn-complete-task-{id}` |
| `/voceros/galeria` | Indicador de cuota 30 fotos/mes y formulario | `#photo-quota-badge`, `#photo-quota-progress`, `#btn-submit-vocero-foto` |
| `/secretaria/bitacora` | Formulario y tarjetas de actas | `#input-acta-contenido`, `#btn-submit-acta`, `.acta-card` |
| `/admin/estructura` | Generador idempotente de torres/unidades | `#form-generar-estructura`, `#input-est-nombre`, `#input-est-identificadores`, `#btn-submit-estructura` |
| `/admin/usuarios` | Bandeja de activación de Usuarios Fantasma | `[data-testid="ghost-user-card-{id}"]`, `#select-unit-{id}`, `#select-rol-{id}`, `#btn-activate-user-{id}` |
| `/admin/junta` | Asignación de cargos directivos | `#form-asignar-junta`, `#input-junta-usuario-id`, `#select-junta-cargo`, `#btn-submit-junta` |

---

## 5. Arquitectura GUI de Fase 4 (Hitos 10 al 13 — PropTech & LPH)

Todos los componentes nuevos deben cumplir el invariante **Cero Componentes Huérfanos** (`make -C frontend qa-orphans`), **Catch No Destructivo** en Pinia (`isStale = true` conservando el último estado válido) y **Geometría Anti-JSDOM** (respetando el flujo de `AppShellLayout.vue` y `BottomNavBar.vue`):

| Hito | Ruta Vue 3 | Vista / Componente | Store Pinia | Selectores Canónicos (`data-testid` / `id`) |
| :--- | :--- | :--- | :--- | :--- |
| **Hito 10** | `/tesoreria/facturacion` | `BillingGeneratorView.vue` + `ReceiptBreakdownModal.vue` | `useFinanceStore` | `#form-facturar-periodo`, `#input-facturar-periodo`, `#btn-submit-facturacion`, `#modal-recibo-desglose` |
| **Hito 10** | `/finanzas/solvencia` | `SolvencyCertificateView.vue` | `useFinanceStore` | `#card-solvencia-status`, `#btn-emitir-solvencia`, `#qr-solvencia-badge` |
| **Hito 11** | `/consultas` y `/consultas/:id` | `ConsultationsListView.vue`, `ConsultationDetailView.vue`, `VoteReceiptModal.vue` | `useGovernanceStore` | `.consultation-card`, `#quorum-progress-bar`, `#btn-cast-vote`, `#modal-vote-receipt`, `#btn-close-consultation` |
| **Hito 12** | `/accesos/pases` y `/operaciones/garita-qr` | `VisitorPassesView.vue`, `GatehouseScannerView.vue` | `useAccessAmenitiesStore` | `#form-crear-pase-qr`, `#qr-pass-card-{id}`, `#input-scan-qr-token`, `#btn-verify-qr` |
| **Hito 12** | `/operaciones/paqueteria` | `ParcelsTrackerView.vue` | `useAccessAmenitiesStore` | `#form-registrar-paquete`, `.parcel-card`, `#btn-confirm-parcel-{id}` |
| **Hito 13** | `/reservas/areas` | `AmenitiesReservationView.vue` | `useAccessAmenitiesStore` | `#solvency-gate-banner`, `.amenity-card`, `#form-solicitar-reserva`, `#btn-submit-reserva` |
| **Hito 14** | Universal (Todas las Vistas) | `ContextualHelpModal.vue` (`frontend/src/components/layout/ContextualHelpModal.vue`) | `screenHelpCatalog.ts` | `#btn-contextual-help`, `#dialog-contextual-help`, `#help-screen-title`, `#help-steps-list`, `#btn-close-help` |

---

## 6. Sistema Universal de Ayuda Contextual Responsiva (`refactoring-ui` + `modern-web-guidance`) y Manuales en Markdown (Hito 14)

### 6.1. Reglas de Diseño Responsivo y Jerarquía Visual (`refactoring-ui` + `modern-web-guidance`)
Ningún componente, botón de ayuda ni diálogo modal utiliza dimensiones fijas rígidas. Toda la interfaz aplica las siguientes reglas del sistema de diseño:
1. **Escalado Fluido Basado en Contenedor (`container-type: inline-size` + `clamp()`):**
   - `AppShellLayout.vue` declara `container-type: inline-size; container-name: main-canvas;` y limita el ancho máximo del lienzo de trabajo a `max-inline-size: 76rem; margin-inline: auto;` (*"Give an element the width it needs: a 1400px canvas is not a 1400px requirement"*).
   - El relleno (*padding*) y los tamaños tipográficos escalan suavemente con `clamp()` y unidades de contenedor (`cqi`) o viewport dinámico (`dvh`), garantizando que el máximo nunca supere $2.5\times$ el mínimo para respetar el zoom de accesibilidad WCAG 2.1 AA.
2. **Adaptación por Dispositivo de Entrada (`@media (pointer: coarse)` vs `pointer: fine`):**
   - En lugar de imponer tamaños fijos, los botones de acción y el disparador `#btn-contextual-help` emplean un diseño compacto y proporcionado en cursores de escritorio (`padding: 0.375rem 0.75rem`) y expanden automáticamente su área interactiva en pantallas táctiles mediante `@media (pointer: coarse)` (`min-block-size: 2.75rem; padding: 0.5rem 0.875rem`).
3. **Diálogo de Ayuda Contextual Fluido (`ContextualHelpModal.vue`):**
   - Usa el elemento nativo `<dialog>` con `overscroll-behavior: contain` tanto en `dialog:modal` como en `dialog::backdrop` (`overflow: hidden`).
   - En móviles estrechos se adapta fluidamente (`inline-size: min(100% - 1.5rem, 36rem); max-block-size: min(85dvh, 42rem); padding: clamp(1rem, 3cqi, 1.75rem)`), y la longitud de línea de las explicaciones se restringe a `max-inline-size: 65ch` con `text-wrap: pretty` en párrafos y `text-wrap: balance` en títulos para lectura óptima (45–75 caracteres por línea).
4. **Alineación Tabular en Cifras Financieras (`tabular-nums`):**
   - Todo monto en USD, VES, tasa BCV o porcentaje de alícuota aplica `font-variant-numeric: tabular-nums` y alineación derecha en tablas de escritorio para que los decimales coincidan verticalmente.
5. **Contenido Dinámico Sensible a la Ruta y al Rol (`frontend/src/utils/screenHelpCatalog.ts`):**
   - Al pulsarse `#btn-contextual-help`, `ContextualHelpModal.vue` detecta la ruta activa (`useRoute().path`) y el rol del usuario (`authStore.user?.rol`) y muestra:
     - **Propósito de la Pantalla** (jerarquía primaria/secundaria clara).
     - **Guía Paso a Paso (1, 2, 3)** adaptada al rol (Propietario/Inquilino/Conserje vs Presidente/Tesorero/Secretario/Vocero).
     - **Consejos y Errores Frecuentes.**

### 6.2. Manuales Maestros en Markdown Editables y Exportables a PDF (`docs/`)
El repositorio mantiene dos manuales independientes en formato Markdown puro (`.md`) con estructura limpia de capítulos, tablas y listas numeradas para que cualquier administrador pueda editarlos fácilmente y exportarlos a **PDF** (`pandoc`, VS Code Markdown PDF o impresión desde visor Markdown) para enviarlos por WhatsApp o correo electrónico:
1. **`docs/MANUAL_ADMINISTRADOR_E_INSTALADOR.md`:**
   - **Parte I (Instalador / Soporte Técnico):** Despliegue con Docker Compose, configuración de variables `.env`, proxy reverso / SSL, respaldos de PostgreSQL 17 y MinIO, y uso de `scripts/limpieza.sh`.
   - **Parte II (Administrador / Junta de Condominio):** Configuración inicial de Torres/Calles y Unidades (`/admin/estructura`), carga de alícuotas o cuotas fijas mensuales, activación de Usuarios Fantasma (`/admin/usuarios`), designación de Junta (`/admin/junta`), flujo completo de Tesorería (Tasa BCV, Egresos, Facturación Trimodal `CUOTA_FIJA` / `ALICUOTA` / `PARTES_IGUALES`, Aprobación/Rechazo de Pagos, Solvencias y Candado Contable), Cartas Consulta (Art. 23 LPH), Bitácora, Conserjería y Garita QR.
   - **Anexo:** Comando e instrucciones paso a paso para generar el PDF listo para distribuir.
2. **`docs/MANUAL_USUARIO_RESIDENTE.md`:**
   - Manual redactado en lenguaje claro y directo para **Propietarios, Inquilinos y Conserjes**: registro inicial y activación de cuenta, consulta del Dashboard Financiero y recibos, cómo reportar pagos en Bs o USD paso a paso, uso del botón "¡Me sumo!" en incidencias, votación en Cartas Consulta y verificación de su recibo criptográfico, generación de Pases QR para visitantes, retiro de paquetes en garita, reserva de áreas sociales y descarga del Certificado de Solvencia.
