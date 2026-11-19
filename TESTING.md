# 🧪 Bitácora General de Calidad y Certificación 11X (TESTING.md)

**Proyecto:** Condominio App  
**Estándar:** Gobernanza y Calidad Corporativa Nivel 11X (`Rule Zero` — 100% Docker Efímero)  
**Bitácoras Detalladas:** [`backend/TESTING.md`](./backend/TESTING.md) · [`frontend/TESTING.md`](./frontend/TESTING.md)

---

## 1. Resumen Ejecutivo de Métricas QA 11X (Hito 23)

| Capa de la Pirámide 11X | Herramienta / Gate | Umbral Exigido | Estado Actual |
| :--- | :--- | :--- | :--- |
| **Secret Scanning** | `./scripts/verificar-secretos.sh` | 0 secretos expuestos | ✅ **0 hallazgos (`315` archivos escaneados con `grep -e`, `.env.example` y tests incluidos)** |
| **Lint, Tipado & SAST (Backend)** | `make -C backend qa-lint` (`ruff`, `mypy --strict`, `bandit`) | 0 errores / 0 advertencias | ✅ **100% Limpio (`72` archivos `ruff check`/`format`, `mypy --strict` `25` archivos fuente, `bandit` `0` hallazgos)** |
| **Complejidad Ciclomática & MI** | `make -C backend qa-complexity` (`radon_gates.py`) | CC $\le$ Grado A ($\le 5$), MI $\ge$ A | ✅ **Grado A (`MAX_GRADE = 1`, `CC <= 5`, `MI >= A` en todo `src/`)** |
| **Auditoría de Dependencias** | `make -C backend qa-deps` (`uv audit`) | 0 CVEs conocidos | ✅ **0 vulnerabilidades (`118` paquetes incluyendo `pillow==13.0.0`, baseline Hito 19)** |
| **Pruebas Unitarias Backend** | `make -C backend qa-unit` (`pytest` + `coverage`) | Cobertura $\ge 95\%$ | ✅ **99.42% (`464 passed, 4 skipped` en SQLite con `PRAGMA foreign_keys=ON`; PG17 `qa-parity`: `23 passed, 0 skipped`)** |
| **Pruebas de Mutación Backend** | `make -C backend qa-mutation` (`scripts/mutmut_gates.py`) | $\text{MSI} \ge 80\%$ por módulo | ✅ **91.60% MSI global (`2324` muertos / `2537` en `12/12` módulos lógicos `81.30%–99.49%`; `10` timeouts no contados como muertos)** |
| **Paridad ORM ↔ Alembic (Anti-Mock)** | `make -C backend qa-parity` (PostgreSQL 17 + KeyDB) | 0 discrepancias de esquema | ✅ **Paridad 1:1 certificada (`27` tablas ORM + RLS PG17 + `23 passed, 0 skipped` en ciclo reversible `0001..0010`)** |
| **Lint, Tipado & SonarJS (Frontend)** | `make -C frontend qa-lint` (`vue-tsc`, `tsc`, `prettier`, `eslint`) | 0 errores / CC $\le 15$ | ✅ **100% Limpio (`720` entradas `--frozen-lockfile`, `0` HIGH/CRIT en `audit:deps`, `tsc -p tsconfig.e2e.json`, `prettier` y `eslint` cubriendo `src/` y `e2e/`)** |
| **Cero Componentes UI Huérfanos** | `make -C frontend qa-orphans` | 100% componentes `.vue` con `.unit.ts` | ✅ **44/44 componentes cubiertos (`63` suites `.unit.ts`, `0` huérfanos)** |
| **Pruebas Unitarias Frontend** | `make -C frontend qa-unit` (`vitest` + `coverage-v8`) | Cobertura $\ge 95\%$ | ✅ **99.03% Stmts / 96.16% Branch / 98.72% Funcs / 99.12% Lines (`63/63` suites, `226/226` pass + Vite `178` módulos)** |
| **Pruebas de Mutación Frontend** | `make -C frontend qa-mutation` (`Stryker` vía `qa-vue3` + `ui-e2e`) | $\text{MSI} \ge 80\%$ | ✅ **97.49% MSI (`2437` muertos, `9` timeouts, `62` sobrevivientes en `16` archivos fuente; `ignoreStatic: true`)** |
| **Salud Topológica AST (Graphify)** | `.agents/scripts/verify_topological_health.py` | 0 acoplamientos inversos | ✅ **3 grafos `--code-only`: `8.254` nodos, `22.285` relaciones, `0` `.md`, `0` violaciones (raíz `4.463`, back `2.388`, front `1.403`)** |
| **Arquitectura FINOS CALM `1.2`** | `./.agents/scripts/validate_calm_architecture.sh` | 7 controles obligatorios | ✅ **Aprobado (`architecture/qa-11x.calm.json`: `10` nodos, `14` relaciones, `7` controles)** |
| **E2E Screenplay, Geometría, A11y & Visual** | `make -C frontend qa-e2e` (Playwright + `@axe-core/playwright`) | 0 fallos / 0 violaciones WCAG / diff $\le 2\%$ | ✅ **88/88 pass en `4` viewports (`375x667`, `390x844`, `768x1024`, `1440x900`; `23/23` vistas WCAG 2.1 AA + `best-practice` claro/oscuro, `24` PNGs)** |
| **Karate API BDD (Backend)** | `make -C backend qa-bdd` (`karatelabs`) | 100% escenarios Gherkin API | ✅ **33/33 pass (`backend/test/api_test.feature`, flujos nominales `2xx` de los `9` routers aislados por UUID)** |
| **Karate UI BDD (Frontend)** | `make -C frontend qa-bdd` (`karatelabs` + sidecar `chrome-cdp`) | 100% escenarios Gherkin UI | ✅ **18/18 pass (`frontend/test/ui_business_flow.feature`, Chrome CDP `9222`, flujos autenticados por rol Hito 23)** |
| **Performance & Best Practices (Frontend)** | `make -C frontend qa-perf` (`lhci autorun`, 3 corridas/ruta) | Perf $\ge 90\%$, A11y $\ge 95\%$, BP $\ge 95\%$, `CLS = 0` | ✅ **Lighthouse CI aprobado (`6/6` corridas): `/login` y `/register` con `99%` Perf / `100%` A11y / `96%` BP / `CLS = 0`** |
| **Contratos OpenAPI & Fuzzing** | `make -C backend qa-contracts` (`schemathesis`) | 0 fallos 5xx / contrato | ✅ **60/60 operaciones OpenAPI aprobadas (`9.049/9.049` casos generados, baseline Hito 21)** |
| **Seguridad Dinámica (DAST)** | `make -C backend qa-dast` (`zaproxy/zap-stable`, `zap.yaml` no-root) | `0 WARN-NEW / 0 FAIL-NEW` | ✅ **0 alertas (`88` URLs, `FAIL-NEW: 0`, `WARN-NEW: 0`, `PASS: 62`)** |
| **Perfilado CPU & Carga Real** | `make -C backend qa-profile` (`profiler` `py-spy` + `Locust`) | Flamegraph SVG válido y 0% fallos | ✅ **Sidecar `py-spy` (`PID 188`, `288` muestras, `0` errores) + Locust `866` reqs, `0.00%` fallos (`29.25` req/s, `p50 7ms`, `p95 44ms`)** |
| **Ingeniería del Caos** | `make -C backend qa-chaos` (`Pumba` + `Locust` + `Prometheus`) | 0 errores bajo `netem 500ms` | ✅ **2.786 peticiones, 0 fallos (baseline Hito 19)** |
| **Auditoría IaC, SBOM & Imágenes** | `./scripts/auditar-infra.sh` + `trivy image` + `generar-sbom-cyclonedx.sh` | 0 HIGH/CRITICAL misconfigs & CVEs | ✅ **Trivy IaC/FS `HIGH/CRITICAL = 0`; SBOM CycloneDX en `artifacts/sbom/`** |
| **Scripts Bash & Respaldos (`BATS`)** | `qa-bash` (`sinfallas/base-bash-qa`: `shfmt -i 2 -ci`, `shellcheck`, `bats`, `kcov`) | Cobertura `kcov >= 95%` / 0 alertas | ✅ **33/33 pass en `10` archivos BATS / `kcov` `95.26%` (`522/548` líneas), `0` warnings** |

