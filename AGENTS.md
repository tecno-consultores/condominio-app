# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors

# 🤖 AI Agent Directives & Technical Governance — Condominio App (Standard 11X)

Welcome to the **Condominio App** repository. All AI coding assistants (Google Antigravity, Claude Code / Claude Desktop, Hermes Agent, Cursor, Windsurf, etc.) and human developers must strictly adhere to the Level-11X corporate quality, security, and testing directives defined here, in `.agents/rules/domain_condominio_app_rules.md`, and in the global QA 11X corporate skills (`@sinfallas/mcp-qa-11x`).

> **OUTPUT LANGUAGE CONSTRAINT:**
> Always interact with the user, provide status updates, explain reasoning, and write commit messages / user-facing documentation in Spanish.
>
> **TOKEN EFFICIENCY & LANGUAGE DESIGN:**
> Directives in `.agents/rules/` and global skills are maintained in concise, high-density technical English to optimize token utilization (~35% reduction in context window) and ensure maximum logical adherence across LLMs. All human-facing documentation (`docs/`, `docs/specs/`, `CHANGELOG.md`, `ROADMAP.md`, `README.md`, `TESTING.md`, `SECURITY.md`) remains strictly in Spanish. See [.agents/README.md](./.agents/README.md) for full architectural rationale.

---

## 1. Thin-Repo Governance & Domain Rules in `.agents/rules/`

Global canonical QA 11X rules and skills are consumed directly from the global `@sinfallas/mcp-qa-11x` installation without duplicating them locally. Project-specific governance is isolated in:

1. [domain_condominio_app_rules.md](./.agents/rules/domain_condominio_app_rules.md):
   - **Anti-Mock Blindness & Trimodal Fixtures:** Test against Virgin/Ghost (`es_activo=False`, `rol="FANTASMA"`), Nominal (`es_activo=True`), and Locked/Degraded (`bloqueado=True` Candado Contable) fixtures; ORM changes require versioned Alembic migrations verified against real PostgreSQL 17 (`make -C backend qa-parity`).
   - **Parallel BDD Scenario Isolation (`Karate Labs`):** Every scenario in `backend/test/api_test.feature` registers its own isolated fixture with dynamic UUIDs (`java.util.UUID.randomUUID() + ''`) and file-backed SQLite/PostgreSQL concurrency safety.
   - **Rule Zero & Vue 3 Invariants:** Never run linters, tests, migrations, or audits directly on the host OS; execute all checks inside ephemeral Docker containers (`Makefile`, `backend/docker-compose.qa.yml`, `frontend/docker-compose.qa.yml`). Wrap Vue `<input type="number" v-model>` reads safely with `String(val.value ?? '').trim()`.
   - **Continuous Mandatory Documentation & Checkpoint Sync:** Update affected files in `docs/`, `docs/specs/`, `CHANGELOG.md` (`## [Unreleased]`), `ROADMAP.md`, `TESTING.md`, `backend/TESTING.md`, `frontend/TESTING.md`, `.agents/ACTIVE_TASK.md`, `README.md`, and `SECURITY.md`.

---

## 2. Rule Zero: Ephemeral Docker Execution

**NEVER** execute tests, migrations, linters, or operational scripts directly on the host machine (`Ubuntu`, `macOS`, or `Windows`). All executions must occur inside ephemeral Docker containers (`Makefile`, `backend/docker-compose.qa.yml`, `frontend/docker-compose.qa.yml`).

---

## 3. Global Corporate Skills (`@sinfallas/mcp-qa-11x`)

Consumed globally (no local duplication in `.agents/skills/`):

1. `qa-11x-architect`: Master QA 11X & DevSecOps Architect (13 QA layers, DISA ASD STIG V6R5 & OWASP v4.2, 3-Path execution protocol).
2. `qa-11x-docker-certifier`: Ephemeral Docker QA certifier (`>= 95%` coverage, Radon/SonarJS, Karate Labs, mutation testing, zero host contamination).
3. `docker-trivy-keydb-hardening`: Container hardening (`Trivy HIGH/CRITICAL = 0`), multi-threaded KeyDB engine, and non-root runtime users.
4. `graphify-ast-navigator`: AST Knowledge Graph navigation (`graphify-out/graph.json`, `--code-only`), blast-radius pre-audit, and layer boundary compliance.
5. `refactoring-ui`: Visual hierarchy, `OKLCH` tokens, `light-dark()` theming, Anti-JSDOM geometry, and WCAG 2.1 AA compliance.

