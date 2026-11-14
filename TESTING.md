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
| **Complejidad Ciclomática & MI** | `make -C backend qa-complexity` (`radon_gates.py`) | CC $\le$ Grado B, MI $\ge$ Grado B | ✅ **Grado A/B (CC <= 10, MI >= B)** |
| **Auditoría de Dependencias** | `make -C backend qa-deps` (`uv audit`) | 0 CVEs conocidos | ✅ **0 vulnerabilidades (`118` paquetes incluyendo `pillow==13.0.0`)** |
| **Pruebas Unitarias Backend** | `make -C backend qa-unit` (`pytest` + `coverage`) | Cobertura $\ge 95\%$ | ✅ **97.22% cobertura (`276/276` pass, `0 skipped` con PostgreSQL 17; `src/bootstrap.py` `99%`, `src/worker.py` `98%`)** |
| **Pruebas de Mutación Backend** | `make -C backend qa-mutation` (`scripts/mutmut_gates.py`) | $\text{MSI} \ge 80\%$ | ✅ **86.40% MSI (`788/912`, `0` timeouts: `security.py` `93.14%`, `facturacion_lph.py` `85.00%`, `bootstrap.py` `84.90%`, `finanzas.py` `83.70%`)** |
| **Paridad ORM ↔ Alembic (Anti-Mock)** | `make -C backend qa-parity` (PostgreSQL 17 real) | 0 discrepancias de esquema | ✅ **Paridad 1:1 certificada (27 tablas + RLS PG17 + migración reversible `0009_hito18_tarea_diaria_unica`)** |
| **Lint, Tipado & SonarJS (Frontend)** | `make -C frontend qa-lint` (`vue-tsc`, `prettier`, `eslint`) | 0 errores / CC $\le 15$ | ✅ **100% Limpio (`src/` y `e2e/`, `0` HIGH/CRITICAL `pnpm audit`, `@playwright/test@1.64.1`)** |
| **Cero Componentes UI Huérfanos** | `make -C frontend qa-orphans` | 100% componentes `.vue` con `.unit.ts` | ✅ **42/42 componentes cubiertos (`54` suites)** |
| **Pruebas Unitarias Frontend** | `make -C frontend qa-unit` (`vitest` + `coverage-v8`) | Cobertura $\ge 95\%$ | ✅ **>= 95% cobertura V8 (`54` suites / `130/130` pass + build Vite limpio)** |
| **Pruebas de Mutación Frontend** | `make -C frontend qa-mutation` (`Stryker`) | $\text{MSI} \ge 80\%$ | ✅ **83.26% MSI (`stryker.conf.json`)** |
| **Salud Topológica AST (Graphify)** | `python3 .agents/scripts/verify_topological_health.py` | 0 acoplamientos inversos | ✅ **3.103 nodos, 7.551 relaciones, 163 comunidades (0 violaciones en 3 grafos: 5.520 nodos, 13.900 relaciones)** |
| **E2E Screenplay, Geometría, A11y & Visual** | `make -C frontend qa-e2e` (Playwright + `@axe-core/playwright`) | 0 fallos / 0 violaciones WCAG 2.1 AA / diff $\le 2\%$ | ✅ **51/51 pass (`375x667`, `390x844`, `1440x900`, claro/oscuro, `15` snapshots PNG)** |
| **Karate API BDD (Backend)** | `make -C backend qa-bdd` (`karatelabs`) | 100% escenarios Gherkin API | ✅ **25/25 pass (`backend/test/api_test.feature`, incluyendo Bootstrap Día 0)** |
| **Karate UI BDD (Frontend)** | `make -C frontend qa-bdd` (`karatelabs` + sidecar `chrome-cdp`) | 100% escenarios Gherkin UI | ✅ **13/13 pass (`frontend/test/ui_business_flow.feature`, Chrome CDP `9222`)** |
| **Performance & Best Practices (Frontend)** | `make -C frontend qa-perf` (`lhci autorun` en `/login`, `/register`) | Perf $\ge 90\%$, A11y $\ge 95\%$, BP $\ge 95\%$ | ✅ **Performance `99%`, Accessibility `100%`, Best Practices `100%`** |
| **Contratos OpenAPI & Fuzzing** | `make -C backend qa-contracts` (`schemathesis`) | 0 fallos 5xx / contrato | ✅ **59/59 operaciones OpenAPI aprobadas** |
| **Seguridad Dinámica (DAST)** | `make -C backend qa-dast` (`zaproxy/zap-stable`) | `FAIL-NEW: 0` | ✅ **0 fallos (`PASS: 67`, `FAIL-NEW: 0`)** |
| **Ingeniería del Caos & Carga** | `make -C backend qa-chaos` (`Pumba` + `Locust` + `Prometheus`) | 0 errores bajo `netem 500ms` | ✅ **2.786 peticiones, 0 fallos** |
| **Auditoría IaC & Contenedores** | `./scripts/auditar-infra.sh` + `trivy image` (`condominio-backend:hito18`, `condominio-frontend:hito18`) | 0 HIGH/CRITICAL misconfigs & CVEs | ✅ **0 hallazgos + smoke checks `--read-only` no-root (`10001:10001` y `101:101`)** |
| **Scripts Bash & Respaldos (`BATS`)** | `sinfallas/base-bash-qa:latest` (`shfmt -i 2 -ci`, `shellcheck`, `bats test/limpieza.bats test/backup_diario.bats`) | 0 advertencias / 100% pass | ✅ **8/8 pass (0 warnings)** |

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
- `tests/test_bootstrap_cli.unit.py`: Validación del CLI idempotente Día 0 (`src/bootstrap.py`), lectura desde `--from-env` y flags CLI (`--correo`, `--password`, `--condominio-id`, `--unidad-inicial`, `--allow-update-existing`), promoción de Usuarios Fantasma, detección de conflictos de identidad/tenant, contrato `QA-CLI-TTY-01` (sin argumentos devuelve ayuda y salida JSON UTF-8), PBKDF2 real (`100_000` iteraciones) y aislamiento multi-tenant RLS en **PostgreSQL 17** (`276/276` pruebas backend aprobadas, `97.22%` cobertura global; gate multi-core `scripts/mutmut_gates.py` con **`86.40%` MSI global**).

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
25. **Bootstrap Día 0 de Presidente inicial, generación de estructura y activación de residente Fantasma (`v1.0.0`):** Valida el aprovisionamiento del administrador inicial y la cadena operativa completa tras inicializar el condominio (**25/25 escenarios aprobados**).

