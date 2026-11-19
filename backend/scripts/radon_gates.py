"""Gates de Nivel 11X sobre el análisis de Radon.

Bloquea la certificación si algún bloque supera la complejidad ciclomática de
grado A (CC <= 5) o si el Índice de Mantenibilidad cae por debajo del grado A.
"""

import json
import subprocess
import sys

GRADES = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}
MAX_GRADE = 1


def _grado(calificacion: str) -> int:
    return GRADES.get(calificacion.upper(), 6)


def main() -> int:
    fallos: list[str] = []

    radon_cc = json.loads(subprocess.check_output(["radon", "cc", "src/", "-s", "-nb", "--json"], text=True))
    for archivo, bloques in sorted(radon_cc.items()):
        for bloque in bloques:
            if _grado(bloque["rank"]) > MAX_GRADE:
                fallos.append(
                    f"COMPLEJIDAD {bloque['type']} {bloque['name']} ({archivo}):"
                    f" grado {bloque['rank']} (CC={bloque.get('complexity', '?')}) supera el máximo A (CC <= 5)"
                )

    radon_mi = json.loads(subprocess.check_output(["radon", "mi", "src/", "-s", "--json"], text=True))
    for archivo, modulo in sorted(radon_mi.items()):
        if _grado(modulo["rank"]) > MAX_GRADE:
            fallos.append(f"MI {archivo}: grado {modulo['rank']} supera el máximo A")

    if fallos:
        for fallo in fallos:
            print(f"🚫 {fallo}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
