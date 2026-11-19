# 🎨 Frontend Mobile-First Vue 3 — Condominio App

**Componente:** `frontend/`  
**Stack:** Vue `3.5` (`<script setup lang="ts">`) · TypeScript Strict · Vite `6` · Pinia `2` · Vue Router `4` · pnpm `12` · Nginx `1.27-alpine` No-Root  
**Estándar:** Gobernanza y Calidad Nivel 11X (`Rule Zero` — 100% Docker Efímero)

---

## 1. Arquitectura e Invariantes Clave

- **Imagen Productiva Endurecida (`frontend/Dockerfile` + `frontend/nginx.conf`):** Build multi-stage con `.npmrc` Zero-Trust (`ignore-scripts=true`) y servidor **Nginx `1.27-alpine` no-root** (`UID/GID 101`, puerto `8080`, `--read-only`), compresión `gzip`, cabeceras OSHP/STIG preservadas en todos los bloques `location` y proxy inverso hacia `/api/`, `/health` y `/ws/`.
- **Sistema de Tokens `OKLCH` y `light-dark()` (`src/assets/tokens.css`):** Paleta perceptual unificada con soporte nativo para modo claro/oscuro (`ThemeToggleButton.vue`), `View Transitions API`, `@starting-style`, `calc-size()`, `@media (prefers-reduced-motion: reduce)` y `@media (forced-colors: active)`.
- **Geometría Anti-JSDOM y Shell Unificado:** Todas las vistas autenticadas viven bajo la ruta padre `<AppShellLayout>`, con `BottomNavBar` y `MobileNavDrawer` en móvil (`< 768px`, cierre de sesión accesible y áreas táctiles `>= 44x44px`), `SidebarNav` en escritorio (`>= 768px`), footer *in-flow* y gestión unificada de `<dialog>` en Top-Layer (`useTopLayerDialog`).
- **Stores Pinia No Destructivos y Seguridad Cliente:** Los 5 stores (`authStore`, `financeStore`, `operationsStore`, `governanceStore`, `accessAmenitiesStore`) conservan datos válidos ante fallos de red (`StaleDataBanner`), implementan refresco dual (`useDualRefresh`), idempotencia con `crypto.randomUUID()` (`useIdempotency`), cliente `apiClient.ts` con cookies `HttpOnly`, `X-CSRF-Token` y *single-flight refresh* ante `401`.
- **Invariantes Vue 3 / PropTech 11X:** Cobertura de **44/44 componentes `.vue`** sin huérfanos (`qa-orphans`), aritmética decimal exacta `ROUND_HALF_UP`, guarda `String(val.value ?? '').trim()` en entradas numéricas y cero exposición de UUIDs o llaves primarias crudas en la interfaz (`UI-11X-02`).
- **Aseguramiento E2E, Mutación y Rendimiento:** Patrón **Screenplay** en Playwright (`e2e/screenplay/`), auditoría **WCAG 2.1/2.2 AA** y `best-practice` con `@axe-core/playwright`, regresión visual en 4 viewports (`375x667`, `390x844`, `768x1024`, `1440x900`), **Stryker** (`stryker.conf.json`, `MSI >= 80%`), **Lighthouse CI** (`lighthouserc.cjs`, `CLS = 0`), **Karate UI** (`test/ui_business_flow.feature` vía `chrome-cdp`) y **SonarJS** (`CC <= 15`).

---

## 2. Estructura del Módulo

```text
frontend/
├── src/
│   ├── assets/             # Sistema de diseño perceptual OKLCH + light-dark() (tokens.css)
│   ├── components/         # Componentes comunes, layout (AppShellLayout, MobileNavDrawer, SidebarNav), finanzas, gobernanza y operaciones
│   ├── composables/        # useDualRefresh, useIdempotency, useThemeMode, useTopLayerDialog, useViewTransition
│   ├── router/             # Enrutador Vue Router con hidratación de sesión, guardias RBAC y fallback 404
│   ├── services/           # Cliente HTTP apiClient.ts (cookies HttpOnly, X-CSRF-Token y refresh single-flight)
│   ├── stores/             # 5 stores Pinia no destructivos + storeErrors.ts
│   ├── utils/              # security.ts, decimal.ts (ROUND_HALF_UP), navigationCatalog.ts, screenHelpCatalog.ts, navIcons.ts
│   └── views/              # Vistas por dominio (auth, finance, governance, operations, admin) + pruebas *.unit.ts
├── e2e/
│   ├── screenplay/         # Actores, Tareas y Preguntas Screenplay (core.ts, tasks.ts, questions.ts)
│   ├── fixtures/           # Mock stateful alineado 1:1 con esquemas OpenAPI y RBAC reales
│   └── *.e2e.ts            # Flujos autenticados, accesibilidad @axe-core y regresión visual PNG
├── test/                   # Escenarios BDD UI Gherkin (Karate Labs: ui_business_flow.feature)
├── Dockerfile              # Build multi-stage pnpm + nginx:1.27-alpine no-root (UID 101, puerto 8080)
├── nginx.conf              # Configuración productiva no-root con cabeceras OSHP y proxy inverso
├── stryker.conf.json       # Configuración de pruebas de mutación (MSI >= 80%)
├── lighthouserc.cjs        # Auditoría automatizada Lighthouse CI (CLS = 0)
└── Makefile                # Orquestación efímera Docker QA 11X
```

---

## 3. Comandos QA Efímeros (`Rule Zero` — `frontend/Makefile`)

Ejecute todas las validaciones en contenedores Docker efímeros sin Node ni pnpm instalados en el host:

```bash
make -C frontend qa-orphans     # Verifica 0 componentes .vue sin prueba unitaria (44/44)
make -C frontend qa-lint        # pnpm audit + vue-tsc --noEmit + Prettier + ESLint (SonarJS CC <= 15)
make -C frontend qa-unit        # Vitest + cobertura V8 (>= 95%) + build Vite de producción
make -C frontend qa-mutation    # Pruebas de mutación Frontend con Stryker (qa-vue3 + ui-e2e, MSI >= 80%)
make -C frontend qa-e2e         # Playwright Screenplay + @axe-core WCAG 2.1 AA + 24 PNGs (4 viewports)
make -C frontend qa-perf        # Lighthouse CI multi-corrida (Performance >= 90%, A11y >= 95%, BP >= 95%, CLS = 0)
make -C frontend qa-bdd         # Escenarios BDD UI en Gherkin (Karate Labs + sidecar chrome-cdp)
make -C frontend build-ui       # Compila dist/ y levanta entorno QA (ui-api-mock, ui-prod, chrome-cdp)
make -C frontend qa-all         # Pipeline integral (lint + orphans + unit + mutation + perf + e2e + bdd)
make -C frontend clean-cache    # Detiene contenedores y elimina volúmenes de caché pnpm QA
```

---

## 4. Documentación Relacionada

- **[`frontend/TESTING.md`](./TESTING.md)** — Bitácora detallada de suites unitarias, Screenplay E2E, WCAG, Lighthouse y Karate UI.
- **[`README.md`](../README.md)** — Presentación general del sistema y despliegue productivo Docker Hub.
- **[`docs/qa/README.md`](../docs/qa/README.md)** — Guía maestra de la pirámide QA Nivel 11X y arquitectura Thin-Repo.
- **[`SECURITY.md`](../SECURITY.md)** — Política de seguridad y catálogo de los **22 vectores** mitigados.
