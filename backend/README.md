# ⚡ Backend FastAPI & Worker Asíncrono — Condominio App

**Componente:** `backend/`  
**Stack:** Python `3.13` · FastAPI · SQLAlchemy `2.0` Async · Alembic · PostgreSQL `17` (RLS) · KeyDB Multi-Hilo · MinIO S3 · Pillow `13` (AVIF)  
**Estándar:** Gobernanza y Calidad Nivel 11X (`Rule Zero` — 100% Docker Efímero)

---

## 1. Arquitectura e Invariantes Clave

- **Imagen Unificada Multi-Rol (`CONTAINER_ROLE=api|worker`):** Empaquetada mediante [`Dockerfile`](./Dockerfile) multi-stage no-root (`appuser`, UID/GID `10001`) con `uv sync --frozen --no-dev` y [`docker-entrypoint.sh`](./docker-entrypoint.sh) consciente de rol (`--healthcheck` HTTP `/health` o heartbeat físico `QA-HEALTH-01`).
- **Modelo Relacional y Migraciones (`27` tablas ORM):** Definidas en [`src/models.py`](./src/models.py) con paridad 1:1 validada contra [`alembic/versions/`](./alembic/versions/) (`0001` a `0010`) sobre PostgreSQL `17` real.
- **9 Routers REST (`src/routers/`):** `auth.py`, `administracion.py`, `finanzas.py`, `pagos.py`, `incidencias.py`, `operaciones.py`, `consultas.py`, `accesos.py` y `reservas.py`.
- **Single-Condo + PG17 RLS Real (`0010`):** Todas las tablas operan con `ENABLE` y `FORCE ROW LEVEL SECURITY` sobre `condominio_id`, conexión runtime bajo rol no-superusuario (`condominio_app_runtime` con `NOBYPASSRLS`), inyección fail-closed (`tenant_id = ""` por defecto), restricciones `UNIQUE` compuestas por `(condominio_id, ...)` y tablas WORM (`auditoria_recibos`, `votos_consulta`) sin permisos `UPDATE`/`DELETE`.
- **Complejidad Radon Grado A:** Gate estricto [`scripts/radon_gates.py`](./scripts/radon_gates.py) exigiendo complejidad ciclomática **Grado A (`CC <= 5`)** e Índice de Mantenibilidad **Grado A** en todo `src/`.
- **Criptografía, Sesión e Idempotencia en KeyDB:** Subclaves independientes vía `HKDF-SHA256`, hashing `PBKDF2-HMAC-SHA256` (`>= 600_000` iteraciones async), JWT en cookies `HttpOnly` + Bearer, validación estricta `X-CSRF-Token`, lockout atómico Lua, política fail-closed en producción, idempotencia aislada `idemp:{condominio_id}:{usuario_id}:{scope}:{key}` con *response replay* y nonces QR anti-replay.
- **Worker Asíncrono (`src/worker.py`, `src/worker_media.py`, `src/worker_scheduler.py`):** Colas confiables con `BLMOVE` y DLQ acotada, codificación AVIF con carga `AWS4-HMAC-SHA256` hacia MinIO, envío SMTP `STARTTLS` con sanitización CRLF y generación diaria idempotente de tareas de conserjería.
- **Bootstrap Idempotente Día 0 (`src/bootstrap.py`):** Inicialización segura desde entorno (`--from-env`) o flags sin exponer contraseñas en CLI, bloqueando la reactivación de cuentas revocadas administrativamente.

---

## 2. Estructura del Módulo

```text
backend/
├── src/
│   ├── routers/            # 9 routers REST (auth, administracion, finanzas, pagos, incidencias, operaciones, consultas, accesos, reservas)
│   ├── main.py             # Lifespan Fail-Fast, cabeceras OSHP, /health, /metrics y handlers de excepción
│   ├── database.py         # Motor async, pool PostgreSQL/SQLite, PRAGMA foreign_keys y SET LOCAL ROLE RLS
│   ├── dependencies.py     # Autenticación dual Cookie/Bearer, RBAC e inyección de tenant_id
│   ├── security.py         # HKDF-SHA256, PBKDF2, JWT, CSRF, Anti-SSRF DNS async, Magic Bytes y cuotas <= 2 MB
│   ├── redis_client.py     # Cliente KeyDB Fail-Closed, revocación por sid/usuario, nonces QR y lockout Lua
│   ├── redis_idempotency.py# Dependencia unificada de idempotencia con replay y liberación en 4xx/5xx
│   ├── finanzas.py         # Núcleo matemático Decimal (ROUND_HALF_UP), quórum y firmas HMAC-SHA256
│   ├── facturacion_lph.py  # Motor de alícuotas (Hamilton), cuota fija, saldo a favor y UPSERT de cargos
│   ├── worker*.py          # Orquestador QA-HEALTH-01, conversión AVIF/MinIO, SMTP y scheduler diario
│   └── bootstrap.py        # CLI idempotente Día 0 (--from-env)
├── alembic/versions/       # Migraciones reversibles 0001..0010 verificadas contra PG17 real
├── scripts/                # radon_gates.py (Grado A), mutmut_gates.py, find_worker.py
├── tests/                  # Suites unitarias e integración PG17 (test_*.unit.py, cobertura >= 95%)
├── test/                   # Escenarios BDD Gherkin en Karate Labs (api_test.feature)
├── Dockerfile              # Imagen productiva multi-stage Python 3.13 --no-dev no-root (UID 10001)
└── Makefile                # Orquestación efímera Docker QA 11X
```

---

## 3. Comandos QA Efímeros (`Rule Zero` — `backend/Makefile`)

Ejecute todos los gates dentro de contenedores efímeros sin instalar dependencias en el host:

```bash
make -C backend qa-lint         # Ruff + Mypy (--strict) + Bandit (SAST)
make -C backend qa-complexity   # Radon Grado A (CC <= 5, MI >= A)
make -C backend qa-deps         # Auditoría de CVEs en dependencias (uv audit)
make -C backend qa-unit         # Pruebas unitarias Pytest (cobertura >= 95%)
make -C backend qa-parity       # Paridad ORM <-> Alembic reversible (0001..0010) y RLS en PG17 real
make -C backend qa-bdd          # Escenarios BDD de caja negra (Karate Labs API)
make -C backend qa-mutation     # Pruebas de mutación AST multi-core (12 módulos, MSI >= 80%)
make -C backend qa-contracts    # Fuzzing de contratos OpenAPI (Schemathesis)
make -C backend qa-dast         # Seguridad dinámica (OWASP ZAP con zap.yaml no-root)
make -C backend qa-chaos        # Resiliencia y carga (Pumba + Locust + Prometheus)
make -C backend qa-profile      # Perfilado de CPU con sidecar py-spy bajo carga Locust
make -C backend qa-infra        # Auditoría Trivy IaC + FS sobre el repositorio
make -C backend qa-all          # Pipeline base (qa-lint + qa-complexity + qa-unit + qa-parity)
make -C backend clean-cache     # Apaga contenedores y limpia cachés QA efímeras
```

---

## 4. Documentación Relacionada

- **[`backend/TESTING.md`](./TESTING.md)** — Bitácora detallada de suites, cobertura y resultados del backend.
- **[`README.md`](../README.md)** — Presentación general del sistema y despliegue productivo Docker Hub.
- **[`docs/qa/README.md`](../docs/qa/README.md)** — Guía maestra de la pirámide QA Nivel 11X y arquitectura Thin-Repo.
- **[`SECURITY.md`](../SECURITY.md)** — Política de seguridad y catálogo de los **22 vectores** mitigados.
