# 🛡️ QA Testing & Calidad Nivel 11X - Condominio App

Bienvenido al centro de documentación del estándar de calidad, pruebas automatizadas y resiliencia para el proyecto **Condominio App**.

Este repositorio sigue rigurosamente el estándar corporativo **Nivel 11X (QA Blueprint x11)**, lo que garantiza que todo el software producido (Backend en FastAPI y Frontend en Vue 3) esté matemáticamente probado, aislado de la red durante pruebas unitarias, libre de vulnerabilidades de seguridad estáticas y dinámicas, y certificado contra fallos catastróficos mediante Ingeniería del Caos.

---

## 📚 Índice de Documentación de QA

1. **[Filosofía y Principios Nivel 11X (`QA_PHILOSOPHY_11X.md`)](./QA_PHILOSOPHY_11X.md):**
   * Los 11 pilares innegociables de calidad.
   * La regla del **95% de cobertura como piso mínimo**.
   * Paranoia positiva (pruebas de mutación).
   * Efimeridad absoluta: Cero compilaciones locales (`docker build`), uso exclusivo de imágenes base oficiales (`sinfallas/*`) y cachés persistentes.
   * Monitoreo y Observabilidad universal (Métricas RED).

2. **[Guía de Pruebas para Backend FastAPI (`BACKEND_FASTAPI_QA.md`)](./BACKEND_FASTAPI_QA.md):**
   * Pila tecnológica completa: `ruff`, `mypy`, `pytest`, `pytest-cov`, `pytest-mock`, `mutmut`, `schemathesis`, `Karate Labs`, `locust`, `radon`, `py-spy`, `OWASP ZAP`, `Pumba`.
   * Estructura del `docker-compose.qa.yml` y targets del `Makefile` (`make qa-unit`, `make qa-lint`, `make qa-mutation`, `make qa-all`).
   * Configuración de referencia de `pyproject.toml`.
   * Observabilidad obligatoria con `prometheus-fastapi-instrumentator`.
   * Ejemplos de pruebas unitarias con mocking, pruebas de contratos BDD y pruebas de caos/estrés con Locust.

3. **[Guía de Pruebas para Frontend Vue 3 (`FRONTEND_VUE3_QA.md`)](./FRONTEND_VUE3_QA.md):**
   * Pila tecnológica completa: `pnpm` (Zero-Trust), `Vitest` + `jsdom`, `ESLint` + `Prettier` + `SonarJS`, `Stryker`, `Playwright` + `@axe-core`, `Lighthouse CI`, `Karate Labs`.
   * Estructura del `docker-compose.qa.yml` y targets del `Makefile` (`make qa-unit`, `make qa-perf`, `make qa-e2e`, etc.).
   * Configuraciones de referencia: `package.json`, `vitest.config.ts`, `playwright.config.ts`, `stryker.conf.json`, `lighthouserc.js`.
   * Regresión visual pixel-perfect y accesibilidad estricta WCAG 2.1 AA.

4. **[CI/CD Pipelines y Git Hooks Locales (`CI_CD_AND_HOOKS.md`)](./CI_CD_AND_HOOKS.md):**
   * Paridad absoluta: el runner de CI ejecuta exactamente los mismos comandos de Docker/Make que en local.
   * Pipeline completo para GitHub Actions (`qa-pipeline.yml`).
   * Auditoría de infraestructura con Trivy (`auditar-infra.sh`).
   * Barrera de entrada local con `Lefthook` (pre-commit, commit-msg, pre-push) para bloquear commits con fallos de linting o secretos expuestos.

5. **[Directivas de Sistema para Inteligencia Artificial (`AI_MASTER_PROMPT.md`)](./AI_MASTER_PROMPT.md):**
   * Rol y reglas para agentes de IA (Staff QA Automation Engineer).
   * Filosofía *Fail & Forbid*.
   * Protocolo de fusión no destructiva de archivos de configuración (`.example`).
   * Enrutamiento de contexto y directivas de generación de código.

---

## 🛠 Matriz Resumida de Herramientas para Condominio App

| Capa de Validación | Backend (FastAPI / Python) | Frontend (Vue 3 / TypeScript) |
| :--- | :--- | :--- |
| **Linting y Tipado** | `ruff` + `mypy (strict=true)` | `ESLint` + `Prettier` + `vue-tsc` |
| **Pruebas Unitarias & Mocking** | `pytest` + `TestClient` + `pytest-mock` | `Vitest` + `jsdom` + `v8` |
| **Piso de Cobertura** | **≥ 95%** obligatorio (`pytest-cov`) | **≥ 95%** obligatorio (`@vitest/coverage-v8`) |
| **Pruebas de Mutación** | `mutmut` | `Stryker` (`@stryker-mutator/vitest-runner`) |
| **Deuda Técnica & Complejidad** | `radon` (Grado A/B) | `eslint-plugin-sonarjs` (Complejidad cognitiva baja) |
| **Profiling de Rendimiento** | `py-spy` (*Flamegraphs* CPU/RAM) | `Lighthouse CI` (Core Web Vitals ≥ 90) |
| **Seguridad Estática (SAST)** | `bandit` + `uv pip audit` | `eslint-plugin-security` + `npm/pnpm audit` |
| **Seguridad Dinámica (DAST)** | `OWASP ZAP` (Baseline Scan en red interna) | N/A (Consumido desde API) |
| **Contratos y Fuzzing** | `schemathesis` (Ataque a `openapi.json`) | N/A |
| **Aceptación y BDD** | `Karate Labs` (Escenarios Gherkin `.feature`) | `Karate Labs` (UI Headless) |
| **E2E & Accesibilidad** | N/A | `Playwright` + `@axe-core` (WCAG 2.1 AA) |
| **Ingeniería del Caos** | `Pumba` + `Locust` (Jitter de red y estrés) | N/A |
| **Observabilidad en Vivo** | `prometheus-fastapi-instrumentator` (`/metrics`) | `nginx-prometheus-exporter` |
| **Auditoría de Infraestructura** | `aquasec/trivy` (IaC + FileSystem) | `aquasec/trivy` (IaC + FileSystem) |
| **Control Pre-Commit Local** | `Lefthook` | `Lefthook` |
