"""Localiza el PID del proceso Python real (worker de uvicorn/worker) dentro del contenedor.

Soporta tanto arranque con `--reload` (`multiprocessing.spawn_main`) como arranque
directo en producción/QA (`uvicorn src.main:app` o `python -m src.worker`) sin caer
falsamente en PID 1 (`/bin/bash` o el wrapper Rust `uv`).
"""

import os
import sys
from pathlib import Path


def _parse_ppid_from_stat(stat_text: str) -> str | None:
    rparen = stat_text.rfind(")")
    if rparen == -1:
        return None
    fields = stat_text[rparen + 2 :].split()
    return fields[1] if len(fields) > 1 else None


def _is_python_process(pid: int, argv0: str) -> bool:
    base0 = Path(argv0).name.lower() if argv0 else ""
    if base0.startswith("python"):
        return True
    try:
        exe = os.readlink(f"/proc/{pid}/exe")
    except OSError:
        return False
    return Path(exe).name.lower().startswith("python")


def _classify_proc_pid(proc_root: str, pid: int) -> tuple[bool, bool]:
    try:
        with open(f"{proc_root}/{pid}/cmdline", "rb") as f:
            raw_args = f.read().split(b"\x00")
        with open(f"{proc_root}/{pid}/stat", encoding="utf-8") as f:
            ppid = _parse_ppid_from_stat(f.read())
    except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
        return False, False
    if ppid is None or ppid == "0":
        return False, False
    argv = [arg.decode("utf-8", errors="ignore") for arg in raw_args if arg]
    cmd_str = " ".join(argv)
    if "find_worker.py" in cmd_str or not _is_python_process(pid, argv[0] if argv else ""):
        return False, False
    return "spawn_main" in cmd_str, any(tok in cmd_str for tok in ("uvicorn", "src.main", "src.worker"))


def find_target_python_pid(proc_root: str = "/proc") -> int | None:
    """Retorna el PID del worker Python (`spawn_main`) o proceso Python uvicorn/worker activo."""
    self_pid = os.getpid()
    fallback_pid: int | None = None
    for pid in sorted(int(p) for p in os.listdir(proc_root) if p.isdigit()):
        if pid == self_pid:
            continue
        is_spawn, is_worker = _classify_proc_pid(proc_root, pid)
        if is_spawn:
            return pid
        if fallback_pid is None and is_worker:
            fallback_pid = pid
    return fallback_pid


def main() -> int:
    pid = find_target_python_pid()
    if pid is None:
        sys.stderr.write("No se encontró proceso Python uvicorn/worker activo.\n")
        return 1
    sys.stdout.write(str(pid))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
