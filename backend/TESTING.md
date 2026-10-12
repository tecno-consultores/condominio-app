# Bitácora de Pruebas y Validación (TESTING.md) - Backend

**Proyecto:** Condominio App  
**Estándar:** QA Blueprint Nivel 11X

---

## 1. Cobertura de Negocio en Pruebas Unitarias

La suite unitaria actual cubre de forma completamente aislada (sin red ni base de datos real):

- `tests/test_main.unit.py`:
  - Healthcheck HTTP `/health` respondiendo con estado 200 y JSON `{"status": "healthy"}`.
- `tests/test_schemas.unit.py`:
  - Validación de esquemas Pydantic `UsuarioCreate` (datos válidos, rechazo de correo malformado con validador de correo, campos requeridos).
  - Validación de serialización de respuesta en `UsuarioResponse` (`from_attributes`).
- `tests/test_models.unit.py`:
  - Modelado SQLAlchemy de `Usuario` (campos, defaults, flag fantasma `es_activo = False`).
  - Modelado de `Estructura` (Torres, Calles, Edificios).
  - Modelado de `Unidad` con identificador único.
  - Modelado de `ContratoOcupacion` (histórico de inquilinos y propietarios).
- `tests/test_auth.unit.py`:
  - Registro de usuarios fantasma (`POST /api/auth/register`) con mocking asíncrono de sesión DB y Redis.
  - Validación de unicidad de clave de idempotencia (`Idempotency-Key` en Redis devolviendo 409 Conflict si está repetida).
  - Rechazo de petición sin encabezado de idempotencia (código 422).
  - Validación de usuario duplicado (correo o cédula) retornando 409 Conflict y de violación de unicidad de BD (IntegrityError) retornando 400.
  - Manejo y rollback ante fallos inesperados de base de datos (código 500).
  - Inicio de sesión (`POST /api/auth/login`) con verificación de credenciales y creación de cookie `HttpOnly` `access_token`.
  - Rechazo de inicio de sesión con credenciales inválidas (código 401).
  - Endpoint `/api/auth/me`: rechazo sin cookie (401), validación de firma y expiración de token JWT (401 en caso de token expirado o inválido), y retorno exitoso de perfil autenticado.
- `tests/test_dependencies.unit.py`:
  - Dependencia `get_current_user`: rechazo sin cookie (401), token expirado, token adulterado y token sin `sub` (401), usuario inexistente (401) y continuación exitosa hacia el endpoint protegido.
- `tests/test_finanzas_core.unit.py` (núcleo matemático, fronteras súper estrictas para mutmut):
  - Redondeo `HALF_UP` a centavos y conversión USD/VES por la tasa del día (incluye tasa cero/negativa y moneda no soportada).
  - Regla de referencia obligatoria por método (`ZELLE`, `PAGO_MOVIL`, `TRANSFERENCIA` vs `EFECTIVO`).
  - Frontera exacta de "pago parcial vs total" (igual, excedente, acumulación de pagos previos y pago en cero).
  - Cálculo de saldo pendiente (nunca negativo) y deuda total agregada.
- `tests/test_pagos.unit.py`:
  - `POST /api/pagos/reportar`: conversión por tasa del día, idempotencia (409), referencia obligatoria (400), tasa no registrada (400), recibo inexistente (404), periodo bloqueado por Candado Contable (409), moneda inválida (422), falta de `Idempotency-Key` (422) y fallo de BD (500).
  - `PUT /api/pagos/{id}/aprobar`: aplicación de pago parcial, pago total exacto y acumulación sobre saldo previo; auditoría; conflictos 404/409.
  - `PUT /api/pagos/{id}/rechazar`: motivo obligatorio (422), registro de auditoría con motivo y conflictos 404/409.
  - `GET /api/pagos/revision`: listado de pagos `EN_REVISION`.
- `tests/test_finanzas_router.unit.py`:
  - `POST/GET /api/finanzas/tasa`: alta, actualización (upsert), validación de tasa positiva (422) y 404 si no está registrada.
  - `POST /api/finanzas/egresos`: conversión multimoneda, falta de tasa (400), periodo inválido (422), tasa cero (400) y fallo de BD (500).
  - `GET /api/finanzas/resumen`: deuda total, total de egresos, egresos por categoría y estado de cobranza.
  - `POST /api/finanzas/cierre-mensual`: bloqueo de recibos/egresos, inmutabilidad del Candado Contable (409 si ya cerrado) y periodo inválido (422).

---

## 2. Pruebas BDD, Caos y Resiliencia

- `test/api_test.feature`: Escenarios funcionales en Gherkin ejecutados por Karate Labs de caja negra contra la API viva.
- `tests/locustfile.py`: Perfil de carga concurrente y saturación para inyección de caos y estrés con Pumba + Locust + Prometheus.

---

## 3. Ejecución Efímera en Docker

Todas las pruebas se ejecutan utilizando contenedores efímeros sin dependencias instaladas en el host mediante `backend/Makefile`:

### Pruebas Unitarias y Cobertura (mínimo 95%):
```bash
make qa-unit
```

### Linters, Tipado y SAST:
```bash
make qa-lint
```

### Verificación de Complejidad Ciclomática (Radon) con gates:
```bash
make qa-complexity
```
Falla si algún bloque supera el grado **B** (complejidad) o el Índice de Mantenibilidad cae por debajo de **B** (gate riguroso en `scripts/radon_gates.py`).

### Auditoría de Vulnerabilidades en Dependencias (uv audit):
```bash
make qa-deps
```

