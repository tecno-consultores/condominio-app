# Domain-Specific Governance Rules (condominio_app)

## 1. The Mock Blindness Anti-Pattern

Synthetic unit test mocks created ad-hoc invariably introduce **Mock Blindness**:
- The test writer models only the happy path based on idealized assumptions.
- Factory-default states (e.g. newly registered Ghost User without unit assignment, month without exchange rate registered, or closed accounting period) return empty lists or conflict states in real life.
- Synthetically passing tests give false confidence while the real frontend or client reports false positives or crashes in production.

---


## 4. Parallel BDD Scenario Isolation & Multi-Connection SQLite (`Karate Labs`)

1. **Zero Inter-Scenario State Coupling (`threads = 5`):**
   - `ExamplesTest.java` executes Karate Labs scenarios in parallel across 5 threads (`Runner.path("classpath:examples").parallel(5)`).
   - Every scenario in `backend/test/api_test.feature` that requires an authenticated Ghost or Nominal user MUST register its own isolated fixture (`POST /api/auth/register` with a scenario-unique email, cedula, and `Idempotency-Key`) before calling `POST /api/auth/login`. Never depend on another scenario's execution order.
2. **Avoid `StaticPool` on Multi-Threaded Live API Containers:**
   - The `api` service in `backend/docker-compose.qa.yml` (exercised concurrently by Karate Labs, Schemathesis, ZAP, and Locust) MUST use a file-backed ephemeral SQLite URL (`sqlite+aiosqlite:////tmp/qa_api.db`) rather than `:memory:` (`StaticPool`), preventing concurrent `AsyncSession.close()` rollbacks on a single shared connection.


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

