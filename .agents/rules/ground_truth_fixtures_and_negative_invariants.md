# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors

# Mandatory Directive: Ground-Truth Fixtures & Negative Invariants Governance

> **CORE GOVERNANCE DIRECTIVE — ZERO MOCK BLINDNESS:**
> Applies to all AI agents and developers creating or testing integrations with external APIs, storage (MinIO), cache (KeyDB), or databases (PostgreSQL).
> **OUTPUT LANGUAGE CONSTRAINT:** Always communicate with the user and write final explanations in Spanish.

---

## 1. The Mock Blindness Anti-Pattern

Synthetic unit test mocks created ad-hoc invariably introduce **Mock Blindness**:
- The test writer models only the happy path based on idealized assumptions.
- Factory-default states (e.g. newly registered Ghost User without unit assignment, month without exchange rate registered, or closed accounting period) return empty lists or conflict states in real life.
- Synthetically passing tests give false confidence while the real frontend or client reports false positives or crashes in production.

---

## 2. Universal Trimodal Ground-Truth Fixture Matrix

For **EVERY** component, service, or integration, the test suite MUST include and validate against the following three states:

| Fixture Type | Description | Mandatory Assertion (Negative Invariant) |
| :--- | :--- | :--- |
| **Fixture A: Virgin / Ghost / Insolvent State** | Newly registered user (`es_activo=False`, `rol="FANTASMA"`), tenant without voting delegation (`puede_votar_asamblea=False`), or unit with pending debt (`saldo_pendiente > 0`). | **MUST assert negative:** `es_activo=False` blocked (`403`) on all financial/operational endpoints; un-delegated tenant blocked (`403`) from Carta Consulta voting; insolvent unit blocked (`403`/`409`) from Amenity Reservations and Solvency Certificates. |
| **Fixture B: Nominal Configured** | Active resident or board member (`es_activo=True`), exchange rate registered, open period, solvent unit (`deuda == 0.00`). | **MUST assert positive:** `es_activo=True`, penny-exact Hamilton aliquot prorating ($\sum \text{cuotas} == \text{total}$), valid `HMAC-SHA256` signatures on votes/solvency/QR passes, and audit trail creation. |
| **Fixture C: Locked / Replayed / Duplicate State** | Closed accounting month (`bloqueado=True`, `estado="CERRADO"`), replayed QR `jti` nonce, duplicate vote per unit, or reused bank reference `(metodo, numero_referencia)`. | **MUST assert graceful handling:** Explicit `409 Conflict` (Candado Contable, QR Replay, Duplicate Vote, Duplicate Bank Reference) without unhandled `500` exceptions or state corruption. |

---

## 3. Negative Invariant Enforcement

1. **Assert What Should NOT Happen:**
   - Tests must assert that unapproved users (`FANTASMA`) or locked months (`CERRADO`) do NOT mutate balances, receipts, or expenses.
2. **Fail-Closed Rule:**
   - If a virgin/locked fixture allows a state mutation or returns a false positive, the test suite aborts with exit code 1.

---

## 4. Parallel BDD Scenario Isolation & Multi-Connection SQLite (`Karate Labs`)

1. **Zero Inter-Scenario State Coupling (`threads = 5`):**
   - `ExamplesTest.java` executes Karate Labs scenarios in parallel across 5 threads (`Runner.path("classpath:examples").parallel(5)`).
   - Every scenario in `backend/test/api_test.feature` that requires an authenticated Ghost or Nominal user MUST register its own isolated fixture (`POST /api/auth/register` with a scenario-unique email, cedula, and `Idempotency-Key`) before calling `POST /api/auth/login`. Never depend on another scenario's execution order.
2. **Avoid `StaticPool` on Multi-Threaded Live API Containers:**
   - The `api` service in `backend/docker-compose.qa.yml` (exercised concurrently by Karate Labs, Schemathesis, ZAP, and Locust) MUST use a file-backed ephemeral SQLite URL (`sqlite+aiosqlite:////tmp/qa_api.db`) rather than `:memory:` (`StaticPool`), preventing concurrent `AsyncSession.close()` rollbacks on a single shared connection.
