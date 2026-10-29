# 🧪 Tipos de Pruebas en el Estándar QA 11X y Cómo Utilizarlos

> **PROPÓSITO:**  
> Guía técnica canónica de los 13 niveles de la pirámide de calidad 11X aplicada a **Condominio App**.

---

## 🏛️ La Pirámide de Calidad Nivel 11X

```text
               ▲
              / \
             /   \      [13] Fixtures Trimodales & Invariantes Negativos (Fantasma / Nominal / Candado)
            /     \     [12] Ingeniería del Caos (Pumba) & Resiliencia
           /       \    [11] Seguridad Dinámica DAST (OWASP ZAP)
          /         \   [10] Rendimiento & Estrés (Locust / py-spy / Lighthouse CI)
         /           \  [09] Accesibilidad WCAG 2.1 AA & Geometría Visual (Playwright + Axe)
        /             \ [08] Mutación: Pruebas de las Pruebas (Mutmut / Stryker)
       /               \[07] BDD UI Aceptación (Karate Labs UI en Chrome Headless)
      /                 \[06] BDD API Caja Negra (Karate Labs HTTP)
     /                   \[05] Contratos OpenAPI & Fuzzing (Schemathesis)
    /                     \[04] Paridad de Esquema DB & Migraciones Reales (Alembic + Postgres 17)
   /                       \[03] Pruebas Unitarias Aisladas (Pytest / Vitest >= 95%)
  /                         \[02] Tipado Estricto & Complejidad (Mypy / Radon / vue-tsc / SonarJS)
 /                           \[01] Análisis Estático, Formateo & SAST (Ruff / ESLint / Bandit / Trivy)
─────────────────────────────────────────────────────────────────────────────────────────────
```

---

## Resumen de Comandos de Ejecución Efímera (`Rule Zero`)

### Backend (`backend/Makefile`)
- `make -C backend qa-lint`: Ruff + Mypy (`--strict`) + Bandit (SAST).
- `make -C backend qa-complexity`: Radon (`CC <= B`, `MI >= B`) validado por `scripts/radon_gates.py`.
- `make -C backend qa-deps`: Auditoría de vulnerabilidades en dependencias (`uv audit`).
- `make -C backend qa-unit`: Pruebas unitarias aisladas con cobertura obligatoria `>= 95%`.
- `make -C backend qa-parity`: Validador `.agents/scripts/verify_alembic_orm_parity.py` + ciclo completo de migraciones Alembic contra `postgres:17-alpine`.
- `make -C backend qa-contracts`: Fuzzing de contratos OpenAPI con Schemathesis.
- `make -C backend qa-bdd`: Escenarios Gherkin de caja negra en Karate Labs (`backend/test/api_test.feature`).
- `make -C backend qa-dast`: Escaneo dinámico OWASP ZAP Baseline contra la API viva.
- `make -C backend qa-chaos`: Ingeniería del Caos con Pumba (`netem` 500ms) + Locust + Prometheus.

### Frontend (`frontend/Makefile`)
- `make -C frontend qa-lint`: Auditoría de dependencias (`pnpm audit`), `vue-tsc --noEmit`, Prettier y ESLint + SonarJS + Security.
- `make -C frontend qa-orphans`: Certificación de 0 componentes `.vue` sin prueba unitaria (`verify_zero_orphan_vue_components.py`).
- `make -C frontend qa-unit`: Vitest + cobertura v8 `>= 95%`.
- `make -C frontend qa-mutation`: Pruebas de mutación con Stryker.
- `make -C frontend qa-e2e`: Regresión visual Mobile/Desktop y accesibilidad WCAG 2.1 AA con Playwright + `@axe-core/playwright`.
- `make -C frontend qa-perf`: Core Web Vitals (`>= 0.90`) y Accesibilidad (`>= 0.95`) con Lighthouse CI.
- `make -C frontend qa-bdd`: Flujos interactivos de negocio con Karate UI en Chrome Headless (`frontend/test/ui_business_flow.feature`).

### Compuerta Universal Pre-Commit
```bash
./.agents/scripts/certify_task_completion.sh
```