### Perfilado de CPU de la API bajo carga (py-spy):
```bash
make qa-profile
```
Genera `profile.svg` muestreando al worker de uvicorn (detectado con `scripts/find_worker.py`) mientras Locust satura el endpoint.

### Auditoría de Infraestructura como Código (Trivy IaC + FS):
```bash
make qa-infra
```
Equivalente efímero a `../auditar-infra.sh` (mismo escaneo misconfigs HIGH/CRITICAL y CVEs CRITICAL).

### Pruebas de Mutación (Mutmut):
```bash
make qa-mutation
```

### Fuzzing y Contratos OpenAPI (Schemathesis):
```bash
make qa-contracts
```

### Seguridad Dinámica DAST (OWASP ZAP):
```bash
make qa-dast
```

### Certificación de Resiliencia y Caos (Pumba + Locust + Prometheus):
```bash
make qa-chaos
```

### Ejecución Integral de Calidad:
```bash
make qa-all
```

---

## 4. Ejecuciones Realizadas y Correcciones Aplicadas (2026-10-12)

Se ejecutaron por primera vez las suites que nunca habían corrido y se corrigieron los hallazgos:

| Suite | Herramienta | Resultado |
| --- | --- | --- |
| Contratos / Fuzzing | Schemathesis | ✅ **626/626 casos, 0 fallos** (antes: 15 fallos) |
| DAST | OWASP ZAP (`zaproxy/zap-stable`) | ✅ **FAIL-NEW: 0** (66 PASS) |
| Caos / Resiliencia | Pumba + Locust + Prometheus | ✅ **2786 reqs, 0 fallos, sin bloqueo** (p99 ≈ 1.4 s con `netem 500 ms`) |
| Unitarias | Pytest + Coverage | ✅ **122 pruebas, 99.66%** (mínimo 95%) |
| Lint / SAST | Ruff + Mypy + Bandit | ✅ Sin errores |
| Complejidad | Radon | ✅ Todo grado A |

### Correcciones derivadas

1. **500 en login/register por BD no inicializada**: el SQLite en memoria no tenía esquema. Se agregó `create_all` en el `lifespan` y `StaticPool` para mantener una única conexión (`src/database.py`, `src/main.py`).
2. **500 en register por falta de Redis**: el QA compose no levantaba Redis. Se agregó el servicio `redis` con healthcheck y `REDIS_URL` en `docker-compose.qa.yml`.
3. **Contratos**: se documentaron los 4xx faltantes (400/401/404/409) en `auth`, `pagos` y `finanzas`; `register` distingue 400 (malformado) vs 409 (duplicado); campos enteros `strict=True` (rechaza coerción `bool→int`); el malformado `Allow` de OPTIONS devenía de Starlette (header parcial) y se reconstruye desde los paths de OpenAPI; `/metrics` quedó fuera del contrato (`include_in_schema=False`).
4. **Correo `.test` (dominios reservados RFC 2606)**: se alineó la validación de correo con el `format: email` del contrato usando `email-validator` con `test_environment=True` (acepta los dominios de prueba que envía el fuzzing) manteniendo `Cache-Control: no-store` en toda respuesta (regla 10049 de ZAP).
5. **Caos**: el target `qa-chaos` no arrancaba Pumba/Prometheus (se anteponía la salida de Locust); ahora `stress_test` depende de `pumba` y `prometheus`. El locustfile contaba el login inválido (401 esperado) como fallo; ahora usa `catch_response` y lo marca como éxito.
6. **ZAP**: la imagen del blueprint (`owasp/zap2docker-stable`) fue deprecada (pull bloqueado); se migró a `zaproxy/zap-stable:latest`. El target tolera código 2 (advertencias, p. ej. 404 de `/robots.txt`) documentando que `FAIL-NEW=0`; sólo falla ante fails reales.

### Pendientes / Gaps (fuera de la suite del backend)

- Sólo queda bloqueado `qa-mutation` (mutmut v3 bajo Docker-in-Docker: los mutantes se clonan sin `pyproject.toml`). Autorizado posponer.

### Infraestructura Nivel 11X implementada (2026-10-12)

- **Gates de Radon**: `make qa-complexity` ahora bloquea sobre grado B (complejidad y mantenibilidad).
- **Auditoría de dependencias**: `make qa-deps` (uv audit) verde sin vulnerabilidades (139 paquetes).
- **Perfilado**: `make qa-profile` genera `profile.svg` con py-spy sobre el worker de uvicorn bajo carga de Locust; los contenedores ya tenían `SYS_PTRACE` + `seccomp:unconfined`.
- **Auditoría IaC**: `make qa-infra` y `auditar-infra.sh` (raíz) escanean misconfiguraciones (HIGH/CRITICAL) y CVEs (CRITICAL) con Trivy. Score limpio; manifiesto detectado: `backend/uv.lock`.
- **Barrera de Git**: `lefthook.yml` (pre-commit: ruff + detección de secretos), commit-msg (commitlint), pre-push (`auditar-infra.sh`); `instalar-hooks.sh` + `package.json` con `@commitlint/*` y lefthook.
- **CI/CD**: `.github/workflows/00-iac-audit.yml` (Trivy) y `01-ci-backend.yml` (qa-lint, qa-complexity, qa-deps, qa-unit en Docker efímero).
- **Tox**: `tox.ini` con el pipeline completo de QA local (lint, tipado, SAST, gates, auditoría y cobertura).
- **Limpieza**: `backend/limpieza.sh` (purga profunda con `sudo`, incluye perfiles chaos/graphify y `docker system prune`).
- **Graphify MCP**: perfil oculto `--profile graphify` en `docker-compose.qa.yml` (extracción de grafo semántico y servidor MCP SSE en `:8080`).

---
