# Guía de Pruebas y QA para Frontend (Vue 3) - Condominio App

Este documento describe la estrategia corporativa **Nivel 11X** para pruebas automatizadas, calidad estética, accesibilidad (WCAG 2.1 AA) y rendimiento (Core Web Vitals) para el **Frontend en Vue 3** de Condominio App.

---

## 1. Reglas de Ejecución Efímera en Docker y Zero-Trust

* **Gestor de Paquetes:** Uso obligatorio de `pnpm` con configuración Zero-Trust (`.npmrc` con `ignore-scripts=true`).
* **Caché Persistente:** El volumen `pnpm-store` evita descargas redundantes entre corridas.
* **Contenedores Utilizados:**
  * `qa-vue3` (`node:20-bookworm-slim`): Para linting, type-checking, Vitest y mutación con Stryker.
  * `ui-e2e` (`mcr.microsoft.com/playwright:v1.43.0-jammy`): Para regresión visual de Playwright y auditorías de Lighthouse CI.
  * `ui-prod` (`nginx:alpine`): Servidor estático que levanta el bundle compilado de Vue para pruebas E2E.
  * `karatelabs` (`sinfallas/karatelabs:latest`): Pruebas de aceptación BDD en navegador headless.
  * `nginx-exporter` y `prometheus`: Observabilidad de tráfico en pruebas de interfaz.

---

## 2. Pila Tecnológica y Separación de Responsabilidades

1. **Lógica y Componentes Aislados:** `Vitest` + `jsdom` (ejecución ultra-rápida, mocks de API, cobertura ≥ 95%).
2. **Calidad de Código y Estética:** `ESLint` + `Prettier` + `typescript-eslint`.
3. **Deuda Técnica y Complejidad:** `eslint-plugin-sonarjs` (limita la complejidad cognitiva en componentes) y `eslint-plugin-security`.
4. **Pruebas de Mutación Frontend:** `Stryker` (`@stryker-mutator/vitest-runner`) alterando código en `.vue` y `.ts`.
5. **Regresión Visual y Accesibilidad:** `Playwright` + `@axe-core/playwright` (auditoría WCAG 2.1 AA y snapshots pixel-perfect).
6. **Rendimiento y Core Web Vitals:** `Lighthouse CI` (`@lhci/cli`) con exigencia de Score ≥ 90 en performance y ≥ 95 en accesibilidad.
7. **Aceptación BDD:** `Karate Labs` con navegador Chromium headless.
8. **Observabilidad:** `Nginx Prometheus Exporter` + `Prometheus` (monitoreo pasivo de peticiones HTTP en frontend).

---

## 3. Configuración de Referencia: `package.json`

```json
{
  "name": "condominio-app-frontend",
  "version": "1.0.0",
  "description": "Frontend Mobile-First en Vue 3 para Condominio App",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc --noEmit && vite build",
    "type-check": "vue-tsc --noEmit",
    "format": "prettier --write \"src/**/*.{js,ts,vue}\" \"tests/**/*.{js,ts}\"",
    "format:check": "prettier --check \"src/**/*.{js,ts,vue}\" \"tests/**/*.{js,ts}\"",
    "lint": "eslint . --ext .vue,.js,.ts",
    "test:unit": "vitest run",
    "test:coverage": "vitest run --coverage",
    "mutate": "stryker run",
    "audit:deps": "pnpm audit",
    "test:e2e": "playwright test",
    "test:perf": "lhci autorun"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.3.0",
    "pinia": "^2.1.7",
    "axios": "^1.6.8"
  },
  "devDependencies": {
    "@axe-core/playwright": "^1.2.3",
    "@lhci/cli": "^0.13.0",
    "@playwright/test": "^1.43.0",
    "@stryker-mutator/core": "^8.2.6",
    "@stryker-mutator/vitest-runner": "^8.2.6",
    "@typescript-eslint/eslint-plugin": "^7.1.1",
    "@typescript-eslint/parser": "^7.1.1",
    "@vitest/coverage-v8": "^1.3.1",
    "@vue/test-utils": "^2.4.4",
    "eslint": "^8.56.0",
    "eslint-config-prettier": "^9.1.0",
    "eslint-plugin-security": "^3.0.0",
    "eslint-plugin-sonarjs": "^0.24.0",
    "eslint-plugin-vue": "^9.21.1",
    "jsdom": "^24.0.0",
    "prettier": "^3.2.5",
    "typescript": "^5.3.0",
    "vite": "^5.1.0",
    "vitest": "^1.3.0",
    "vue-eslint-parser": "^9.4.2",
    "vue-tsc": "^1.8.27"
  }
}
```

---

## 4. Archivos de Configuración de Calidad

### A. `vitest.config.ts` (Pruebas Unitarias y Cobertura 95%)
```typescript
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'jsdom',
    // Tool Boundary Estricto: Solo pruebas marcadas explícitamente como unitarias
    include: ['src/**/*.unit.{ts,tsx}', 'src/**/*.spec.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      thresholds: {
        lines: 95,
        functions: 95,
        branches: 95,
        statements: 95,
      },
      exclude: [
        'coverage/**',
        'dist/**',
        'playwright-report/**',
        'lhci-reports/**',
        '.stryker-tmp/**',
        'e2e/**',
        'test/**',
        '**/*.d.ts',
        '*.config.ts',
        '*.config.js'
      ]
    }
  }
});
```