---

## 4. Automation Scripts in `.agents/scripts/` and `scripts/`

- `.agents/scripts/certify_task_completion.sh`: 10-stage closure certification gate (secrets, Trivy IaC/FS, JSON integrity, zero orphan UI components, zero orphan API endpoints, AST topology, ORM parity, roadmap consistency, docs invariants, and test/doc sync).
- `.agents/scripts/verify_alembic_orm_parity.py`: Parity validator between SQLAlchemy ORM models, Alembic migrations, and revision ID lengths (`<= 32`).
- `.agents/scripts/verify_zero_orphan_vue_components.py`: Ensures 100% of `.vue` views and components have active `.unit.ts` suites.
- `.agents/scripts/verify_no_orphan_api_endpoints.py`: Bidirectional front-back API parity validator.
- `.agents/scripts/verify_json_no_duplicate_keys.py`: Detects duplicate keys in JSON files.
- `.agents/scripts/inspect_blast_radius.py`: Computes incoming dependency edges from `graphify-out/graph.json`.
- `.agents/scripts/verify_topological_health.py`: AST architectural validator blocking forbidden cross-layer coupling.
- `.agents/scripts/verify_roadmap_consistency.py`: Validates bidirectional consistency across `ROADMAP.md` and `.agents/ACTIVE_TASK.md`.
- `.agents/scripts/verify_docs_invariants.py`: Enforces cognitive budgets (`<= 40` lines in `ACTIVE_TASK.md`) and documentation invariants.
- `scripts/actualizar-grafos-graphify.sh`, `scripts/auditar-infra.sh`, `scripts/verificar-secretos.sh`, `scripts/limpieza.sh`, `scripts/generar-sbom-cyclonedx.sh`.

---

## 5. Mandatory Task Closure Protocol

> **NON-NEGOTIABLE:** Following **EACH** task modifying source code, the AI agent **MUST** autonomously execute:
>
> 1. **Mandatory 11X Test Creation (ALWAYS Including Karate Labs):** Create or extend unit/integration tests (`>= 95%` coverage) and incorporate Karate Labs BDD scenarios in `backend/test/api_test.feature` (with dynamic UUID `Idempotency-Key`) and `frontend/test/ui_business_flow.feature`.
> 2. **Mandatory Test Execution & AST Graph Verification:** Execute suites inside ephemeral Docker (`Rule Zero` / `run_ephemeral_qa`), refresh `graphify-out/graph.json` (`./scripts/actualizar-grafos-graphify.sh`), and verify `0` topological violations.
> 3. **Mandatory Documentation & Checkpoint Sync:** Update affected files in `docs/`, `docs/specs/`, `CHANGELOG.md`, `ROADMAP.md`, `TESTING.md`, `backend/TESTING.md`, `frontend/TESTING.md`, `.agents/ACTIVE_TASK.md`, and `README.md`.
> 4. **Security & Gate 10/10 Closure:** Run `./scripts/verificar-secretos.sh`, `./scripts/auditar-infra.sh`, and `certify_11x_gate` / `./.agents/scripts/certify_task_completion.sh`.

---

<!-- QA_11X_MCP_CONNECTOR_START -->
## 🤖 Central QA 11X Skill & MCP Server Connector (`@sinfallas/mcp-qa-11x`)

> **OUTPUT LANGUAGE & HIGH-IQ TOKEN ECONOMY:** Interact and explain reasoning in the **user's prompt language**; write commit messages and human-facing docs matching the **existing language of `README.md` and `CHANGELOG.md`** (explicitly ignoring `AGENTS.md` and `.agents/**`, which remain in concise English for token economy; default to prompt language on empty repos). Apply *3-Tier Progressive Disclosure* (load global skill `references/*.md` and local `.agents/rules/domain_*.md` on-demand only), *Graphify AST-First & Windowed-Read-Second* (for ANY code/architecture Q&A or pre-change, query `graphify-out/graph.json` & `GRAPH_REPORT.md` via `inspect_ast_blast_radius` / `inspect_blast_radius.py` BEFORE `grep` or `read_file` with `StartLine`/`EndLine` 40–80 lines; never read full files `>150` lines blindly), *Zero Redundant Re-Read*, *Parallel Tool Batching*, and *Subagent Context Isolation* (`<=20` line summary return).

