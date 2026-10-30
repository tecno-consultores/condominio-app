---
name: graphify-ast-navigator
description: >-
  AST Knowledge Graph navigation, pre-refactoring blast-radius audit, layer boundary compliance,
  and CLI-first query protocol for shell-capable AI agents.
---

# Graphify AST Navigator & Blast Radius Skill

This skill guides the use of AST (Abstract Syntax Tree) knowledge graphs to prevent regressions, circular dependencies, and unexpected side effects.
> **OUTPUT LANGUAGE CONSTRAINT:** Always communicate with the user and write final explanations in Spanish.

---

## 1. CLI-First Execution Rule

- Shell-capable AI agents (Google Antigravity, local CLI agents) MUST query and inspect AST graphs directly using CLI scripts:
  ```bash
  # Pre-refactoring blast radius inspection
  python3 .agents/scripts/inspect_blast_radius.py "<symbol_or_filename>"

  # Topological layer boundaries audit
  python3 .agents/scripts/verify_topological_health.py
  ```
- **Do not** spawn unnecessary background MCP servers or occupy port 8080 when running in environments where shell tools are directly available.

---

## 2. Blast Radius Assessment Matrix

When modifying a symbol or file:
1. **Low Risk:** `< 5` direct callers across `< 3` files. Proceed with local unit tests.
2. **Moderate Risk:** `5-14` callers across `3-7` files. Verify callers' contracts and re-run all caller unit tests.
3. **High / Critical Risk:** `>= 15` callers, `>= 8` files, or security-sensitive keywords (`auth`, `token`, `security`, `csrf`, `secret`, `session`, `finanzas`, `pagos`). Requires full regression test suite execution across the entire pyramid before merging.

---

## 3. Deterministic AST Graph Regeneration (`sinfallas/remote-graphify:latest`)

To regenerate `graphify-out/graph.json` and `graphify-out/GRAPH_REPORT.md` including all Python, TypeScript, and Vue 3 (`.vue`) files while excluding build/cache directories and restoring host ownership:

```bash
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace sinfallas/remote-graphify:latest -c '$(head -n1 $(which graphify) | cut -c3-) -c "import pathlib; from graphify.detect import detect; from graphify.extract import collect_files, extract; from graphify.build import build_from_json; from graphify.cluster import cluster, score_all; from graphify.analyze import god_nodes, surprising_connections, suggest_questions; from graphify.report import generate; from graphify.export import to_json; root = pathlib.Path(\".\"); det = detect(root); files = [f for f in collect_files(root) if not any(p in f.parts for p in (\".venv\", \"node_modules\", \"dist\", \"coverage\", \"target\", \"htmlcov\", \".git\"))]; ext = extract(files); G = build_from_json(ext); comms = cluster(G); coh = score_all(G, comms); gods = god_nodes(G); surp = surprising_connections(G, comms); qs = suggest_questions(G, comms, {}); out = root / \"graphify-out\"; out.mkdir(exist_ok=True); (out / \"graph.json\").unlink(missing_ok=True); to_json(G, comms, out / \"graph.json\"); rep = generate(G, comms, coh, {}, gods, surp, det, {\"input\": 0, \"output\": 0}, \".\", suggested_questions=qs); (out / \"GRAPH_REPORT.md\").write_text(rep)" && chown -R '"$(id -u):$(id -g)"' /workspace/graphify-out'
python3 .agents/scripts/verify_topological_health.py
```
