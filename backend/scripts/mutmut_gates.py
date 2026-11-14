# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors
"""Gates de Nivel 11X para pruebas de mutación en backend con Mutmut 2.5.

Paraleliza mutantes AST de Mutmut por shards en múltiples procesos usando ``os.fork()``
y ``pytest.main(...)`` con dependencias pesadas precalentadas en aislamiento temporal.
"""

from __future__ import annotations

import importlib
import multiprocessing
import os
import shutil
import signal
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mutmut
import pytest

MSI_MINIMO = 80.0
TIMEOUT_MUTANTE_SEG = 30
_PREWARM_LIBS: tuple[str, ...] = (
    "pytest",
    "sqlalchemy",
    "aiosqlite",
    "pydantic",
    "fastapi",
    "starlette",
    "jwt",
)
_PYTEST_BASE_FLAGS: tuple[str, ...] = (
    "-x",
    "-q",
    "--import-mode=importlib",
    "--tb=no",
    "-p",
    "no:cov",
    "-p",
    "no:schemathesis",
    "-p",
    "no:locust",
    "-p",
    "no:hypothesis",
    "-o",
    "addopts=--import-mode=importlib --strict-markers",
    "-o",
    "pythonpath=",
)
TARGETS: tuple[tuple[str, tuple[str, ...], bool], ...] = (
    ("src/finanzas.py", ("tests/test_finanzas_core.unit.py",), True),
    ("src/facturacion_lph.py", ("tests/test_hito10_alicuotas_solvencia.unit.py",), False),
    ("src/security.py", ("tests/test_security_11x.unit.py",), False),
    ("src/bootstrap.py", ("tests/test_bootstrap_cli.unit.py",), True),
)


@dataclass(frozen=True)
class ResultadoMutacion:
    """Resumen cuantitativo de mutantes ejecutados para un módulo fuente."""

    modulo: str
    killed: int
    timeout: int
    survived: int
    supervivientes: tuple[tuple[int, str], ...] = ()

    @property
    def total(self) -> int:
        return self.killed + self.timeout + self.survived

    @property
    def msi(self) -> float:
        if self.total == 0:
            return 0.0
        return ((self.killed + self.timeout) / self.total) * 100.0


def _precalentar_dependencias() -> None:
    """Precarga bibliotecas externas pesadas en el worker antes de hacer fork()."""
    for mod_name in _PREWARM_LIBS:
        importlib.import_module(mod_name)


def _copiar_sandbox(origen: Path, destino: Path) -> None:
    """Copia src/, tests/ y pyproject.toml a un sandbox temporal limpio."""
    ignorar = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "mutants", "htmlcov")
    shutil.copytree(origen / "src", destino / "src", ignore=ignorar)
    shutil.copytree(origen / "tests", destino / "tests", ignore=ignorar)
    shutil.copy2(origen / "pyproject.toml", destino / "pyproject.toml")


def _ejecutar_pytest_fork(sandbox: Path, raiz_app: Path, flags: list[str]) -> str:
    """Evalúa la suite objetivo en un hijo fork() aislado con timeout estricto."""
    pid = os.fork()
    if pid == 0:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        os.close(devnull)
        os.chdir(sandbox)
        rutas_app = {"", str(raiz_app), "/app"}
        sys.path[:] = [str(sandbox)] + [p for p in sys.path if p not in rutas_app]
        for clave in [k for k in list(sys.modules) if k == "src" or k.startswith(("src.", "tests"))]:
            sys.modules.pop(clave, None)
        signal.alarm(TIMEOUT_MUTANTE_SEG)
        try:
            rc = int(pytest.main(flags))
        except SystemExit as exc:
            rc = int(exc.code or 0) if isinstance(exc.code, int) else 1
        except BaseException:
            rc = 1
        os._exit(0 if rc == 0 else 1)

    _, status = os.waitpid(pid, 0)
    if os.WIFSIGNALED(status):
        return "timeout"
    return "survived" if os.WEXITSTATUS(status) == 0 else "killed"