---

## 2. Suites Unitarias del Backend (`backend/tests/*.unit.py`)

- `tests/test_main.unit.py`: Healthcheck `/health`, cabeceras de seguridad HTTP (`Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Content-Security-Policy` con `frame-ancestors 'none'`, `Cross-Origin-Opener-Policy: same-origin-allow-popups`, `Cross-Origin-Resource-Policy: same-origin`, `Permissions-Policy`, `Vary` sin duplicados y `Strict-Transport-Security` condicional), aislamiento pre-auth Fetch Metadata (`403` ante `cross-site`), sanitización de errores `422` en producción, ocultamiento de `/docs` y arranque *Fail-Fast* en `lifespan` bajo `APP_ENV=production`.
- `tests/test_security_11x.unit.py`:
  - Hashing `PBKDF2-HMAC-SHA256` con sal aleatoria, verificación en tiempo constante, rechazo estricto de hashes legacy SHA-256 sin sal y validación *Fail-Fast* (`validate_production_security_settings`) en `APP_ENV=production`.
  - Generación y validación de tokens CSRF `HMAC-SHA256` (expiración, firma inválida, formato malformado).
  - Validador Anti-SSRF `validate_safe_outgoing_url` (bloqueo de esquemas no HTTP, credenciales embebidas, `localhost`, contenedor interno `postgres`/`redis`/`minio`, rangos RFC 1918 y fallo DNS).
  - Lector seguro de archivos `read_uploaded_file_safely` (corte inmediato HTTP 413 al superar 2 MB).
  - Validador Anti-CSWSH `verify_websocket_origin` y bloqueo de Mass Assignment (`extra="forbid"`).
  - Aislamiento de idempotencia por alcance (`build_idempotency_key`), rotación de refresh tokens con periodo de gracia de 5s y extracción dual Cookie/Bearer.
