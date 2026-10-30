# 🧪 Bitácora General de Calidad y Certificación 11X (TESTING.md)

**Proyecto:** Condominio App  
**Estándar:** Gobernanza y Calidad Corporativa Nivel 11X (`Rule Zero` — 100% Docker Efímero)  
**Bitácora Detallada del Backend:** [`backend/TESTING.md`](./backend/TESTING.md)

---

## 1. Resumen Ejecutivo de Métricas QA 11X

| Capa de la Pirámide 11X | Herramienta / Gate | Umbral Exigido | Estado Actual |
| :--- | :--- | :--- | :--- |
| **Secret Scanning** | `./scripts/verificar-secretos.sh` | 0 secretos expuestos | ✅ **0 hallazgos** |
| **Lint, Tipado & SAST (Backend)** | `make -C backend qa-lint` (`ruff`, `mypy --strict`, `bandit`) | 0 errores / 0 advertencias | ✅ **100% Limpio** |
| **Complejidad Ciclomática & MI** | `make -C backend qa-complexity` (`radon_gates.py`) | CC $\le$ Grado B, MI $\ge$ Grado B | ✅ **Grado A en todos los módulos** |
| **Auditoría de Dependencias** | `make -C backend qa-deps` (`uv audit`) | 0 CVEs conocidos | ✅ **0 vulnerabilidades** |
| **Pruebas Unitarias Backend** | `make -C backend qa-unit` (`pytest` + `coverage`) | Cobertura $\ge 95\%$ | ✅ **99.83% cobertura (159/159 pass)** |
| **Paridad ORM ↔ Alembic (Anti-Mock)** | `make -C backend qa-parity` (PostgreSQL 17 real) | 0 discrepancias de esquema | ✅ **Paridad 1:1 certificada (17 tablas)** |
| **Lint, Tipado & SonarJS (Frontend)** | `make -C frontend qa-lint` (`vue-tsc`, `prettier`, `eslint`) | 0 errores / CC $\le 15$ | ✅ **100% Limpio** |
| **Cero Componentes UI Huérfanos** | `make -C frontend qa-orphans` | 100% componentes `.vue` con `.unit.ts` | ✅ **18/18 componentes cubiertos** |
| **Pruebas Unitarias Frontend** | `make -C frontend qa-unit` (`vitest` + `coverage-v8`) | Cobertura $\ge 95\%$ | ✅ **99.74% líneas / 95.62% ramas (50/50 pass)** |
| **Contratos OpenAPI & Fuzzing** | `make -C backend qa-contracts` (`schemathesis`) | 0 fallos 5xx / contrato | ✅ **626/626 casos aprobados** |
| **Seguridad Dinámica (DAST)** | `make -C backend qa-dast` (`zaproxy/zap-stable`) | `FAIL-NEW: 0` | ✅ **0 fallos (66 reglas PASS)** |
| **Ingeniería del Caos & Carga** | `make -C backend qa-chaos` (`Pumba` + `Locust` + `Prometheus`) | 0 errores bajo `netem 500ms` | ✅ **2.786 peticiones, 0 fallos** |
| **Auditoría IaC & Contenedores** | `./auditar-infra.sh` (`trivy config` + `trivy fs`) | 0 HIGH/CRITICAL misconfigs | ✅ **0 hallazgos** |

---

## 2. Suites Unitarias del Backend (`backend/tests/*.unit.py`)

- `tests/test_main.unit.py`: Healthcheck `/health`, cabeceras de seguridad HTTP (`Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`), sanitización de errores `422` en producción y ocultamiento de `/docs` en `APP_ENV=production`.
- `tests/test_security_11x.unit.py`:
  - Hashing `PBKDF2-HMAC-SHA256` con sal aleatoria, verificación en tiempo constante y soporte de transición para hashes SHA-256 heredados.
  - Generación y validación de tokens CSRF `HMAC-SHA256` (expiración, firma inválida, formato malformado).
  - Validador Anti-SSRF `validate_safe_outgoing_url` (bloqueo de esquemas no HTTP, credenciales embebidas, `localhost`, contenedor interno `postgres`/`redis`/`minio`, rangos RFC 1918 y fallo DNS).
  - Lector seguro de archivos `read_uploaded_file_safely` (corte inmediato HTTP 413 al superar 2 MB).
  - Validador Anti-CSWSH `verify_websocket_origin` y bloqueo de Mass Assignment (`extra="forbid"`).
  - Aislamiento de idempotencia por alcance (`build_idempotency_key`), rotación de refresh tokens con periodo de gracia de 5s y extracción dual Cookie/Bearer.
- `tests/test_schemas.unit.py` y `tests/test_models.unit.py`: Validaciones estrictas Pydantic v2 y modelos SQLAlchemy 2.0 (`Usuario`, `Estructura`, `Unidad`, `ContratoOcupacion`).
- `tests/test_auth.unit.py` y `tests/test_dependencies.unit.py`: Registro idempotente de Usuarios Fantasma, login con cookies `HttpOnly`, validación de JWT y `/api/auth/me`.
- `tests/test_finanzas_core.unit.py`, `tests/test_pagos.unit.py` y `tests/test_finanzas_router.unit.py`: Matemática financiera `Decimal` (`ROUND_HALF_UP`), conversión USD/VES con tasa BCV, pagos parciales vs totales, auditoría de rechazos y **Candado Contable** (`POST /api/finanzas/cierre-mensual`).

---

## 3. Escenarios BDD Karate Labs (`backend/test/api_test.feature`)

1. **Healthcheck y Cabeceras de Seguridad:** Verifica estado 200 y presencia de `X-Content-Type-Options: nosniff` y `X-Frame-Options: DENY`.
2. **Registro Idempotente de Usuario Fantasma:** Verifica alta con `es_activo: false` y rechazo `409 Conflict` al repetir `Idempotency-Key`.
3. **Rechazo de Mass Assignment (`extra="forbid"`):** Verifica que enviar `"es_activo": true` o `"rol": "PRESIDENTE"` en el registro devuelve `422 Unprocessable Entity`.
4. **Exigencia de `Idempotency-Key`:** Verifica retorno `422` cuando se omite la cabecera en mutaciones críticas.
5. **Autenticación Dual (`Cookie HttpOnly` + `Authorization: Bearer`):** Verifica login exitoso y consulta de `/api/auth/me` con ambos mecanismos.
6. **Protección de Rutas Privadas:** Verifica rechazo `401 Unauthorized` sin credenciales.
7. **Flujo Financiero y Candado Contable:** Verifica registro de tasa BCV, cierre mensual (`POST /api/finanzas/cierre-mensual`) y bloqueo `409 Conflict` ante intento de re-cierre.

---

## 4. Comandos de Certificación Efímera (`Rule Zero`)

```bash
# Ejecutar gates completos del backend en contenedores Docker efímeros
make -C backend qa-lint
make -C backend qa-complexity
make -C backend qa-deps
make -C backend qa-unit
make -C backend qa-parity

# Ejecutar el gate integral de cierre de tarea (.agents)
./.agents/scripts/certify_task_completion.sh
```
