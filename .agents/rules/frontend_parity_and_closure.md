# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors

# Terminal ↔ Frontend Parity & Task Closure Protocol

> **CORE GOVERNANCE DIRECTIVE:**
> Applies to all AI agents and developers.
> **OUTPUT LANGUAGE CONSTRAINT:** Always communicate with the user and write final explanations in Spanish.

---

## 1. Terminal ↔ Frontend Parity Invariants

1. **Zero Console-Exclusive Actions:**
   - Any administrative, financial, or operational action supported by the backend MUST have an equivalent graphical interface in the Vue 3 frontend (`docs/API_ROUTES.md`).
2. **Zero Orphan API Endpoints:**
   - Every route defined in the FastAPI backend MUST be paired with a Vue 3 view or component enabling inspection, parameter configuration, and interactive execution.
3. **Zero Read-Only Operational Consoles:**
   - Operational management views (Treasury approvals, User assignment tray, Structure builder, Board roles, Janitor tasks) must offer tactical mutation actions (create, approve, reject with mandatory reason modal, toggle, complete) whenever the backend API supports mutations.
4. **Non-Destructive UI Error Handling:**
   - Pinia stores must never reset populated arrays or objects to empty primitives (e.g. `items.value = []`) inside generic `catch` blocks if valid data already exists in memory. Maintain the last known valid state and set an explicit `isStale` / `error` flag.
5. **UX/UI Residential Hospitality, Perceptual Tokens & Motion Architecture (`docs/specs/10_DISENO_UX_UI_AMIGABLE_TRANSICIONES_Y_SISTEMA_TOKENS.md`):**
   - Centralize visual tokens in `OKLCH` with `light-dark()` (`color-scheme: light dark`), using `color-mix(in oklab, ...)` for safe gamut tints, two-part elevation shadows, and top accent borders (`border-block-start: 4px`).
   - Never rely on color alone to convey status (`SOLVENTE`, `ABONO_PARCIAL`, `MOROSO`, `EN_REVISION`); always pair color badges with semantic icons/glyphs and maintain $\ge 3:1$ non-text contrast and `@media (forced-colors: active)` outlines.
   - Animate only compositor-friendly properties (`opacity`, `transform`) or top-layer discrete transitions (`@starting-style`, `transition-behavior: allow-discrete`, `overlay` with `data-closing` fallback for Firefox/Safari), SPA `document.startViewTransition`, and `interpolate-size: allow-keywords` / `calc-size(auto, size)` (with `block-size: auto` fallback), strictly honoring `@media (prefers-reduced-motion: reduce)` per rule (never global `0.01ms` resets).

---

## 2. Proactive Vulnerability Audit

Before exposing new endpoints or frontend views:
1. **Ghost User & RBAC Enforcement:** Ensure `FANTASMA` (`es_activo = False`) or unauthorized users cannot trigger protected actions in both Backend dependencies and Vue Router navigation guards.
2. **Automated SAST & Secret Checks:** Run static security audits (`bandit`, `ESLint Security`, `uv audit`, `pnpm audit`) in ephemeral Docker with 0 High/Critical findings.
3. **Anti-XSS & Anti-CSRF:** Never bind unescaped dynamic HTML (`v-html`) without strict sanitization (`escapeHtml` / `DOMPurify`).

---

## 3. Mandatory Task Closure Protocol

After **EVERY** task or turn that adds, edits, or removes code or configuration files, the AI agent **MUST** autonomously execute this protocol before concluding:

1. **Mandatory 11X Test Creation (Including Karate Labs for API & UI):**
   - Backend mutations: add/update unit tests (`backend/tests/**/*.unit.py`) AND mandatory BDD scenarios in Karate API (`backend/test/api_test.feature`).
   - Frontend mutations: add/update unit tests (`frontend/src/**/*.unit.ts`) AND mandatory BDD scenarios in Karate UI (`frontend/test/ui_business_flow.feature`).
2. **Full Ephemeral Docker Test Execution (`Rule Zero`):**
   - Backend: Run `make -C backend qa-lint qa-complexity qa-unit qa-parity`.
   - Frontend (once initialized): Run `make -C frontend qa-lint qa-orphans qa-unit`.
3. **Autonomous & Mandatory Multi-Layer Documentation Sync:**
   - Update affected operational manuals and specs in `docs/` and `docs/specs/`.
   - Update `CHANGELOG.md` under `## [Unreleased]`.
   - Update `ROADMAP.md` progress.
   - Update `TESTING.md` and `backend/TESTING.md` metrics and counts.
   - Update `README.md` when user-facing interfaces or architectures change.
4. **Secret, Dependency Vulnerability, JSON & Parity Certification:**
   - Run `./scripts/verificar-secretos.sh` (0 secret leaks).
   - Run `./auditar-infra.sh` (0 High/Critical findings).
   - Run `./.agents/scripts/certify_task_completion.sh` (all gates passed).