- `tests/test_schemas.unit.py` y `tests/test_models.unit.py`: Validaciones estrictas Pydantic v2 y modelos SQLAlchemy 2.0 (`Usuario`, `Estructura`, `Unidad`, `ContratoOcupacion`).
- `tests/test_auth.unit.py` y `tests/test_dependencies.unit.py`: Registro idempotente de Usuarios Fantasma, login con cookies `HttpOnly`, validación de JWT y `/api/auth/me`.
- `tests/test_finanzas_core.unit.py`, `tests/test_pagos.unit.py`, `tests/test_finanzas_router.unit.py` y `tests/test_hito10_alicuotas_solvencia.unit.py`: Matemática financiera `Decimal` (`ROUND_HALF_UP`), prorrateo por alícuotas mediante el **Método del Resto Mayor (Hamilton)**, facturación trimodal (`ALICUOTA`, `CUOTA_FIJA` con conciliación de superávit/déficit hacia `FondoCondominio`, y `PARTES_IGUALES`), aplicación automática de `credito_disponible_usd`, bloqueo `409 Conflict` ante referencias bancarias duplicadas, firma/verificación `HMAC-SHA256` de certificados de solvencia y **Candado Contable** (`POST /api/finanzas/cierre-mensual`).
- `tests/test_hito11_consultas_asambleas.unit.py`: Firma y verificación criptográfica `HMAC-SHA256` de votos (`generar_firma_voto_consulta`, `verificar_firma_voto_consulta`), escrutinio ponderado LPH (`DOS_TERCIOS` $66.6700\%$, `MAYORIA_SIMPLE` $50.0100\%$ y `UNANIMIDAD` $100.0000\%$), creación/listado/detalle de Cartas Consulta y Asambleas (`/api/consultas`), voto único por unidad con validación de `puede_votar_asamblea` (`403 Forbidden` para inquilinos sin poder y `409 Conflict` para voto duplicado) y cierre con asiento automático en `BitacoraActa`.
- `tests/test_hito12_accesos_paqueteria.unit.py`: Firma y verificación en tiempo constante `HMAC-SHA256` de Pases de Visita QR (`construir_claims_pase_qr`, `generar_firma_pase_qr`, `construir_token_pase_qr`, `decodificar_y_verificar_token_pase_qr`), quema atómica Anti-Replay en KeyDB (`burn_qr_nonce`, `is_qr_nonce_burned`), emisión/listado/revocación de pases (`/api/accesos/pases`), verificación en garita (`POST /api/accesos/verificar-qr`) y cadena de custodia de paquetería (`/api/paqueteria`).
- `tests/test_hito13_reservas_areas.unit.py`: Configuración y listado de áreas sociales (`/api/reservas/areas`), solicitud de reserva con **Candado de Solvencia Estricta** (`$0.00 USD` deuda en `Recibo` devolviendo `403 Forbidden` a unidades morosas), exclusividad de fecha por área (`409 Conflict`), generación automática de `TareaDiaria` de inspección post-evento y cierre de inspección (`PUT /api/reservas/{id}/inspeccionar`) completando la tarea del conserje.
- `tests/test_hito17_3_concurrencia_finanzas.unit.py`: Unicidad DDL `Recibo(unidad_id, periodo)` (`uq_recibo_unidad_periodo`), índice único parcial `uq_pagos_metodo_ref_activo` (excluyendo `RECHAZADO`/`NULL`), titularidad Anti-IDOR en `POST /api/pagos/reportar` (`403`), aprobación atómica con `Idempotency-Key` + `.with_for_update()` (`PUT /api/pagos/{id}/aprobar`), bloqueo `409` en `POST /api/finanzas/egresos` cuando `ReporteMensual.estado == "CERRADO"`, prorrateo LPH por alícuotas de cuotas extraordinarias en `ALICUOTA` (`src/facturacion_lph.py`), validación `validar_suma_alicuotas` y fracción racional exacta `2/3` (`FRACCION_DOS_TERCIOS`).
- `tests/test_hito17_4_integridad_rls.unit.py`: Bloqueo de voto tras `fecha_cierre` (`409`), cierre atómico de consultas sin actas duplicadas, `jti` anti-replay en votos/solvencia y verificación live de deuda en `GET /api/finanzas/solvencia/verificar/{folio}`, índice único parcial `uq_reserva_area_fecha_activa` + `PUT /api/reservas/{reserva_id}/cancelar` + cargo contable `DANOS_AREA_SOCIAL` en `FINALIZADA_CON_DANOS`, DTO dual `UnidadPublicaResponse` vs `UnidadResponse`, histórico `ContratoOcupacion` (`fecha_fin`), regla LPH Junta para `INQUILINO`, `apply_rls_session_settings` y validación real en **PostgreSQL 17** de `relrowsecurity`/`relforcerowsecurity` en las 27 tablas ORM más aislamiento multi-tenant por `condominio_id` bajo rol `condominio_app_runtime`.
- `tests/test_hito18_worker_prod.unit.py`: Conversión real `Pillow` PNG $\to$ AVIF y subida HTTP autenticada con `AWS4-HMAC-SHA256` hacia MinIO, restricción `uq_tarea_diaria_plantilla_fecha` (`UniqueConstraint`) y rollback limpio en carrera DB de `generar_tareas_diarias_desde_plantillas`, envío SMTP `STARTTLS` con sanitización CRLF y reintentos acotados hacia `queue:notifications:dlq`, supervisión `QA-HEALTH-01` real sin mocks (`run_worker_orchestrator`, heartbeat físico, detección de salida/excepción de tareas obligatorias) y pruebas CLI (`--check-health`, `--once`, `--help`).
- `tests/test_bootstrap_cli.unit.py`: Validación del CLI idempotente Día 0 (`src/bootstrap.py`), lectura desde `--from-env` y flags CLI sin exposición de contraseñas (`--correo`, `--condominio-id`, `--unidad-inicial`, `--allow-update-existing`), promoción de Usuarios Fantasma bloqueando cuentas revocadas administrativamente, detección de conflictos de identidad/tenant, contrato `QA-CLI-TTY-01` (sin argumentos devuelve ayuda y salida JSON UTF-8), `PBKDF2` (`600_000` iteraciones async) y aislamiento multi-tenant RLS en **PostgreSQL 17**.
- `tests/test_hito20_seguridad_rls_rbac.unit.py`: Subclaves independientes `HKDF-SHA256`, validación estricta de claims JWT (`typ`/`iat`/`iss`/`aud`), lockout atómico Lua en KeyDB (`ip` + `correo`), revocación fail-closed 7d sin fugas RAM, bloqueo `Cookie + Bearer dummy` en CSRF, protección `/metrics`, validación `ALLOWED_HOSTS`/`TRUSTED_PROXY_IPS`, cabeceras OSHP ante HTTP `500`, contención RBAC `VICEPRESIDENTE -> PRESIDENTE` y privacidad/aislamiento en `estructura/unidades`, `finanzas/resumen`, `paqueteria`, `reservas` y `accesos/pases/mios`.
- **Erradicación Anti-Mock Blindness (`tests/test_{database,facturacion_lph,redis_client,administracion,incidencias}.unit.py` y `test_pg17_http_concurrency.unit.py` — Hito 23):** Suites unitarias sobre motores SQLite con `PRAGMA foreign_keys=ON` (`0` `_mock_session` ni roles ficticios), cobertura dinámica de **27 tablas ORM** y esquemas Pydantic con `extra="forbid"`, concurrencia real PostgreSQL 17 + KeyDB (`23 passed, 0 skipped`), **Radon Grado A (`CC <= 5`, `MI >= A`)**, **Mutmut `91.60%` MSI global** en los `12/12` módulos lógicos (`2324/2537`, sin contar timeouts como muertos), **OWASP ZAP DAST** (`zap.yaml` no-root, `88 URLs`, `0 WARN-NEW / 0 FAIL-NEW`, `PASS: 62`) y `qa-profile` con sidecar aislado `profiler` (**`py-spy`** PID `188`, `288` muestras, `0` errores) bajo carga **Locust** (**`866` reqs, `0.00%` fallos**). Suite total SQLite: **`464 passed, 4 skipped` (`99.42%` cobertura)** (`test_bootstrap_cli.unit.py` re-validado `15 passed, 1 skipped`).