> **Nota E2E UI (`frontend/test/ui_business_flow.feature`, Playwright y Lighthouse CI):** `frontend/docker-compose.qa.yml` incorpora el sidecar headless `chrome-cdp` (`mcr.microsoft.com/playwright:v1.64.1-jammy` en `127.0.0.1:9222`) compartido con `karatelabs` mediante `network_mode: "service:chrome-cdp"`, logrando **`13/13` escenarios aprobados** en Karate UI BDD (incluyendo validación geométrica DOM y theming nativo de `/login` y `/register`). Adicionalmente, la suite Playwright (`ui-e2e` contra `ui-prod` con `@playwright/test@1.64.1` sin CVEs HIGH) certifica **`51/51` pruebas** en `375x667`, `390x844` y `1440x900` (`0` violaciones críticas/serias WCAG 2.1 AA en modos claro/oscuro, `0` oclusiones Anti-JSDOM, botones `CopyButton` con `data-copied` y `15` snapshots visuales Linux) y **Lighthouse CI** alcanza **`99%` Performance, `100%` Accessibility y `100%` Best Practices**.

---

## 4. Comandos de Certificación Efímera (`Rule Zero`)

```bash
# Ejecutar gates completos del backend en contenedores Docker efímeros
make -C backend qa-lint
make -C backend qa-complexity
make -C backend qa-deps
make -C backend qa-unit
make -C backend qa-parity

# Validar scripts Bash (shfmt, ShellCheck y BATS) y purgar residuos efímeros
docker run --rm -u "$(id -u):$(id -g)" -v "$(pwd):/app" -w /app sinfallas/base-bash-qa:latest \
  bash -c "shfmt -d -i 2 -ci limpieza.sh scripts/limpieza.sh backend/limpieza.sh frontend/limpieza.sh && shellcheck limpieza.sh scripts/limpieza.sh backend/limpieza.sh frontend/limpieza.sh && bats test/limpieza.bats"
./limpieza.sh

# Ejecutar el gate integral de cierre de tarea (.agents)
./.agents/scripts/certify_task_completion.sh
```
