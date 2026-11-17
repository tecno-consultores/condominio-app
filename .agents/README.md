# `.agents/` — Thin-Repo Governance & QA 11X Gatekeepers (Condominio App)

Internal governance hub for AI coding assistants and maintainers under the **QA Level-11X Standard** (`@sinfallas/mcp-qa-11x` `v3.1.0`).

Canonical rules and corporate skills (`qa-11x-architect`, `qa-11x-devsecops-hardener`, `qa-11x-systematic-debugging`, `qa-11x-screenplay-builder`, `qa-11x-llm-evaluator`, `qa-11x-vibe-rescue`, `qa-11x-docker-certifier`, `docker-trivy-keydb-hardening`, `graphify-ast-navigator`, `refactoring-ui`, plus `tactical-patterns-11x`) are consumed directly from the global installation without local duplication.

## Directory Layout

```text
.agents/
├── .qa-11x-version                         # Synced blueprint/MCP version metadata (v3.1.0)
├── ACTIVE_TASK.md                          # Ephemeral session scratchpad (<= 40 lines, git-ignored)
├── ACTIVE_TASK.md.example                  # Deterministic <= 40-line checkpoint template
├── README.md                               # This architecture summary (concise technical English)
├── rules/
│   └── domain_condominio_app_rules.md      # Isolated Condominio App domain invariants
└── scripts/                                # Local Rule-Zero certification gates
    ├── certify_task_completion.sh          # 10-stage certification gate (ephemeral Docker)
    ├── inspect_blast_radius.py             # AST pre-change dependency & caller audit
    ├── validate_calm_architecture.sh       # FINOS CALM 1.2 + 7 mandatory QA-11X controls
    ├── verify_alembic_orm_parity.py        # SQLAlchemy ORM <-> Alembic & <= 32 char revision check
    ├── verify_docs_invariants.py           # Cognitive budgets (<= 40 lines) & doc invariants
    ├── verify_json_no_duplicate_keys.py    # Duplicate key scanner across JSON files
    ├── verify_no_orphan_api_endpoints.py   # Bidirectional FastAPI <-> Vue 3 API parity check
    ├── verify_roadmap_consistency.py       # ROADMAP.md <-> ACTIVE_TASK.md consistency validator
    ├── verify_topological_health.py        # Graphify AST layer boundary & anti-coupling check
    └── verify_zero_orphan_vue_components.py # 100% .vue -> .unit.ts coverage check
```

## Language Policy & Git Gate (`QA-GIT-GATE-01`)

- **Internal `.agents/**`:** Concise technical English for context-window token efficiency.
- **Human Docs & Chat:** Spanish across user interaction, commit messages, `README.md`, `CHANGELOG.md`, `ROADMAP.md`, `TESTING.md`, `SECURITY.md`, and `docs/**`.
- **`QA-GIT-GATE-01`:** Never execute `git push` automatically; complete work with a verified local `git commit`.

## Verification Commands (`Rule Zero`)

```bash
# Sync Thin-Repo skills/scripts from global @sinfallas/mcp-qa-11x
npx -y @sinfallas/mcp-qa-11x@latest install-skill --init-agents --include-scripts --reconcile

# Validate FINOS CALM 1.2 architecture & execute 10/10 gate in ephemeral Docker
./.agents/scripts/validate_calm_architecture.sh
./.agents/scripts/certify_task_completion.sh --strict
```