### B. `playwright.config.ts` (Regresión Visual, E2E y Accesibilidad)
```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.e2e.ts',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL: 'http://ui-prod:80',
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
    timezoneId: 'America/Caracas',
    locale: 'es-VE',
  },
  projects: [
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 13'] }, // Enfoque Mobile-First
    },
    {
      name: 'Desktop Chrome',
      use: { ...devices['Desktop Chrome'] },
    }
  ],
  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.01,
      animations: 'disabled', // Congela transiciones CSS para evitar diferencias por ms
      threshold: 0.1,
    },
  },
});
```

### C. `stryker.conf.json` (Mutación de Frontend)
```json
{
  "$schema": "./node_modules/@stryker-mutator/core/schema/stryker-schema.json",
  "packageManager": "pnpm",
  "reporters": ["html", "clear-text", "progress"],
  "testRunner": "vitest",
  "coverageAnalysis": "perTest",
  "mutate": [
    "src/**/*.ts",
    "src/**/*.vue",
    "!src/main.ts",
    "!src/**/*.spec.ts",
    "!src/**/*.unit.ts",
    "!src/**/*.d.ts"
  ]
}
```

### D. `lighthouserc.js` (Rendimiento Core Web Vitals)
```javascript
module.exports = {
  ci: {
    collect: {
      url: ['http://ui-prod:80/'],
      numberOfRuns: 3,
    },
    assert: {
      assertions: {
        'categories:performance': ['error', { minScore: 0.9 }],
        'categories:accessibility': ['error', { minScore: 0.95 }],
        'categories:best-practices': ['error', { minScore: 0.9 }],
        'categories:seo': ['error', { minScore: 0.9 }],
      },
    },
    upload: {
      target: 'filesystem',
      outputDir: './lhci-reports',
    },
  },
};
```

---

## 5. Orquestador Docker Efímero: `docker-compose.qa.yml`

Ubicado en `frontend/` (o raíz del proyecto según la estructura monorepo):

```yaml
services:
  ui-prod:
    image: nginx:alpine
    container_name: condominio_frontend_ui_prod
    hostname: condominio_frontend_ui_prod
    pull_policy: always
    environment:
      TZ: 'America/Caracas'
    volumes:
      - ./dist:/usr/share/nginx/html:ro
      - nginx-logs:/var/log/nginx
    ports:
      - "8080:80"

  qa-vue3:
    image: node:20-bookworm-slim
    container_name: condominio_qa_vue3
    hostname: condominio_qa_vue3
    pull_policy: if_not_present
    environment:
      TZ: 'America/Caracas'
      PNPM_HOME: /pnpm
    volumes:
      - .:/app
      - pnpm-store:/pnpm
    working_dir: /app
    command: bash -c "echo 'Contenedor QA Vue 3 listo para Vitest y Lint'; sleep infinity"

  ui-e2e:
    image: mcr.microsoft.com/playwright:v1.43.0-jammy
    container_name: condominio_frontend_ui_e2e
    hostname: condominio_frontend_ui_e2e
    pull_policy: always
    environment:
      TZ: 'America/Caracas'
      PNPM_HOME: /pnpm
    volumes:
      - .:/app
      - pnpm-store:/pnpm
    working_dir: /app
    command: bash -c "echo 'Contenedor E2E Playwright listo'; sleep infinity"

  karatelabs:
    image: sinfallas/karatelabs:latest
    container_name: condominio_frontend_karate
    hostname: condominio_frontend_karate
    pull_policy: always
    depends_on:
      - ui-prod
    environment:
      - UI_BASE_URL=http://ui-prod:80
    volumes:
      - ./test:/app/src/test/java/examples/test
    command: bash -c "echo 'Contenedor Karate listo'; sleep infinity"

  nginx-exporter:
    image: nginx/nginx-prometheus-exporter:latest
    container_name: condominio_frontend_nginx_exporter
    hostname: condominio_frontend_nginx_exporter
    profiles:
      - observability
    command:
      - "-nginx.scrape-uri=http://ui-prod:80/stub_status"
    ports:
      - "9113:9113"
    depends_on:
      - ui-prod

  prometheus:
    image: prom/prometheus:latest
    container_name: condominio_frontend_prometheus
    hostname: condominio_frontend_prometheus
    profiles:
      - observability
    entrypoint:
      - /bin/sh
      - -c
      - |
        echo "
        global:
          scrape_interval: 2s
        scrape_configs:
          - job_name: 'vue_nginx'
            static_configs:
              - targets: ['nginx-exporter:9113']
        " > /tmp/prometheus.yml
        /bin/prometheus --config.file=/tmp/prometheus.yml
    ports:
      - "9090:9090"
    depends_on:
      - nginx-exporter

volumes:
  nginx-logs:
  pnpm-store:
    name: condominio_vue3_pnpm_store
```

