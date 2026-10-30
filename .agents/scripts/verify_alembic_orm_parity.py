#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors

"""Script de auditoría para prevenir modelos ORM huérfanos sin migración de base de datos.

Inspecciona modelos SQLAlchemy en backend/src/models.py (o backend/src/models/*.py) y valida
que todas las tablas declaradas con __tablename__ existan en los archivos de migración
de Alembic (backend/alembic/versions/*.py).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

if (REPO_ROOT / "backend").exists():
    BACKEND_DIR = REPO_ROOT / "backend"
elif (REPO_ROOT / "fastapi").exists():
    BACKEND_DIR = REPO_ROOT / "fastapi"
elif Path("/app/src").exists():
    BACKEND_DIR = Path("/app")
else:
    BACKEND_DIR = REPO_ROOT


def _resolve_migrations_dir() -> Path | None:
    candidates = [
        BACKEND_DIR / "alembic" / "versions",
        BACKEND_DIR / "migrations" / "versions",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _resolve_model_files() -> list[Path]:
    files: list[Path] = []
    single_file = BACKEND_DIR / "src" / "models.py"
    models_dir = BACKEND_DIR / "src" / "models"
    if single_file.exists():
        files.append(single_file)
    if models_dir.exists() and models_dir.is_dir():
        for py_file in models_dir.glob("*.py"):
            if py_file.name not in ("__init__.py", "base.py"):
                files.append(py_file)
    return files


def get_orm_tables() -> set[str]:
    """Extrae nombres de tablas a partir de __tablename__ en los modelos ORM."""
    tables: set[str] = set()
    table_pattern = re.compile(r'__tablename__\s*=\s*["\']([^"\']+)["\']')
    for py_file in _resolve_model_files():
        content = py_file.read_text(encoding="utf-8")
        for match in table_pattern.finditer(content):
            tables.add(match.group(1))
    return tables


def get_migrated_tables() -> set[str]:
    """Extrae nombres de tablas creadas o renombradas en las migraciones de Alembic."""
    migrated: set[str] = set()
    migrations_dir = _resolve_migrations_dir()
    if not migrations_dir:
        return migrated

    create_pattern = re.compile(r'op\.create_table\(\s*["\']([^"\']+)["\']')
    rename_pattern = re.compile(r'op\.rename_table\(\s*["\'][^"\']+["\']\s*,\s*["\']([^"\']+)["\']\)')

    for mig_file in migrations_dir.glob("*.py"):
        content = mig_file.read_text(encoding="utf-8")
        for match in create_pattern.finditer(content):
            migrated.add(match.group(1))
        for match in rename_pattern.finditer(content):
            migrated.add(match.group(1))
    return migrated


def validate_revision_id_lengths() -> list[tuple[str, str]]:
    """Verifica que ningún revision ID de Alembic supere los 32 caracteres (límite VARCHAR(32) en PostgreSQL)."""
    invalid: list[tuple[str, str]] = []
    migrations_dir = _resolve_migrations_dir()
    if not migrations_dir:
        return invalid
    rev_pattern = re.compile(r'^\s*revision(?:\s*:\s*[^=]+)?\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
    for mig_file in sorted(migrations_dir.glob("*.py")):
        content = mig_file.read_text(encoding="utf-8")
        match = rev_pattern.search(content)
        if match and len(match.group(1)) > 32:
            invalid.append((mig_file.name, match.group(1)))
    return invalid


def main() -> int:
    print("🔍 [QA 11X] Verificando paridad entre modelos SQLAlchemy ORM y migraciones Alembic...")

    invalid_revs = validate_revision_id_lengths()
    if invalid_revs:
        print("\n❌ ERROR: Revision IDs de Alembic superan el límite de 32 caracteres de PostgreSQL:")
        for fname, rev in invalid_revs:
            print(f"   - {fname}: '{rev}' ({len(rev)} chars > 32)")
        return 1

    model_files = _resolve_model_files()
    if not model_files:
        print("ℹ️ Archivos de modelos no encontrados; omitiendo verificación de paridad ORM.")
        return 0

    orm_tables = get_orm_tables()
    if not orm_tables:
        print("ℹ️ No se detectaron modelos con __tablename__; omitiendo verificación.")
        return 0

    migrated_tables = get_migrated_tables()
    missing = orm_tables - migrated_tables

    if missing:
        print("\n❌ ERROR: Se detectaron modelos ORM huérfanos sin migración de Alembic:")
        for table in sorted(missing):
            print(f"   - Tabla: '{table}' definida en ORM pero NO creada en migraciones.")
        print("\n💡 Solución: Genera la migración en backend/alembic/versions/ (ej. alembic revision -m 'add_<tabla>')")
        return 1

    tables_str = ", ".join(sorted(orm_tables))
    print(f"✅ ÉXITO: Las {len(orm_tables)} tablas ORM ({tables_str}) cuentan con su migración Alembic.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
