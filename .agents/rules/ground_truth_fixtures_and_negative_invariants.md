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
| **Fixture A: Virgin / Ghost State** | Newly registered user (`es_activo=False`, `rol="FANTASMA"`) or month with zero receipts/rates. | **MUST assert negative:** `es_activo=False`, zero financial access, redirect to `/espera-aprobacion`. Any positive access is a critical test failure. |
| **Fixture B: Nominal Configured** | Active resident or board member (`es_activo=True`), exchange rate registered, open period. | **MUST assert positive:** `es_activo=True`, accurate USD/VES calculations, audit trail creation. |
| **Fixture C: Locked / Degraded State** | Closed accounting month (`bloqueado=True`, `estado="CERRADO"`) or missing daily rate. | **MUST assert graceful handling:** Explicit `409 Conflict` (Candado Contable) or `400/404` without unhandled `500` exceptions or state corruption. |

---

## 3. Negative Invariant Enforcement

1. **Assert What Should NOT Happen:**
   - Tests must assert that unapproved users (`FANTASMA`) or locked months (`CERRADO`) do NOT mutate balances, receipts, or expenses.
2. **Fail-Closed Rule:**
   - If a virgin/locked fixture allows a state mutation or returns a false positive, the test suite aborts with exit code 1.
