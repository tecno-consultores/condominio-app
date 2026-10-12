"""Localiza el PID del worker de uvicorn dentro del contenedor.

El contenedor arranca `bash -c "... && uvicorn src.main:app --reload"`, por lo que
la cadena es: bash (PID 1) -> uvicorn reloader (mismo PID 1) -> worker (python
lanzado vía `multiprocessing.spawn_main`). py-spy se ancla al worker para capturar
los frames de carga reales.
"""

import os
import sys


def main() -> None:
    for pid in sorted(int(p) for p in os.listdir("/proc") if p.isdigit()):
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                cmd = f.read().replace(b"\x00", b" ")
            with open(f"/proc/{pid}/stat", encoding="utf-8") as f:
                ppid = f.read().split()[3]
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if ppid != "0" and b"spawn_main" in cmd:
            sys.stdout.write(str(pid))
            return
    sys.stdout.write("1")


if __name__ == "__main__":
    main()