def _evaluar_shard(
    args: tuple[str, str, tuple[str, ...], bool, list[Any]],
) -> tuple[int, int, int, list[tuple[int, str]]]:
    """Ejecuta un subconjunto (shard) de mutaciones AST en su propio sandbox."""
    raiz_str, modulo, pruebas, noconftest, mids = args
    raiz = Path(raiz_str)
    orig = (raiz / modulo).read_text(encoding="utf-8")
    _precalentar_dependencias()

    killed = 0
    timeout = 0
    survived = 0
    supervivientes: list[tuple[int, str]] = []
    with tempfile.TemporaryDirectory(prefix="mutmut_gate_") as tmp_dir:
        sandbox = Path(tmp_dir)
        _copiar_sandbox(raiz, sandbox)
        flags = list(_PYTEST_BASE_FLAGS)
        if noconftest:
            flags.append("--noconftest")
        flags.extend(str(sandbox / p) for p in pruebas)

        estado_base = _ejecutar_pytest_fork(sandbox, raiz, flags)
        if estado_base != "survived":
            raise RuntimeError(f"La suite base falló sin mutaciones ({estado_base}) en {modulo}.")

        ruta_mod = sandbox / modulo
        for mid in mids:
            mut_src, _ = mutmut.mutate(mutmut.Context(source=orig, mutation_id=mid, filename=modulo))
            ruta_mod.write_text(mut_src, encoding="utf-8")
            estado = _ejecutar_pytest_fork(sandbox, raiz, flags)
            if estado == "killed":
                killed += 1
            elif estado == "timeout":
                timeout += 1
            else:
                survived += 1
                supervivientes.append((int(getattr(mid, "line_number", 0)), str(getattr(mid, "line", "")).strip()))
        ruta_mod.write_text(orig, encoding="utf-8")
    return killed, timeout, survived, supervivientes


def _ejecutar_target(raiz: Path, modulo: str, pruebas: tuple[str, ...], noconftest: bool) -> ResultadoMutacion:
    """Genera mutaciones AST de Mutmut para un módulo y las distribuye por shards."""
    orig = (raiz / modulo).read_text(encoding="utf-8")
    muts = list(mutmut.list_mutations(mutmut.Context(source=orig, filename=modulo)))
    if not muts:
        return ResultadoMutacion(modulo=modulo, killed=0, timeout=0, survived=0)

    n_workers = min(os.cpu_count() or 4, len(muts))
    shards = [muts[i::n_workers] for i in range(n_workers) if muts[i::n_workers]]
    tareas = [(str(raiz), modulo, pruebas, noconftest, shard) for shard in shards]

    killed_total = 0
    timeout_total = 0
    survived_total = 0
    supervivientes: list[tuple[int, str]] = []
    mp_ctx = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=len(tareas), mp_context=mp_ctx) as pool:
        for killed, timeout, survived, surv_shard in pool.map(_evaluar_shard, tareas):
            killed_total += killed
            timeout_total += timeout
            survived_total += survived
            supervivientes.extend(surv_shard)

    return ResultadoMutacion(
        modulo=modulo,
        killed=killed_total,
        timeout=timeout_total,
        survived=survived_total,
        supervivientes=tuple(sorted(supervivientes)),
    )


def main() -> int:
    """Orquesta todos los módulos críticos, imprime el MSI y valida el umbral >= 80%."""
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    os.environ.setdefault("COVERAGE_FILE", "/tmp/.coverage")
    raiz = Path(__file__).resolve().parent.parent
    resultados: list[ResultadoMutacion] = []

    for modulo, pruebas, noconftest in TARGETS:
        r = _ejecutar_target(raiz, modulo, pruebas, noconftest)
        resultados.append(r)
        print(
            f"[Mutmut] {r.modulo}: killed={r.killed}, timeout={r.timeout}, "
            f"survived={r.survived}, total={r.total}, MSI={r.msi:.2f}%",
            flush=True,
        )

    killed_total = sum(r.killed for r in resultados)
    timeout_total = sum(r.timeout for r in resultados)
    survived_total = sum(r.survived for r in resultados)
    total = killed_total + timeout_total + survived_total
    msi_total = ((killed_total + timeout_total) / total) * 100.0 if total > 0 else 0.0

    print(
        f"[Mutmut TOTAL] killed={killed_total}, timeout={timeout_total}, "
        f"survived={survived_total}, total={total}, MSI={msi_total:.2f}%",
        flush=True,
    )
    if total == 0 or msi_total < MSI_MINIMO:
        for r in resultados:
            if r.supervivientes:
                muestra = ", ".join(f"L{ln}" for ln, _ in r.supervivientes[:15])
                print(f"[Supervivientes {r.modulo}] {muestra}", file=sys.stderr)
        msg = f"🚫 MSI Backend ({msi_total:.2f}%) por debajo del mínimo requerido ({MSI_MINIMO:.1f}%)."
        print(msg, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
