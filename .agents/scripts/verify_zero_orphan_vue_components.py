#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors

"""verify_zero_orphan_vue_components.py — Invariante de Cero Componentes UI Huérfanos.

Audita que cada archivo .vue (o componente de UI en frontend/src o vue3/src) posea su
correspondiente suite .unit.ts dedicada o esté directamente testeado en una suite unitaria activa.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _resolve_frontend_src(repo_root: Path) -> Path | None:
    candidates = [
        repo_root / "frontend" / "src",
        repo_root / "vue3" / "src",
        repo_root / "src",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _is_ui_component_file(file_name: str) -> bool:
    return file_name.endswith(".vue") or (
        file_name.endswith(".tsx") and not file_name.endswith(".unit.tsx")
    )


def _collect_frontend_files(frontend_src: Path) -> tuple[list[str], list[str]]:
    ui_files: list[str] = []
    unit_files: list[str] = []
    for root, _, files in os.walk(frontend_src):
        for file_name in files:
            full_path = os.path.join(root, file_name)
            if _is_ui_component_file(file_name):
                ui_files.append(full_path)
            elif file_name.endswith((".unit.ts", ".unit.tsx", ".spec.ts", ".test.ts")):
                unit_files.append(full_path)
    return ui_files, unit_files


def _is_referenced_in_unit_suites(ui_file: str, unit_files: list[str]) -> bool:
    base = os.path.basename(ui_file)
    name, ext = os.path.splitext(base)
    direct_unit = ui_file.replace(ext, ".unit.ts")
    direct_unit_tsx = ui_file.replace(ext, ".unit.tsx")

    if os.path.exists(direct_unit) or os.path.exists(direct_unit_tsx):
        return True

    tokens = (base, f"'{name}'", f'"{name}"', f" {name} ")
    for unit_f in unit_files:
        try:
            with open(unit_f, encoding="utf-8") as file:
                content = file.read()
            if any(token in content for token in tokens):
                return True
        except OSError:
            continue
    return False


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent.parent
    frontend_src = _resolve_frontend_src(repo_root)

    if not frontend_src:
        print(
            "ℹ️ No se detectó directorio de frontend (frontend/src o vue3/src); "
            "omitiendo verificación de huérfanos."
        )
        return 0

    ui_files, unit_files = _collect_frontend_files(frontend_src)
    if not ui_files:
        print("ℹ️ No se encontraron componentes UI (.vue / .tsx); verificación aprobada.")
        return 0

    orphans = [
        os.path.relpath(ui_file, repo_root)
        for ui_file in sorted(ui_files)
        if not _is_referenced_in_unit_suites(ui_file, unit_files)
    ]

    print(f"📊 Componentes UI auditados: {len(ui_files)}")
    print(f"📊 Suites de pruebas unitarias: {len(unit_files)}")

    if orphans:
        print(f"\n❌ Se detectaron {len(orphans)} componente(s) UI huérfano(s) sin pruebas unitarias:")
        for orphan in orphans:
            print(f"   - {orphan}")
        print(
            "\nDirectiva Incumplida: Invariante de Cero Componentes UI Huérfanos "
            "(.agents/rules/mandatory_qa_pyramid_and_doc_sync.md)"
        )
        return 1

    print("✔ Cero componentes UI huérfanos. 100% de componentes y vistas cuentan con pruebas unitarias.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
