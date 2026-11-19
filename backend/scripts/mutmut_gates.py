# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors
"""Gates de Nivel 11X para pruebas de mutación en backend con Mutmut 2.5.

Paraleliza mutantes AST de Mutmut por shards en un pool persistente de workers usando
``os.fork()`` y ``pytest.main(...)`` sobre un sandbox único por worker en ``/tmp``.
Evalúa los 12 módulos ejecutables de lógica/seguridad/worker en ``backend/src/`` y
verifica clasificación exhaustiva de todo módulo bajo ``src/``.
"""

from __future__ import annotations

import argparse
import atexit
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
    "httpx",
    "redis",
    "email_validator",
    "PIL",
    "prometheus_client",
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
)
TARGETS: tuple[tuple[str, tuple[str, ...], bool], ...] = (
    ("src/bootstrap.py", ("tests/test_bootstrap_cli.unit.py",), True),
    ("src/database.py", ("tests/test_database.unit.py",), True),
    ("src/dependencies.py", ("tests/test_dependencies.unit.py",), False),
    ("src/facturacion_lph.py", ("tests/test_facturacion_lph.unit.py",), True),
    ("src/finanzas.py", ("tests/test_finanzas_core.unit.py",), True),
    ("src/main.py", ("tests/test_main.unit.py",), False),
    ("src/redis_client.py", ("tests/test_redis_client.unit.py",), True),
    ("src/redis_idempotency.py", ("tests/test_redis_client.unit.py",), True),
    ("src/security.py", ("tests/test_security_11x.unit.py",), False),
    (
        "src/worker.py",
        ("tests/test_hito18_worker_prod.unit.py", "tests/test_hito21_contabilidad_idempotencia_worker.unit.py"),
        False,
    ),
    ("src/worker_media.py", ("tests/test_hito21_contabilidad_idempotencia_worker.unit.py",), False),
    ("src/worker_scheduler.py", ("tests/test_hito18_worker_prod.unit.py",), True),
)

# Catálogos declarativos ORM/Pydantic y adaptadores de transporte HTTP cubiertos por paridad PG17,
# cobertura unitaria >= 95%, Karate BDD (33 escenarios) y Schemathesis OpenAPI (simétrico a Stryker).
EXCLUDED_DECLARATIVE_AND_TRANSPORT: frozenset[str] = frozenset(
    {
        "src/models.py",
        "src/schemas.py",
        "src/routers/accesos.py",
        "src/routers/administracion.py",
        "src/routers/auth.py",
        "src/routers/consultas.py",
        "src/routers/finanzas.py",
        "src/routers/incidencias.py",
        "src/routers/operaciones.py",
        "src/routers/pagos.py",
        "src/routers/reservas.py",
    }
)

_WORKER_SANDBOX: Path | None = None
_WORKER_RAIZ: Path | None = None


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
        # QA 11X: timeouts no cuentan como mutantes matados.
        return (self.killed / self.total) * 100.0


def _precalentar_dependencias() -> None:
    """Precarga bibliotecas externas pesadas en el worker antes de hacer fork()."""
    for mod_name in _PREWARM_LIBS:
        importlib.import_module(mod_name)


def _copiar_sandbox(origen: Path, destino: Path) -> None:
    """Copia src/, tests/, scripts/ y pyproject.toml a un sandbox temporal limpio."""
    ignorar = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "mutants", "htmlcov")
    shutil.copytree(origen / "src", destino / "src", ignore=ignorar)
    shutil.copytree(origen / "tests", destino / "tests", ignore=ignorar)
    if (origen / "scripts").is_dir():
        shutil.copytree(origen / "scripts", destino / "scripts", ignore=ignorar)
    shutil.copy2(origen / "pyproject.toml", destino / "pyproject.toml")


def _limpiar_sandbox_worker() -> None:
    global _WORKER_SANDBOX
    if _WORKER_SANDBOX is not None:
        shutil.rmtree(_WORKER_SANDBOX, ignore_errors=True)
        _WORKER_SANDBOX = None


def _inicializar_worker_sandbox(raiz_str: str) -> None:
    """Inicializa una única vez por proceso worker las dependencias y su sandbox temporal."""
    global _WORKER_SANDBOX, _WORKER_RAIZ
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["REDIS_URL"] = "redis://127.0.0.1:1/15"
    _WORKER_RAIZ = Path(raiz_str)
    _precalentar_dependencias()
    sandbox = Path(tempfile.mkdtemp(prefix="mutmut_gate_"))
    _copiar_sandbox(_WORKER_RAIZ, sandbox)
    _WORKER_SANDBOX = sandbox
    atexit.register(_limpiar_sandbox_worker)


