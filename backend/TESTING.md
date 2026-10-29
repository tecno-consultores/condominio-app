# Bitácora de Pruebas y Validación (TESTING.md) - Backend

**Proyecto:** Condominio App  
**Estándar:** QA Blueprint Nivel 11X

---

## 1. Cobertura de Negocio en Pruebas Unitarias

La suite unitaria actual cubre de forma completamente aislada (sin red ni base de datos real):

- `tests/test_main.unit.py`:
  - Healthcheck HTTP `/health` respondiendo con estado 200 y JSON `{"status": "healthy"}`.
  - Cabeceras de seguridad HTTP (`Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`).
- `tests/test_security_11x.unit.py`:
  - Hashing `PBKDF2-HMAC-SHA256` con sal criptográfica de 16 bytes, verificación en tiempo constante (`hmac.compare_digest`) y soporte de transición para hashes SHA-256 heredados.
  - Generación y validación de tokens CSRF `HMAC-SHA256` (`generate_csrf_token`, `validate_csrf_token`).
  - Validador Anti-SSRF `validate_safe_outgoing_url` (bloqueo de esquemas no HTTP, credenciales en URL, `localhost`, contenedores internos `postgres`/`redis`/`minio`, rangos RFC 1918 y fallo DNS).
  - Lector seguro de archivos `read_uploaded_file_safely` (corte inmediato HTTP 413 al superar 2 MB).
  - Validador Anti-CSWSH `verify_websocket_origin` para conexiones WebSocket.
  - Aislamiento de claves de idempotencia por alcance (`build_idempotency_key`: `idemp:{scope}:{key}`) y periodo de gracia de 5s para rotación concurrente de refresh tokens en KeyDB.
  - Bloqueo de Mass Assignment (`ConfigDict(extra="forbid")`), extracción dual `Cookie`/`Bearer` y sanitización de errores `422` en modo `production`.
- `tests/test_schemas.unit.py`:
  - Validación de esquemas Pydantic `UsuarioCreate` (datos válidos, rechazo de correo malformado con validador de correo, campos requeridos, bloqueo de campos extra).
  - Validación de serialización de respuesta en `UsuarioResponse` (`from_attributes`).
- `tests/test_models.unit.py`:
  - Modelado SQLAlchemy de `Usuario` (campos, defaults, flag fantasma `es_activo = False`).
  - Modelado de `Estructura` (Torres, Calles, Edificios).
  - Modelado de `Unidad` con identificador único.
  - Modelado de `ContratoOcupacion` (histórico de inquilinos y propietarios).
- `tests/test_auth.unit.py`:
  - Registro de usuarios fantasma (`POST /api/auth/register`) con mocking asíncrono de sesión DB y KeyDB.
  - Validación de unicidad de clave de idempotencia aislada por alcance (`Idempotency-Key` devolviendo 409 Conflict si está repetida).
  - Rechazo de petición sin encabezado de idempotencia (código 422).
  - Validación de usuario duplicado (correo o cédula) retornando 409 Conflict y de violación de unicidad de BD (IntegrityError) retornando 400.
  - Manejo y rollback ante fallos inesperados de base de datos (código 500).
  - Inicio de sesión (`POST /api/auth/login`) con verificación de credenciales y creación de cookie `HttpOnly` `access_token`.
  - Rechazo de inicio de sesión con credenciales inválidas (código 401).
  - Endpoint `/api/auth/me`: rechazo sin credenciales (401), validación de firma y expiración de token JWT (401 en caso de token expirado o inválido) y retorno exitoso de perfil autenticado por Cookie o Bearer.
- `tests/test_dependencies.unit.py`:
  - Dependencia `get_current_user`: rechazo sin cookie ni Bearer (401), token expirado, token adulterado y token sin `sub` (401), usuario inexistente (401) y continuación exitosa hacia el endpoint protegido.
- `tests/test_finanzas_core.unit.py` (núcleo matemático, fronteras súper estrictas para mutmut):
  - Redondeo `HALF_UP` a centavos y conversión USD/VES por la tasa del día (incluye tasa cero/negativa y moneda no soportada).
  - Regla de referencia obligatoria por método (`ZELLE`, `PAGO_MOVIL`, `TRANSFERENCIA` vs `EFECTIVO`).
  - Frontera exacta de "pago parcial vs total" (igual, excedente, acumulación de pagos previos y pago en cero).
  - Cálculo de saldo pendiente (nunca negativo) y deuda total agregada.