This project (`condominio-app`) enforces the **Level-11X Quality & DevSecOps Standard** (stacks: `fastapi, vue3, bash-scripts`).

1. **3-Path Proportional Execution (`DOCS_ONLY` vs. `MICRO_CHANGE` vs. `CODE_CHANGE` / `FULL_11X`):**
   - **`DOCS_ONLY` Fast-Path (ONLY `*.md` / `docs/` changed):** DO NOT run test suites (`run_ephemeral_qa`) and DO NOT rebuild AST graphs (`./scripts/actualizar-grafos-graphify.sh`). Only sync docs/`CHANGELOG.md`, run `certify_11x_gate`, and push to `git`.
   - **`MICRO_CHANGE` Surgical-Path (`<= 3` files, 0 new API/ORM changes, `LOW` AST Blast Radius `< 5` callers):** Use an inline 3-line plan, run `inspect_ast_blast_radius`, execute affected stack `run_ephemeral_qa` in Docker (**Rule Zero**), update stack AST graph, sync `CHANGELOG.md`, run `certify_11x_gate`, and `git push`.
   - **`CODE_CHANGE` (`FULL_11X`) Architectural-Path (`> 3` files, new API/UI, ORM migrations, security, or `MED`/`HIGH` Blast Radius):** Execute all 11 steps below inside ephemeral Docker (**Rule Zero** — never run `pytest`, `vitest`, `npm`, `pnpm`, `uv`, or linters on host OS).
2. **Global Corporate Skills & MCP Tools (`@sinfallas/mcp-qa-11x`):** Consume the 5 global skills (`qa-11x-architect`, `qa-11x-docker-certifier`, `docker-trivy-keydb-hardening`, `graphify-ast-navigator`, `refactoring-ui`) without duplicating them in local `.agents/skills/`. Use `inspect_project_config`, `audit_test_pyramid_gaps`, `inspect_ast_blast_radius`, `audit_security_stig_owasp`, `run_ephemeral_qa` (`skip_if_docs_only: true` supported), `certify_11x_gate`, `clean_workspace_11x`, `reconcile_agents_governance`, and `propose_skill_evolution_pr` (on QA-escape bug fixes, proactively include `💡 Oportunidad de Mejora Detectada para el Estándar QA 11X` and invoke `propose_skill_evolution_pr`).
3. **Mandatory 11-Step Execution & Closure Workflow (Non-Negotiable for Architectural Code Changes):**
   - **Step 1 (Plan):** Invoke `/plan` or plan artifact before modifying code.
   - **Step 2 (Active Task):** Track real-time progress (`- [ ]` -> `- [x]`) in `.agents/ACTIVE_TASK.md` (compact `<= 40 lines`).
   - **Step 3 (AST Graph Q&A & Pre-Change):** Query `inspect_ast_blast_radius` (`inspect_blast_radius.py`); if `graphify-out/graph.json` is missing, create it first via `./scripts/actualizar-grafos-graphify.sh`.
   - **Step 4 (Governance & Cleanup):** Sync `AGENTS.md`, `.agents/`, `scripts/limpieza.sh`, and `.gitignore`.
   - **Step 5 (11X Tests + Karate Labs):** Create unit (`>= 95%` coverage), integration, and **Karate Labs BDD (`.feature`)** tests.
   - **Step 6 (Full Suite Execution):** Run all suites in ephemeral Docker (`Rule Zero` / `run_ephemeral_qa`, 0 warnings).
   - **Step 7–9 (Docs, Changelog & Roadmap):** Sync `docs/specs/`, `README.md`, `TESTING.md`, `CHANGELOG.md`, and `ROADMAP.md`.
   - **Step 10 (Post-Change AST Graph):** Run `./scripts/actualizar-grafos-graphify.sh` (incremental per modified stack).
   - **Step 11 (Certify & Push):** Run `certify_11x_gate` and `clean_workspace_11x`, mark `.agents/ACTIVE_TASK.md` `COMPLETED (100%)` (suggest `/compact`), and `git push`.
<!-- QA_11X_MCP_CONNECTOR_END -->
