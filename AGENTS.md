# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)

# 🤖 AI Agent Directives & Technical Governance — Condominio App (Standard 11X)

Welcome to the **Condominio App** repository. All AI coding assistants and human developers must strictly adhere to the Level-11X corporate quality, security, and testing directives defined here, in `.agents/rules/domain_condominio_app_rules.md`, and in the global QA 11X corporate skills (`@sinfallas/mcp-qa-11x` `v3.1.0`).

> **OUTPUT LANGUAGE CONSTRAINT:**
> Always interact with the user, provide status updates, explain reasoning, and write commit messages / human-facing documentation in **Spanish**.
>
> **TOKEN EFFICIENCY & LANGUAGE DESIGN:**
> Directives in `.agents/` and global skills stay in concise technical English (~35% token reduction). Human-facing docs (`docs/`, `docs/specs/`, `CHANGELOG.md`, `ROADMAP.md`, `README.md`, `TESTING.md`, `SECURITY.md`) stay strictly in Spanish. See [.agents/README.md](./.agents/README.md).

---

## 1. Thin-Repo Governance & Domain Rules in `.agents/rules/`

Global canonical QA 11X rules and skills are consumed directly from `@sinfallas/mcp-qa-11x` without duplicating them locally. Project-specific governance is isolated in [domain_condominio_app_rules.md](./.agents/rules/domain_condominio_app_rules.md):
- **Anti-Mock Blindness & Trimodal Fixtures:** Test Virgin/Ghost, Nominal, and Locked/Degraded states; verify Alembic migrations against live PostgreSQL 17 (`make -C backend qa-parity`).
- **Parallel BDD Scenario Isolation (`Karate Labs`):** Every scenario registers its own isolated UUID fixture (`java.util.UUID.randomUUID() + ''`) against file-backed ephemeral SQLite/PostgreSQL.
- **Rule Zero & Vue 3 Invariants:** Execute all checks in ephemeral Docker containers; guard `<input type="number" v-model>` with `String(val.value ?? '').trim()`.
- **Continuous Mandatory Sync:** Sync `docs/`, `docs/specs/`, `CHANGELOG.md`, `ROADMAP.md`, `TESTING.md`, `.agents/ACTIVE_TASK.md`, `README.md`, and `SECURITY.md`.

---

## 2. Rule Zero: Ephemeral Docker Execution

**NEVER** execute tests, migrations, linters, or operational scripts directly on the host OS (`Ubuntu`, `macOS`, or `Windows`). Execute everything inside ephemeral Docker containers (`Makefile`, `docker-compose.qa.yml`, `backend/docker-compose.qa.yml`, `frontend/docker-compose.qa.yml`).

---

## 3. Global Corporate Skills (`@sinfallas/mcp-qa-11x` `v3.1.0`)

Consumed globally (zero local duplication in `.agents/skills/`):

1. `qa-11x-architect`: Master QA 11X & DevSecOps orchestrator (3-Path routing, 13 QA layers, `QA-GIT-GATE-01`).
2. `qa-11x-devsecops-hardener`: 22 DISA ASD STIG V6R5 & OWASP v4.2 controls, PG17 RLS (`QA-PG17-RLS`), Vault AES-256-GCM, WORM audit chains, `QA-HEALTH-01`, `SEC-CI-ACTION-REF`.
3. `qa-11x-systematic-debugging`: 4-phase deterministic root-cause debugging (`Reproduce -> Isolate -> Trace -> Verify`).
4. `qa-11x-screenplay-builder`: Proportional E2E Screenplay Pattern, Anti-JSDOM geometry, semantic locators, 3-phase temporal assertions.
5. `qa-11x-llm-evaluator`: Dual-mode offline contracts + DeepEval/Promptfoo OWASP LLM Top 10 evaluation.
6. `qa-11x-vibe-rescue`: 5-stage Vibe-to-Enterprise hardening (`VIBE-SEC-001..QA-005`).
7. `qa-11x-docker-certifier`: Ephemeral Docker QA certifier (`>= 95%` coverage, Radon/SonarJS, Karate Labs, `kcov >= 95%`, mutation testing).
8. `docker-trivy-keydb-hardening`: Container hardening (`Trivy HIGH/CRITICAL = 0`), non-root users, lockfile builds, KeyDB multi-thread.
9. `graphify-ast-navigator`: AST Knowledge Graph navigation (`graphify-out/graph.json`, `--code-only`) and pre-change blast radius.
10. `refactoring-ui`: Visual hierarchy, `OKLCH` tokens, `light-dark()` theming, WCAG 2.1/2.2 AA compliance.
11. `tactical-patterns-11x`: JIT complexity rescue (`CC <= 5`, `SonarJS <= 15`), Port/Adapter offline testing, atomic outbox/idempotency.

---

## 4. Automation Scripts in `.agents/scripts/` and `scripts/`

