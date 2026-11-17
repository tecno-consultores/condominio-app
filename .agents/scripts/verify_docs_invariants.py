#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
"""Validador determinista de presupuesto cognitivo e invariantes documentales QA 11X (condominio-app)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

MAX_ACTIVE_TASK_LINES = 40

FORBIDDEN_DOC_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\b8 Resources\b|\b8 recursos\b|\b8 Recursos\b", "conteo obsoleto de 8 recursos MCP"),
    (r"1\.43\.0-jammy|karatelabs:1\.5\.0|base-python-uv:3\.15", "tag de imagen Docker obsoleto o inexistente"),
    (r"\buv pip audit\b", "subcomando inexistente 'uv pip audit' (usar 'uv audit' o 'pip-audit')"),
    (r"refactoring-ui/\{topic\}[^\n]*\(`01` a `09`\)", "ejemplo numérico inválido en refactoring-ui/{topic}"),
)

STATIC_DOC_TARGETS: tuple[str, ...] = (
    "README.md",
    "AGENTS.md",
    ".agents/README.md",
    "CHANGELOG.md",
    "ROADMAP.md",
    "TESTING.md",
    "backend/TESTING.md",
    "frontend/TESTING.md",
    "SECURITY.md",
    "AUTHORS.md",
)

FILE_SPECIFIC_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (
        "docs/MANUAL_ADMINISTRADOR_E_INSTALADOR.md",
        r"BOOTSTRAP_ADMIN_PASSWORD=\"SU_CONTRASENA",
        "placeholder sin prefijo CHANGE_ME en MANUAL_ADMINISTRADOR_E_INSTALADOR.md",
    ),
)


def _check_scratchpad_lines(root: Path, rel: str) -> list[str]:
    candidate = root / rel
    if not candidate.is_file():
        return []
    count = len(candidate.read_text(encoding="utf-8").splitlines())
    if count <= MAX_ACTIVE_TASK_LINES:
        return []
    return [f"{rel} excede el límite compacto ({count} > {MAX_ACTIVE_TASK_LINES} líneas)."]


def check_cognitive_budgets(root: Path) -> list[str]:
    """Verifica que .agents/ACTIVE_TASK.md y su plantilla respeten <= 40 líneas."""
    return [
        *_check_scratchpad_lines(root, ".agents/ACTIVE_TASK.md.example"),
        *_check_scratchpad_lines(root, ".agents/ACTIVE_TASK.md"),
    ]


def check_security_section_numbering(root: Path) -> list[str]:
    """Detecta numeración duplicada '### 4.X.' en SECURITY.md."""
    sec_md = root / "SECURITY.md"
    if not sec_md.is_file():
        return []
    seen: set[str] = set()
    duplicates: list[str] = []
    for line in sec_md.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^###\s+(4\.\d+)\.", line)
        if match:
            sec_id = match.group(1)
            if sec_id in seen:
                duplicates.append(f"SECURITY.md contiene sección duplicada '### {sec_id}.'")
            seen.add(sec_id)
    return duplicates


def _scan_file_patterns(rel_path: str, content: str) -> list[str]:
    errors = [
        f"{rel_path}: detectado {reason}."
        for pattern, reason in FORBIDDEN_DOC_PATTERNS
        if re.search(pattern, content)
    ]
    for target, pat, msg in FILE_SPECIFIC_PATTERNS:
        if rel_path == target and re.search(pat, content):
            errors.append(msg)
    return errors


def check_active_docs(root: Path) -> list[str]:
    """Valida invariantes en los documentos reales de Condominio App y docs/**/*.md."""
    errors: list[str] = []
    targets: list[Path] = [root / rel for rel in STATIC_DOC_TARGETS if (root / rel).is_file()]
    docs_dir = root / "docs"
    if docs_dir.is_dir():
        targets.extend(sorted(docs_dir.rglob("*.md")))

    seen: set[Path] = set()
    for full_path in targets:
        resolved = full_path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        rel_path = full_path.relative_to(root).as_posix()
        errors.extend(_scan_file_patterns(rel_path, full_path.read_text(encoding="utf-8")))
    return errors


def validate_repository_docs(root: Path) -> list[str]:
    """Ejecuta todas las validaciones documentales sobre el directorio raíz."""
    return [
        *check_cognitive_budgets(root),
        *check_security_section_numbering(root),
        *check_active_docs(root),
    ]


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    target_root = Path(args[0]).resolve() if args else Path.cwd().resolve()
    errors = validate_repository_docs(target_root)
    if errors:
        print("❌ [Docs Invariants] Se detectaron violaciones documentales o de presupuesto cognitivo:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("✔ [Docs Invariants] Presupuesto cognitivo (<= 40 líneas) e invariantes documentales verificados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