def _ejecutar_pytest_fork(
    sandbox: Path,
    raiz_app: Path,
    flags: list[str],
    timeout_seg: int = TIMEOUT_MUTANTE_SEG,
) -> str:
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
        importlib.invalidate_caches()
        importlib.import_module("tests")
        signal.alarm(timeout_seg)
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
    args: tuple[str, tuple[str, ...], bool, list[Any]],
) -> tuple[int, int, int, list[tuple[int, str]]]:
    """Ejecuta un subconjunto (shard) de mutaciones AST reutilizando el sandbox del worker."""
    modulo, pruebas, noconftest, mids = args
    if _WORKER_SANDBOX is None or _WORKER_RAIZ is None:
        raise RuntimeError("Worker sandbox no inicializado.")
    sandbox = _WORKER_SANDBOX
    raiz = _WORKER_RAIZ
    ruta_mod = sandbox / modulo
    orig = (raiz / modulo).read_text(encoding="utf-8")

    killed = 0
    timeout = 0
    survived = 0
    supervivientes: list[tuple[int, str]] = []
    flags = [*_PYTEST_BASE_FLAGS, "-o", f"pythonpath={sandbox}"]
    if noconftest:
        flags.append("--noconftest")
    flags.extend(str(sandbox / p) for p in pruebas)

    ruta_mod.write_text(orig, encoding="utf-8")
    try:
        estado_base = _ejecutar_pytest_fork(sandbox, raiz, flags, timeout_seg=max(TIMEOUT_MUTANTE_SEG * 2, 60))
        if estado_base != "survived":
            raise RuntimeError(f"La suite base falló sin mutaciones ({estado_base}) en {modulo}.")

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
    finally:
        ruta_mod.write_text(orig, encoding="utf-8")
    return killed, timeout, survived, supervivientes


def _ejecutar_target(
    pool: ProcessPoolExecutor,
    n_workers: int,
    raiz: Path,
    modulo: str,
    pruebas: tuple[str, ...],
    noconftest: bool,
) -> ResultadoMutacion:
    """Genera mutaciones AST de Mutmut para un módulo y las distribuye por shards."""
    orig = (raiz / modulo).read_text(encoding="utf-8")
    muts = list(mutmut.list_mutations(mutmut.Context(source=orig, filename=modulo)))
    if not muts:
        return ResultadoMutacion(modulo=modulo, killed=0, timeout=0, survived=0)

    n_shards = min(n_workers, len(muts))
    shards = [muts[i::n_shards] for i in range(n_shards) if muts[i::n_shards]]
    tareas = [(modulo, pruebas, noconftest, shard) for shard in shards]

    killed_total = 0
    timeout_total = 0
    survived_total = 0
    supervivientes: list[tuple[int, str]] = []
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


def _validar_mapeo_src(raiz: Path) -> None:
    """Verifica dinámicamente que todo módulo de src/ esté clasificado en TARGETS o exclusiones."""
    descubiertos = {
        str(p.relative_to(raiz)).replace(os.sep, "/")
        for p in sorted((raiz / "src").rglob("*.py"))
        if p.name != "__init__.py"
    }
    mapeados = {m for m, _, _ in TARGETS}
    faltantes = sorted(descubiertos - mapeados - EXCLUDED_DECLARATIVE_AND_TRANSPORT)
    if faltantes:
        raise RuntimeError(f"Módulos sin clasificación en mutmut_gates.py: {', '.join(faltantes)}")


def _seleccionar_targets(modulos_cli: list[str]) -> tuple[tuple[str, tuple[str, ...], bool], ...]:
    if not modulos_cli:
        return TARGETS
    solicitados = set(modulos_cli)
    conocidos = {m for m, _, _ in TARGETS}
    desconocidos = sorted(solicitados - conocidos)
    if desconocidos:
        raise RuntimeError(f"Módulo(s) desconocido(s) para --module: {', '.join(desconocidos)}")
    return tuple(t for t in TARGETS if t[0] in solicitados)


def main(argv: list[str] | None = None) -> int:
    """Orquesta módulos ejecutables de src/, imprime MSI real (killed/total) y valida >= 80%."""
    parser = argparse.ArgumentParser(description="Gates Mutmut QA 11X Backend")
    parser.add_argument(
        "--module",
        action="append",
        default=[],
        help="Ruta relativa de módulo en TARGETS para depuración selectiva (opcional).",
    )
    args = parser.parse_args(argv)

    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    os.environ.setdefault("COVERAGE_FILE", "/tmp/.coverage")
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["REDIS_URL"] = "redis://127.0.0.1:1/15"
    raiz = Path(__file__).resolve().parent.parent
    _validar_mapeo_src(raiz)
    seleccion = _seleccionar_targets(args.module)
    resultados: list[ResultadoMutacion] = []

    n_workers = min(os.cpu_count() or 4, 8)
    mp_ctx = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(
        max_workers=n_workers,
        mp_context=mp_ctx,
        initializer=_inicializar_worker_sandbox,
        initargs=(str(raiz),),
    ) as pool:
        for modulo, pruebas, noconftest in seleccion:
            r = _ejecutar_target(pool, n_workers, raiz, modulo, pruebas, noconftest)
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
    msi_total = (killed_total / total) * 100.0 if total > 0 else 0.0

    print(
        f"[Mutmut TOTAL] killed={killed_total}, timeout={timeout_total}, "
        f"survived={survived_total}, total={total}, MSI={msi_total:.2f}%",
        flush=True,
    )
    if total == 0 or msi_total < MSI_MINIMO:
        for r in resultados:
            if r.supervivientes:
                muestra = ", ".join(f"L{ln}:{txt[:40]}" for ln, txt in r.supervivientes[:15])
                print(f"[Supervivientes {r.modulo}] {muestra}", file=sys.stderr)
        msg = f"🚫 MSI Backend ({msi_total:.2f}%) por debajo del mínimo requerido ({MSI_MINIMO:.1f}%)."
        print(msg, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