- `tests/test_pagos.unit.py`:
  - `POST /api/pagos/reportar`: conversión por tasa del día, idempotencia aislada por usuario (409), referencia obligatoria (400), tasa no registrada (400), recibo inexistente (404), periodo bloqueado por Candado Contable (409), moneda inválida (422), falta de `Idempotency-Key` (422) y fallo de BD (500).
  - `PUT /api/pagos/{id}/aprobar`: aplicación de pago parcial, pago total exacto y acumulación sobre saldo previo; auditoría; conflictos 404/409.
  - `PUT /api/pagos/{id}/rechazar`: motivo obligatorio (422), registro de auditoría con motivo y conflictos 404/409.
  - `GET /api/pagos/revision`: listado de pagos `EN_REVISION`.
- `tests/test_finanzas_router.unit.py`:
  - `POST/GET /api/finanzas/tasa`: alta, actualización (upsert), validación de tasa positiva (422) y 404 si no está registrada.
  - `POST /api/finanzas/egresos`: conversión multimoneda, falta de tasa (400), periodo inválido (422), tasa cero (400) y fallo de BD (500).
  - `GET /api/finanzas/resumen`: deuda total, total de egresos, egresos por categoría y estado de cobranza.
  - `POST /api/finanzas/cierre-mensual`: bloqueo de recibos/egresos, inmutabilidad del Candado Contable (409 si ya cerrado) y periodo inválido (422).
- `tests/test_hito4_operaciones.unit.py`:
  - `src/worker.py`: conversión determinista AVIF (`convertir_y_subir_avif`), cola de notificaciones en KeyDB (`encolar_notificacion_correo`) y generador idempotente diario de tareas (`generar_tareas_diarias_desde_plantillas`).
  - `src/routers/administracion.py`: generación idempotente de estructura/unidades (`POST /api/estructura/generar`), listado de unidades (`GET /api/estructura/unidades`), listado de Usuarios Fantasma (`GET /api/usuarios/pendientes`), activación/asignación de unidad (`PUT /api/usuarios/{id}/asignar`) y designación de cargos de Junta (`PUT /api/junta/cargos` validando contrato activo de `PROPIETARIO`).
  - `src/routers/incidencias.py`: listado de incidencias abiertas por prioridad (`GET /api/incidencias/abiertas`), creación idempotente (`POST /api/incidencias/crear`) y adhesión única por vecino (`POST /api/incidencias/{id}/adherir`).
  - `src/routers/operaciones.py`: plantillas y tareas del conserje con cierre automático de incidencia vinculada (`PUT /api/tareas/{id}/completar`), galería de voceros con límite estricto de 30 fotos/mes (`POST /api/voceros/fotos` devolviendo `429 Too Many Requests`), bitácora del secretario (`POST /api/bitacora/acta`, `GET /api/bitacora/historial`) y comunicados con validación Anti-SSRF (`POST /api/comunicados`, `GET /api/comunicados/recientes`).

---

## 2. Pruebas BDD, Paridad PostgreSQL 17, Caos y Resiliencia

- `test/api_test.feature`: 7 escenarios funcionales en Gherkin ejecutados por Karate Labs de caja negra contra la API viva (`make qa-bdd`).
- `make qa-parity`: Verificación de paridad real entre `alembic upgrade head` sobre `postgres:17-alpine` y los modelos SQLAlchemy (`../.agents/scripts/verify_alembic_orm_parity.py`).
- `tests/locustfile.py`: Perfil de carga concurrente y saturación para inyección de caos y estrés con Pumba + Locust + Prometheus.

---

## 3. Ejecución Efímera en Docker

Todas las pruebas se ejecutan utilizando contenedores efímeros sin dependencias instaladas en el host mediante `backend/Makefile`:

```bash
make qa-unit         # Pruebas unitarias + cobertura (mínimo 95%)
make qa-lint         # Ruff + Mypy (--strict) + Bandit (SAST)
make qa-complexity   # Radon (complejidad ciclomática e índice de mantenibilidad <= B)
make qa-deps         # Auditoría de vulnerabilidades en dependencias (uv audit)
make qa-parity       # Paridad real Alembic <-> ORM contra PostgreSQL 17
make qa-bdd          # Escenarios BDD Gherkin con Karate Labs
make qa-profile      # Perfilado de CPU con py-spy bajo carga de Locust
make qa-infra        # Auditoría Trivy IaC + FS (HIGH/CRITICAL = 0)
make qa-mutation     # Pruebas de mutación (Mutmut)
make qa-contracts    # Fuzzing OpenAPI (Schemathesis)
make qa-dast         # Seguridad dinámica (OWASP ZAP)
make qa-chaos        # Ingeniería del Caos (Pumba + Locust + Prometheus)
make qa-all          # Pipeline integral
```
