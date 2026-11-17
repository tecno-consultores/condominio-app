# Domain-Specific Governance Rules (condominio_app)

## 1. Anti-Mock Blindness & Trimodal Fixtures

Synthetic ad-hoc unit mocks introduce **Mock Blindness**:
- Tests must exercise Virgin/Ghost (`es_activo=False`, `rol="FANTASMA"`), Nominal (`es_activo=True`), and Locked/Degraded (`bloqueado=True` Candado Contable) states.
- Factory defaults (Ghost users without units, months without BCV exchange rate, closed accounting periods) must return deterministic empty/conflict states rather than mocked happy paths.
- ORM modifications require versioned Alembic migrations verified against live PostgreSQL 17 (`make -C backend qa-parity`).

---

## 2. Rule Zero: Ephemeral Docker Execution

**NEVER** execute tests, migrations, linters, or operational scripts directly on the host OS (`Ubuntu`, `macOS`, or `Windows`). All executions must occur inside ephemeral Docker containers (`Makefile`, `docker-compose.qa.yml`, `backend/docker-compose.qa.yml`, `frontend/docker-compose.qa.yml`).
- When starting `postgres:17-alpine` for `qa-parity`, always pass `--wait` so PostgreSQL is ready before `alembic upgrade head`.
- In Vue 3 templates (`@vue/runtime-dom`), `<input type="number" v-model="...">` coerces bound `ref` values to `number` on input events; wrap with `String(val.value ?? '').trim()` before string operations.

---

## 3. Continuous Mandatory Documentation & Checkpoint Sync

Following any code change, autonomously synchronize:
1. **Guides & Specs (`docs/`, `docs/specs/`):** Update operational manuals and route/architecture maps (`docs/API_ROUTES.md`, `docs/ARCHITECTURE.md`, `docs/specs/`).
2. **Changelog (`CHANGELOG.md`):** Record additions, changes, and fixes under `## [Unreleased]`.
3. **Milestones (`ROADMAP.md`):** Update milestone and sub-task status/percentages.
4. **Metrics (`TESTING.md`, `backend/TESTING.md`, `frontend/TESTING.md`):** Update counts, pass rates, and coverage (`>= 95%`).
5. **Active Scratchpad (`.agents/ACTIVE_TASK.md`):** Keep `<= 40` lines and update at every checkpoint.
6. **Root Files & Operational Scripts (`README.md`, `SECURITY.md`, `scripts/limpieza.sh`, `scripts/backup-diario.sh`, `scripts/generar-sbom-cyclonedx.sh`, `instalar-hooks.sh`):** Update whenever blueprints, dependencies, or operational workflows change.

---

## 4. Parallel BDD Scenario Isolation & Multi-Connection SQLite (`Karate Labs`)

1. **Zero Inter-Scenario State Coupling (`threads = 5`):**
   - `ExamplesTest.java` runs Karate scenarios across 5 threads (`Runner.path("classpath:examples").parallel(5)`).
   - Every scenario requiring an authenticated Ghost or Nominal user MUST register its own isolated fixture (`POST /api/auth/register` with scenario-unique email, cedula, and dynamic UUID `Idempotency-Key`) before `POST /api/auth/login`.
2. **Avoid `StaticPool` on Multi-Threaded Live API Containers:**
   - The `api` service in `backend/docker-compose.qa.yml` MUST use file-backed ephemeral SQLite (`sqlite+aiosqlite:////tmp/qa_api.db`) instead of `:memory:` (`StaticPool`), avoiding concurrent `AsyncSession.close()` rollbacks across shared connections.