---

## 6. Comandos Operativos: `Makefile`

```makefile
.PHONY: qa-lint qa-unit qa-mutation qa-perf qa-e2e qa-bdd qa-obs qa-all build-ui clean-cache

COMPOSE_FILE = docker-compose.qa.yml
SERVICE_NAME = qa-vue3
E2E_SERVICE = ui-e2e

build-ui:
	@echo "🏗️ Compilando Vue 3 con Vite para Nginx de producción..."
	docker compose -f $(COMPOSE_FILE) run --rm $(SERVICE_NAME) bash -c "pnpm install && pnpm run build"
	docker compose -f $(COMPOSE_FILE) up -d ui-prod

qa-lint:
	@echo "🔍 Auditoría de Dependencias, Tipado (vue-tsc), Prettier y ESLint SonarJS..."
	docker compose -f $(COMPOSE_FILE) run --rm $(SERVICE_NAME) bash -c "pnpm install && pnpm run audit:deps && pnpm run type-check && pnpm run format:check && pnpm lint"

qa-unit:
	@echo "🧪 Pruebas Unitarias Aisladas (Vitest - Cobertura >=95%)..."
	docker compose -f $(COMPOSE_FILE) run --rm $(SERVICE_NAME) bash -c "pnpm install && pnpm run test:coverage"

qa-mutation:
	@echo "👽 Pruebas de Mutación Frontend (Stryker)..."
	docker compose -f $(COMPOSE_FILE) run --rm $(SERVICE_NAME) bash -c "pnpm install && pnpm run mutate"

qa-perf: build-ui
	@echo "⚡ Auditoría de Rendimiento Core Web Vitals (Lighthouse CI)..."
	docker compose -f $(COMPOSE_FILE) run --rm $(E2E_SERVICE) bash -c "pnpm install && pnpm run test:perf"

qa-e2e: build-ui
	@echo "🎭 Regresión Visual y Accesibilidad WCAG (Playwright)..."
	docker compose -f $(COMPOSE_FILE) run --rm $(E2E_SERVICE) bash -c "pnpm install && pnpm exec playwright test"

qa-bdd: build-ui
	@echo "📚 Pruebas de Aceptación Funcional (Karate UI)..."
	docker compose -f $(COMPOSE_FILE) run --rm karatelabs mvn clean test

qa-obs: build-ui
	@echo "📊 Levantando Observabilidad Frontend (Prometheus + Nginx Exporter)..."
	docker compose -f $(COMPOSE_FILE) --profile observability up -d prometheus nginx-exporter

qa-all: qa-lint qa-unit qa-mutation qa-perf qa-e2e qa-bdd
	@echo "✅ Pipeline QA Frontend (Vue 3) completado con éxito."

clean-cache:
	@echo "🧹 Limpiando volúmenes de caché de pnpm..."
	docker compose -f $(COMPOSE_FILE) down -v
	docker compose -f $(COMPOSE_FILE) --profile observability down -v
```

---

## 7. Ejemplos de Pruebas de Frontend

### A. Prueba Unitaria de Store Pinia (`src/stores/auth.unit.ts`)
```typescript
import { setActivePinia, createPinia } from 'pinia';
import { describe, beforeEach, it, expect, vi } from 'vitest';
import { useAuthStore } from './auth';

describe('Auth Store (Flujo Fantasma)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('Inicia en estado no autenticado', () => {
    const auth = useAuthStore();
    expect(auth.isAuthenticated).toBe(false);
    expect(auth.user).toBeNull();
  });

  it('Detecta correctamente el estado de usuario fantasma inactivo', () => {
    const auth = useAuthStore();
    auth.setUser({
      id: 1,
      nombre: 'Juan Fantasma',
      rol: 'FANTASMA',
      es_activo: false
    });

    expect(auth.isAuthenticated).toBe(true);
    expect(auth.isAwaitingApproval).toBe(true);
  });
});
```

### B. Accesibilidad WCAG 2.1 AA y Regresión Visual (`e2e/accessibility.e2e.ts`)
```typescript
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const RUTAS_CRITICAS = ['/', '/login', '/espera-aprobacion'];

test.describe('Auditoría WCAG 2.1 AA y Regresión Visual Snapshot', () => {
  for (const route of RUTAS_CRITICAS) {
    test(`Ruta "${route}" debe ser accesible y mantener diseño pixel-perfect`, async ({ page }) => {
      // Mock determinista para datos dinámicos
      await page.route('**/api/**', async (r) => {
        await r.fulfill({ json: { status: 'mocked', data: [] } });
      });

      await page.goto(route);
      await page.waitForLoadState('networkidle');
      await page.evaluate(() => document.fonts.ready);

      // Verificación estricta de accesibilidad
      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();

      expect(results.violations).toEqual([]);

      // Snapshot visual (falla si hay diferencia de CSS o layout)
      await expect(page).toHaveScreenshot(`snapshot-${route.replace(/\//g, '') || 'home'}.png`, {
        fullPage: true,
      });
    });
  }
});
```
