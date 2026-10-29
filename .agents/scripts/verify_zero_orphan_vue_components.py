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


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent.parent

    candidates = [
        repo_root / "frontend" / "src",
        repo_root / "vue3" / "src",
        repo_root / "src",
    ]
    frontend_src = None
    for candidate in candidates:
        if candidate.exists():
            frontend_src = candidate
            break

    if not frontend_src:
        print("ℹ️ No se detectó directorio de frontend (frontend/src o vue3/src); omitiendo verificación de huérfanos.")
        return 0

    ui_files: list[str] = []
    for root, _, files in os.walk(frontend_src):
        for file_name in files:
            if file_name.endswith(".vue") or (file_name.endswith(".tsx") and not file_name.endswith(".unit.tsx")):
                ui_files.append(os.path.join(root, file_name))

    if not ui_files:
        print("ℹ️ No se encontraron componentes UI (.vue / .tsx); verificación aprobada.")
        return 0

    unit_files: list[str] = []
    for root, _, files in os.walk(frontend_src):
        for file_name in files:
            if file_name.endswith((".unit.ts", ".unit.tsx", ".spec.ts", ".test.ts")):
                unit_files.append(os.path.join(root, file_name))

    orphans: list[str] = []
    for ui_file in sorted(ui_files):
        rel_path = os.path.relpath(ui_file, repo_root)
        base = os.path.basename(ui_file)
        name = os.path.splitext(base)[0]

        ext = os.path.splitext(ui_file)[1]
        direct_unit = ui_file.replace(ext, ".unit.ts")
        direct_unit_tsx = ui_file.replace(ext, ".unit.tsx")

        if os.path.exists(direct_unit) or os.path.exists(direct_unit_tsx):
            continue

        found = False
        for unit_f in unit_files:
            try:
                with open(unit_f, encoding="utf-8") as file:
                    content = file.read()
                    if base in content or f"'{name}'" in content or f'"{name}"' in content or f" {name} " in content:
                        found = True
                        break
            except OSError:
                continue

        if not found:
            orphans.append(rel_path)

    print(f"📊 Componentes UI auditados: {len(ui_files)}")
    print(f"📊 Suites de pruebas unitarias: {len(unit_files)}")

    if orphans:
        print(f"\n❌ Se detectaron {len(orphans)} componente(s) UI huérfano(s) sin pruebas unitarias:")
        for orphan in orphans:
            print(f"   - {orphan}")
        print("\nDirectiva Incumplida: Invariante de Cero Componentes UI Huérfanos (.agents/rules/mandatory_qa_pyramid_and_doc_sync.md)")
        return 1

    print("✔ Cero componentes UI huérfanos. 100% de componentes y vistas cuentan con pruebas unitarias.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