- `.agents/scripts/certify_task_completion.sh`: 10-stage closure gate running under `Rule Zero` (`sinfallas/base-python-uv:3.13`).
- `.agents/scripts/validate_calm_architecture.sh`: FINOS CALM `1.2` validator against `architecture/qa-11x.calm.json` (`7` mandatory controls).
- `.agents/scripts/verify_alembic_orm_parity.py`: SQLAlchemy ORM <-> Alembic parity & `<= 32` char revision IDs.
- `.agents/scripts/verify_zero_orphan_vue_components.py`: Ensures 100% of `.vue` files have `.unit.ts` suites.
- `.agents/scripts/verify_no_orphan_api_endpoints.py`: Bidirectional FastAPI <-> Vue 3 API parity validator.
- `.agents/scripts/verify_json_no_duplicate_keys.py`: Duplicate JSON key detector.
- `.agents/scripts/inspect_blast_radius.py`: Incoming dependency edges from `graphify-out/graph.json`.
- `.agents/scripts/verify_topological_health.py`: AST architectural layer-boundary validator.
- `.agents/scripts/verify_roadmap_consistency.py`: Bidirectional `ROADMAP.md` <-> `.agents/ACTIVE_TASK.md` validator.
- `.agents/scripts/verify_docs_invariants.py`: Cognitive budgets (`<= 40` lines in `ACTIVE_TASK.md`) & documentation invariants.
- `scripts/actualizar-grafos-graphify.sh`, `scripts/auditar-infra.sh`, `scripts/verificar-secretos.sh`, `scripts/limpieza.sh`, `scripts/generar-sbom-cyclonedx.sh`, `scripts/backup-diario.sh`, `instalar-hooks.sh`.

---

## 5. Mandatory Task Closure Protocol (`QA-GIT-GATE-01`)

> **NON-NEGOTIABLE:** Following **EACH** task modifying source code:
> 1. **11X Tests (Including Karate Labs / BATS `kcov >= 95%`):** Extend unit/integration (`>= 95%`), BATS, and Karate BDD scenarios (`backend/test/api_test.feature`, `frontend/test/ui_business_flow.feature`).
> 2. **Ephemeral Verification & AST Refresh:** Execute suites in ephemeral Docker (`Rule Zero`), rebuild AST graphs (`./scripts/actualizar-grafos-graphify.sh`), and verify `0` topological violations.
> 3. **Docs & Checkpoint Sync:** Update affected docs, `CHANGELOG.md`, `ROADMAP.md`, `TESTING.md`, `.agents/ACTIVE_TASK.md`, and `README.md`.
> 4. **Security & 10/10 Closure (Local Commit Only):** Run `./scripts/verificar-secretos.sh`, `./scripts/auditar-infra.sh`, `./.agents/scripts/validate_calm_architecture.sh`, and `certify_11x_gate` / `./.agents/scripts/certify_task_completion.sh --strict`. Create a local `git commit` and **STOP — NEVER execute `git push` automatically**.

---

<!-- QA_11X_MCP_CONNECTOR_START -->
## 🤖 Central QA 11X Skill & MCP Server Connector (`@sinfallas/mcp-qa-11x` `v3.1.0`)

> **OUTPUT LANGUAGE & TOKEN ECONOMY:** Interact and write commit messages / human docs in **Spanish** (matching `README.md` & `CHANGELOG.md`; `.agents/**` remains concise English). Apply *3-Tier Progressive Disclosure*, *Graphify AST-First & Windowed-Read-Second* (`StartLine`/`EndLine` 40–80 lines), *Zero Redundant Re-Read*, *Parallel Tool Batching*, and *Subagent Isolation*.

This project (`condominio-app`) enforces **Level-11X Quality & DevSecOps** (stacks: `fastapi, vue3, bash-scripts`).

1. **3-Path Execution & `QA-GIT-GATE-01` (Never Auto-`git push`):**
   - **`DOCS_ONLY` (`*.md` / `docs/**` only):** `0` Docker QA runs, `0` AST rebuilds -> sync docs/`CHANGELOG.md` -> `certify_11x_gate` -> local `git commit`.
   - **`MICRO_CHANGE` (`<= 3` files, `< 5` callers, `0` route/ORM changes):** 3-line plan -> `inspect_ast_blast_radius` -> affected stack `run_ephemeral_qa` (**Rule Zero**) -> AST refresh -> `CHANGELOG.md` -> `certify_11x_gate` -> local `git commit`.
   - **`FULL_11X` (`> 3` files, new API/UI, ORM, security, or `MED`/`HIGH` blast):** `/plan`, `.agents/ACTIVE_TASK.md` (`<= 40` lines), `inspect_ast_blast_radius`, full ephemeral Docker pyramid + `QA-TEST-SYNC-01`, `validate_calm_architecture.sh`, docs/roadmap sync, AST refresh, `certify_task_completion.sh --strict` (10/10), `clean_workspace_11x`, and local `git commit` (suggest `/compact`; wait for explicit human approval before `git push`).
2. **Global Skills & MCP Tools (`qa-11x`):** Consume the 10 global corporate skills + `tactical-patterns-11x` directly; leverage `inspect_project_config`, `inspect_ast_blast_radius`, `audit_security_stig_owasp`, `run_ephemeral_qa`, `validate_calm_architecture`, `certify_11x_gate`, `clean_workspace_11x`, `reconcile_agents_governance`, and `propose_skill_evolution_pr` (on QA-escape bug fixes).
<!-- QA_11X_MCP_CONNECTOR_END -->
