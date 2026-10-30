# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors

# Mandatory Directive: Anti-Regression & Side-Effects Guardrail

> **SUPREME GOVERNANCE INVARIANT:**
> No code change or refactoring may degrade, break, or disable an existing, previously validated feature. Whenever modifying shared modules, network configurations, or state stores, all agents and developers must proactively enforce the anti-regression safeguards defined herein.
> **OUTPUT LANGUAGE CONSTRAINT:** Always communicate with the user and write final explanations in Spanish.

---

## 1. Pre-Modification Impact & Blast-Radius Analysis

Before altering any shared code, service definition, or configuration:
1. **Shared Configuration & Port Invariants (`docker-compose*.yml`):**
   - **Never delete or overwrite canonical protocol ports** when adding or exposing alternative ports.
   - Verify that base HTTP and database/cache bindings remain reachable.
2. **Graphify AST Blast-Radius Pre-Audit & Post-Update (CLI-First Invariant):**
   - Prior to modifying or refactoring any shared function, model, utility, or state store, and immediately after completing architectural changes, extract/update the AST graph in ephemeral Docker and run the canonical blast radius and topological inspectors via CLI:
     ```bash
     docker run --rm -v "${PWD}:/app" -w /app sinfallas/remote-graphify:latest sh -c "graphify extract . --code-only --force && chown -R $(id -u):$(id -g) /app/graphify-out"
     python3 .agents/scripts/verify_topological_health.py
     python3 .agents/scripts/inspect_blast_radius.py "<symbol_name>"
     ```
   - **CLI-First Execution Rule:** Shell-capable agents (Google Antigravity, local terminal agents) MUST execute the inspector and query tools directly via CLI. They MUST NOT spawn background Docker MCP containers or occupy port 8080, which are reserved exclusively for external non-shell clients (Claude Desktop, Hermes Agent).
   - For any symbol assessed as `MODERATE` or `HIGH/CRITICAL` risk, the agent's implementation plan must explicitly list all affected caller files and guarantee that their contracts and parameters remain intact.
3. **Deterministic Session Continuity (`.agents/ACTIVE_TASK.md`):**
   - Maintain `.agents/ACTIVE_TASK.md` (ignored by Git via `.gitignore`) with granular `CP-X.Y` checkpoints during multi-step tasks so that any interrupted session can resume deterministically from the exact checkpoint.

---

## 2. Strict Pre-Build Static Analysis (Zero Missing Imports)

1. **Mandatory Immediate Linting:**
   - Before executing builds, restarting containers, or concluding a turn, verify syntactic integrity in ephemeral Docker:
     - Backend: `make -C backend qa-lint`
     - Frontend: `make -C frontend qa-lint`
2. **Zero Runtime Exceptions:**
   - Missing imports or unhandled type mutations must be detected during static check, never discovered through runtime container failure or blank screens.

---

## 3. Frontend Anti-Degradation (No Destructive Catch)

1. **Preserve Valid Known State on Network Error:**
   - Stores must never reset populated arrays or objects to empty primitives (e.g. `setItems([])`) inside generic `catch` blocks if valid data already exists in memory.
   - Maintain the last known good state and set an explicit `isStale` / `lastErrorMessage` status flag to inform the user without destroying rendered views.
2. **Explicit User Feedback:**
   - Action buttons (such as `[Enviar Reporte]`, `[Aprobar]`, `[Rechazar]`, `[Me Sumo]`) must always report success, in-flight progress (`isSubmitting`), or failure feedback reactively.
