---
name: qa-11x-docker-certifier
description: >-
  QA 11X Corporate Standard certifier in ephemeral Docker containers. Enforces Rule Zero
  (zero host executions on Ubuntu/macOS), Cyclomatic/Cognitive Complexity Grade A/B, unit test coverage >= 95%,
  mutation testing, WCAG 2.1 AA accessibility, Lighthouse CI, and silent mode RAM conservation.
---

# QA 11X Corporate Standard Certifier (Ephemeral Docker Execution)

This skill governs all tests, linters, audits, and cleanups in projects implementing QA 11X.
> **OUTPUT LANGUAGE CONSTRAINT:** Always communicate with the user and write final explanations in Spanish.

---

## 1. Rule Zero: Total Isolation in Docker Containers

- **STRICTLY FORBIDDEN:** Executing `pip`, `uv`, `pytest`, `ruff`, `mypy`, `npm`, `pnpm`, `vitest`, `stryker`, or `playwright` directly on the host machine.
- Every validation command MUST execute inside ephemeral containers defined in `docker-compose.qa.yml` via `Makefile` targets (`make qa-lint`, `make qa-unit`, `make qa-parity`, `make qa-mutation`, `make qa-e2e`, `make qa-perf`, `make qa-bdd`).

---

## 2. Strict QA 11X Approval Thresholds

| Ecosystem | Tool / Suite | Mandatory Gate | Container Command |
| :--- | :--- | :--- | :--- |
| **Backend (FastAPI)** | `Ruff` + `Mypy --strict` + `Bandit` | **0 errors / 0 vulnerabilities** | `make -C backend qa-lint` |
| **Backend (FastAPI)** | `Radon` (Cyclomatic Complexity) | **Grade A/B (`CC <= B`, `MI >= B`)** | `make -C backend qa-complexity` |
| **Backend (FastAPI)** | `Pytest` (Unit Coverage) | **`>= 95.0%` real coverage on `src/`** | `make -C backend qa-unit` |
| **Backend (FastAPI)** | `Alembic` + `PostgreSQL 17` | **0 orphan ORM models / clean upgrade** | `make -C backend qa-parity` |
| **Backend (FastAPI)** | `Karate Labs` / `Schemathesis` / `ZAP` | Zero contract failures or DAST alerts | `make -C backend qa-bdd` / `qa-contracts` / `qa-dast` |
| **Frontend (Vue 3)** | `vue-tsc --noEmit` + `ESLint` + `SonarJS` | **0 type errors / Low cognitive complexity** | `make -C frontend qa-lint` |
| **Frontend (Vue 3)** | `Vitest` (`@vitest/coverage-v8`) | **`>= 95.0%` lines, functions, branches, statements** | `make -C frontend qa-unit` |
| **Frontend (Vue 3)** | `Zero Orphans Gate` | **0 `.vue` files without `.unit.ts`** | `make -C frontend qa-orphans` |
| **Frontend (Vue 3)** | `Playwright` + `@axe-core/playwright` | **0 WCAG 2.1 A/AA violations** | `make -C frontend qa-e2e` |
| **Frontend (Vue 3)** | `Lighthouse CI` (`lhci autorun`) | **Perf/SEO/BP `>= 0.90` and Accessibility `>= 0.95`** | `make -C frontend qa-perf` |

---

## 3. Repository Hygiene & RAM Conservation

1. **Mandatory Post-QA Cleanup:**
   - After running coverage or mutation tests, execute `make clean-cache` when appropriate to purge temporary containers and networks.
2. **Concise Reporting:**
   - Summarize test counts, coverage percentages, and pass/fail status cleanly.