---

## 3. Escenarios BDD Karate Labs (`backend/test/api_test.feature`)

1. **Healthcheck y Cabeceras de Seguridad:** Verifica estado 200 y presencia de `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy` (`frame-ancestors 'none'`), `Cross-Origin-Opener-Policy: same-origin-allow-popups`, `Cross-Origin-Resource-Policy: same-origin`, `Permissions-Policy` y `Vary` (`Sec-Fetch-Site`).
2. **Registro Idempotente de Usuario Fantasma:** Verifica alta con `es_activo: false` y rechazo `409 Conflict` al repetir `Idempotency-Key`.
3. **Rechazo de Mass Assignment (`extra="forbid"`):** Verifica que enviar `"es_activo": true` o `"rol": "PRESIDENTE"` en el registro devuelve `422 Unprocessable Entity`.
4. **Exigencia de `Idempotency-Key`:** Verifica retorno `422` cuando se omite la cabecera en mutaciones críticas.
5. **Autenticación Dual (`Cookie HttpOnly` + `Authorization: Bearer`):** Verifica login exitoso y consulta de `/api/auth/me` con ambos mecanismos.
6. **Protección de Rutas Privadas:** Verifica rechazo `401 Unauthorized` sin credenciales.
7. **Flujo Financiero y Candado Contable:** Verifica registro de tasa BCV, cierre mensual (`POST /api/finanzas/cierre-mensual`) y bloqueo `409 Conflict` ante intento de re-cierre.
8. **Estructura Física, Activación de Usuario Fantasma y Junta (Hito 4):** Verifica generación de unidades, activación y designación de cargos.
9. **Embudo de Incidencias Vecinales y Adhesión "¡Me sumo!" (Hito 4):** Verifica creación y adhesión única por vecino.
10. **Checklist Diario del Conserje, Galería de Voceros, Bitácora y Comunicados Anti-SSRF (Hito 4):** Verifica flujo operativo completo y bloqueo Anti-SSRF.
11. **Seguridad de URLs de Evidencia (`UrlEvidenciaSegura`):** Verifica bloqueo `422` de esquemas `javascript:` y `data:`.
12. **Facturación Trimodal LPH (`CUOTA_FIJA`), Fondos Patrimoniales y Desglose de Recibo (Hito 10):** Verifica alta de `FondoCondominio`, actualización de alícuota/cuota fija, emisión idempotente `POST /api/finanzas/facturar-periodo` con conciliación de superávit y consulta de `GET /api/finanzas/recibos/{id}/desglose`.
13. **Anti-Fraude de Referencia Bancaria (`409`), Acreditación de Sobrepago y Certificado Digital de Solvencia `HMAC-SHA256` (Hito 10):** Verifica bloqueo `409` al reutilizar `(metodo, numero_referencia)`, acreditación de excedente en `credito_disponible_usd`, emisión de `POST /api/finanzas/solvencia/{unidad_id}` y verificación pública `GET /api/finanzas/solvencia/verificar/{folio}`.
14. **Protección 401 de Cartas Consulta y Asambleas (Hito 11):** Verifica que `GET /api/consultas` y `GET /api/consultas/1` sin sesión devuelven `401 Unauthorized`.
15. **Contención RBAC de Usuario Fantasma en Cartas Consulta LPH (Hito 11):** Verifica que un Usuario Fantasma autenticado recibe `403 Forbidden` al intentar listar, crear, votar o cerrar consultas en `/api/consultas`.
16. **Protección 401 de Accesos QR y Paquetería en Garita (Hito 12):** Verifica que `GET /api/accesos/pases/mios` y `GET /api/paqueteria` sin sesión devuelven `401 Unauthorized`.
17. **Contención RBAC de Usuario Fantasma en Accesos QR y Paquetería (Hito 12):** Verifica que un Usuario Fantasma autenticado recibe `403 Forbidden` al intentar emitir/listar pases QR, verificar en garita o gestionar paquetería.
18. **Protección 401 de Reserva de Áreas Sociales (Hito 13):** Verifica que `GET /api/reservas/areas` y `GET /api/reservas` sin sesión devuelven `401 Unauthorized`.
19. **Contención RBAC de Usuario Fantasma en Reserva de Áreas Sociales e Inspección Post-Evento (Hito 13):** Verifica que un Usuario Fantasma autenticado recibe `403 Forbidden` al consultar/crear áreas sociales, solicitar reservas o registrar inspecciones.
20. **Ciclo de Sesión Completo, CSRF Real, Bloqueo `5/15m` e Idempotencia `8..128` (Hito 17.2):** Verifica `/api/auth/me` con `cedula`/`telefono`/`unidad_activa_id`, rechazo `403` sin `X-CSRF-Token`, rotación en `POST /api/auth/refresh`, cierre `POST /api/auth/logout` con `Clear-Site-Data` y revocación de tokens emitidos, rechazo de `Idempotency-Key` fuera de rango y bloqueo `429` tras 5 intentos fallidos de inicio de sesión.
21. **Aislamiento Temprano Fetch Metadata (`Sec-Fetch-*`):** Verifica rechazo `403` antes de autenticación ante solicitudes `Sec-Fetch-Site: cross-site` + `Sec-Fetch-Mode: cors` (con `X-Frame-Options: DENY` y `Vary: Sec-Fetch-Site`) y aceptación `200` con `Content-Security-Policy` ante `Sec-Fetch-Site: same-origin`.
22. **Concurrencia Financiera, Anti-IDOR y Candado Contable en Egresos (Hito 17.3):** Verifica exigencia de `Idempotency-Key` (`422`), rechazo anti-IDOR `403` al reportar pagos de unidades ajenas y bloqueo `409 Conflict` en `POST /api/finanzas/egresos` cuando `ReporteMensual.estado == "CERRADO"`.
23. **Privacidad DTO en Unidades Públicas y Contratos de Cancelación de Reservas (Hito 17.4):** Verifica exposición mínima pública en `GET /api/estructura/unidades` + `UnidadPublicaResponse` en OpenAPI (sin campos financieros), verificación pública de solvencia inexistente (`404`), exigencia `Idempotency-Key` (`422`) y contención RBAC Fantasma (`403`) en `PUT /api/reservas/{reserva_id}/cancelar`.
24. **Contratos de Infraestructura y Operaciones del Worker (Hito 18):** Verifica cabeceras OSHP en `GET /health`, presencia de `/api/tareas/generar-diarias` y exclusión de `/metrics` en `/openapi.json`, protección `401` sin credenciales y contención RBAC Fantasma (`403`) con `Idempotency-Key` dinámico.
25. **Bootstrap Día 0 de Presidente inicial, generación de estructura y activación de residente Fantasma (`v1.0.0`):** Valida el aprovisionamiento del administrador inicial y la cadena operativa completa tras inicializar el condominio.
26. **Contención de Operación y Secretos Hito 19 (`api_test.feature`):** Registro UUID aislado verificando contrato público y contención RBAC Fantasma en `/api/tareas/generar-diarias`.
27. **Contención RBAC/IDOR y Privacidad DTO Hito 20:** Verifica rechazo `403 Forbidden` ante escalación `VICEPRESIDENTE -> PRESIDENTE` y ocultamiento de campos financieros en `/api/estructura/unidades` para roles no autorizados (complementado por Escenario 2 exigiendo `METRICS_AUTH_TOKEN` en `/metrics`).
28. **Idempotencia con Replay `2xx` y Liberación en Error `4xx` (Hito 21):** Verifica *response replay* determinista (`X-Idempotency-Replayed: true`), rechazo `409 Conflict` ante reutilización con payload distinto y liberación de clave tras `400 Bad Request` permitiendo reintento exitoso `201`.
29. **Subida Segura de Evidencias `POST /api/evidencias/subir` (Hito 21):** Verifica streaming `application/octet-stream` aceptando PNG (`202 ENCOLADO` destino `image/avif`) y rechazando binario EXE (`415 Unsupported Media Type`).
30. **Fusión Contable LPH (`UPSERT`) y Bloqueo de Cierre con Pagos `EN_REVISION` (Hito 21):** Verifica reserva con `costo_uso_usd > 0`, emisión `facturar-periodo` (`PARTES_IGUALES`) sin choque `409` sobre el recibo preliminar, bloqueo `409` de `/api/finanzas/cierre-mensual` con pago `EN_REVISION` y cierre `200` tras rechazo controlado.
31. **Flujos Nominales `2xx` de Finanzas, Pagos y Administración (Hito 23):** Verifica alta de fondo patrimonial, egresos, facturación, emisión/verificación de solvencia `HMAC-SHA256`, actualización de alícuota y aprobación de pago con UUID aislado.
32. **Flujos Nominales `2xx` de Consultas LPH y Reservas de Áreas Sociales (Hito 23):** Verifica emisión de voto ponderado, quorum `100.0000` y cierre de consulta Art. 23, listado, solicitud/cancelación e inspección post-evento de reservas.
33. **Flujos Nominales `2xx` de Incidencias, Operaciones, Accesos QR, Paquetería y Junta (Hito 23):** Verifica creación/adhesión de incidencias, checklist diario de conserjería, vocería/bitácora/comunicado, emisión/verificación QR, paquetería y designación de Junta (**`33/33` escenarios aprobados**).

