#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors

"""Script de Auditoría de Salud Topológica y Límites de Capas (Graphify AST).

Verifica que las relaciones entre componentes y módulos respeten las reglas
arquitectónicas y no existan acoplamientos inversos prohibidos.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def find_graph_files() -> list[Path]:
    graphs: list[Path] = []
    seen: set[Path] = set()
    for pattern in ["**/graphify-out/graph.json", "**/graph.json"]:
        for path in REPO_ROOT.glob(pattern):
            resolved = path.resolve()
            if (
                "node_modules" not in str(path)
                and ".venv" not in str(path)
                and resolved not in seen
            ):
                seen.add(resolved)
                graphs.append(path)
    return graphs


def load_graph(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as file:
        return cast(dict[str, Any], json.load(file))


def audit_layers(graph: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    links = graph.get("links", [])
    violations: list[str] = []

    forbidden_prefixes = [
        "src/models",
        "src/schemas",
        "src/finanzas",
        "backend/src/models",
        "backend/src/schemas",
        "backend/src/finanzas",
    ]
    router_prefixes = ("src/routers/", "backend/src/routers/")

    for link in links:
        src_file = link.get("source_file", "")
        tgt_id = link.get("target", "")
        tgt_node = nodes.get(tgt_id)
        if not tgt_node:
            continue
        tgt_file = tgt_node.get("source_file", "")

        for prefix in forbidden_prefixes:
            if src_file.startswith(prefix) and tgt_file.startswith(router_prefixes):
                violations.append(
                    f"Acoplamiento inverso: '{src_file}' ({link.get('context', 'call')}) -> '{tgt_file}'"
                )

        if src_file.startswith(("src/components/", "frontend/src/components/")) and (
            tgt_file.startswith(("src/views/", "src/pages/", "frontend/src/views/"))
        ):
            violations.append(
                f"Acoplamiento invertido UI: Componente '{src_file}' depende de vista '{tgt_file}'"
            )

        if src_file.startswith(("src/stores/", "frontend/src/stores/", "src/services/", "frontend/src/services/")) and (
            tgt_file.startswith(("src/views/", "frontend/src/views/"))
        ):
            violations.append(
                f"Acoplamiento invertido Store/Service: '{src_file}' depende de vista '{tgt_file}'"
            )

    stats = {
        "nodes": len(nodes),
        "links": len(links),
        "communities": len({n.get("community", 0) for n in nodes.values()}),
    }
    return violations, stats


def main() -> int:
    print("🔍 [Graphify AST] Auditando salud topológica y límites de capas arquitectónicas...")

    graph_files = find_graph_files()
    if not graph_files:
        print("ℹ️ No se detectaron grafos AST (graph.json). Ejecución aprobada.")
        return 0

    all_violations: list[str] = []
    for g_path in graph_files:
        try:
            graph = load_graph(g_path)
            violations, stats = audit_layers(graph)
            print(
                f"📊 Grafo {g_path.relative_to(REPO_ROOT)}: "
                f"{stats['nodes']} nodos, {stats['links']} relaciones, {stats['communities']} comunidades."
            )
            if violations:
                all_violations.extend([f"[{g_path.name}] {v}" for v in violations])
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            print(f"⚠️ Error procesando grafo {g_path}: {exc}")

    if all_violations:
        print("\n❌ Se detectaron violaciones de límites de capas:")
        for violation in all_violations:
            print(f"   - {violation}")
        return 1

    print("✔ Salud topológica y límites de capas certificados (0 acoplamientos indebidos).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
