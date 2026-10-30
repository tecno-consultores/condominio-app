# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors

# Mandatory Directive: QA 11X Pyramid & Continuous Documentation Sync

> **SUPREME CORPORATE GOVERNANCE DIRECTIVE:**
> Applies to all AI agents (Google Antigravity, Claude Code, Hermes Agent, Cursor) and human developers.
> **OUTPUT LANGUAGE CONSTRAINT:** Always communicate with the user, provide status updates, explain reasoning, and write commit messages / user-facing documentation in Spanish.

---

## 1. Supreme Directive: Mandatory 11X Test Creation

Any addition, modification, or bug fix in application source code (`backend/`, `frontend/`, or `scripts/`) **MUST strictly include** corresponding test suites across all applicable layers of the 11X quality pyramid:

1. **Backend Unit Layer (Pytest):**
   - Backend suites (`backend/tests/**/*.unit.py`) with **`>= 95.0%` branch and line coverage**.
   - Strict isolation: mock external I/O and network boundaries.
2. **Database & Migration Parity Layer:**
   - When modifying ORM models (`backend/src/models.py` or `backend/src/models/`), immediately generate and verify the Alembic migration (`backend/alembic/versions/`) against a real ephemeral PostgreSQL container (`make -C backend qa-parity`).
   - Zero tolerance for schema drift between code models and database tables (`.agents/scripts/verify_alembic_orm_parity.py`).
3. **Front-Back Contract Integration Layer:**
   - Validate live HTTP payloads, OpenAPI contracts (`make -C backend qa-contracts`), response shapes, and persistence against running ephemeral API and DB instances.
4. **Acceptance BDD Layer (Karate Labs):**
   - **ALWAYS** include or update BDD feature files in `backend/test/api_test.feature` (API contracts, status codes, headers, payload validation) and `frontend/test/ui_business_flow.feature` (end-to-end interactive UI flows).
   - Any new endpoint or UI view must have matching Karate scenarios.
5. **Zero-Orphan UI Component Invariant:**
   - Every single UI component or view (`.vue`, `.tsx`) in `frontend/src/` must have a dedicated `.unit.ts` test suite. Zero orphan components allowed (`.agents/scripts/verify_zero_orphan_vue_components.py`).
6. **Mutation Testing Resilience (Mutmut / Stryker):**
   - Tests must kill artificial logical mutations to prove test assertion rigor and eliminate false confidence.

---

## 2. Rule Zero: Ephemeral Docker Execution

**NEVER** execute tests, migrations, linters, or operational scripts directly on the host machine (`Ubuntu`, `macOS`, or `Windows`). All executions must occur inside the project's ephemeral Docker containers (`docker-compose.qa.yml` and `Makefile`). If `make` is not installed on the host shell, invoke `docker compose -f backend/docker-compose.qa.yml run --rm qa-backend ...` and `docker compose -f frontend/docker-compose.qa.yml run --rm qa-vue3 ...` directly.
- When starting `postgres:17-alpine` for `qa-parity`, always pass `--wait` (`docker compose -f backend/docker-compose.qa.yml up -d --wait postgres`) so PostgreSQL is ready before `alembic upgrade head`.
- In Vue 3 templates (`@vue/runtime-dom`), `<input type="number" v-model="...">` automatically coerces bound `ref` values to `number` on input events; always wrap with `String(val.value ?? '').trim()` before calling string methods.

---

## 3. Continuous Mandatory Documentation Sync

Following any code modification, the AI agent **MUST autonomously and continuously synchronize**:

1. **Affected Guides & Manuals in `docs/` & `docs/specs/`:**
   - Update operational manuals, domain specifications, and API/GUI route maps (`docs/API_ROUTES.md`, `docs/ARCHITECTURE.md`, `docs/specs/`).
2. **Change History in `CHANGELOG.md`:**
   - Record additions, modifications, and fixes under `## [Unreleased]`.
3. **Milestone Progress in `ROADMAP.md`:**
   - Update milestone and sub-task status in `ROADMAP.md`.
4. **Assurance Metrics in `TESTING.md`, `backend/TESTING.md` & `frontend/TESTING.md`:**
   - Record updated test counts, pass rates, and coverage percentages.
5. **Deterministic Checkpoint Log in `.agents/ACTIVE_TASK.md`:**
   - Update `.agents/ACTIVE_TASK.md` at the start, after each sub-task (`CP-X.Y`), and upon completion of every milestone.
6. **Project Root & Scripts (`README.md`, `SECURITY.md`, `scripts/limpieza.sh`):**
   - Update whenever architectural blueprints, tools, or dependencies evolve.

---

## 4. Pre-Conclusion Verification Gate

Before completing any task, execute:
```bash
./.agents/scripts/certify_task_completion.sh
```
All checks must pass with exit code 0.