> **Nota E2E UI (`frontend/test/ui_business_flow.feature`, Playwright y Lighthouse CI):** `frontend/docker-compose.qa.yml` incorpora el sidecar headless `chrome-cdp` (`mcr.microsoft.com/playwright:v1.64.1-jammy` en `127.0.0.1:9222`) compartido con `karatelabs` mediante `network_mode: "service:chrome-cdp"`, logrando **`18/18` escenarios aprobados** en Karate UI BDD (incluyendo geometría DOM, ruta `404` `#not-found-card` y flujos autenticados por rol Hito 23). Adicionalmente, la suite Playwright (`ui-e2e` contra `ui-prod` con `@playwright/test@1.64.1` sin CVEs HIGH) certifica **`88/88` pruebas (`1.2m`)** en **`4` viewports (`375x667`, `390x844`, `768x1024`, `1440x900`)** (`23/23` vistas WCAG 2.1 AA + `best-practice` claro/oscuro, `0` violaciones, Screenplay sin selectores crudos y **`24` snapshots visuales PNG Linux**) y **Lighthouse CI** alcanza (`6/6` corridas): **`99%` Performance, `100%` Accessibility, `96%` Best Practices y `CLS = 0`**.

---

## 4. Comandos de Certificación Efímera (`Rule Zero`)

```bash
# Ejecutar gates completos del backend en contenedores Docker efímeros
make -C backend qa-lint
make -C backend qa-complexity
make -C backend qa-deps
make -C backend qa-unit
make -C backend qa-parity

# Validar scripts Bash (shfmt, ShellCheck, BATS y kcov >= 95%) y purgar residuos efímeros
make qa-bash
./scripts/limpieza.sh

# Ejecutar el gate integral de cierre de tarea (.agents)
./.agents/scripts/certify_task_completion.sh
```
