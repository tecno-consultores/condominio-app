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
| **Auditoría de Dependencias** | `make -C backend qa-deps` (`uv audit`) | 0 CVEs conocidos | ✅ **0 vulnerabilidades (`dnspython>=2.9.2`)** |
| **Pruebas Unitarias Backend** | `make -C backend qa-unit` (`pytest` + `coverage`) | Cobertura $\ge 95\%$ | ✅ **97.07% cobertura (241/241 pass, `0 skipped` con `POSTGRES_TEST_URL`)** |
| **Paridad ORM ↔ Alembic (Anti-Mock)** | `make -C backend qa-parity` (PostgreSQL 17 real) | 0 discrepancias de esquema | ✅ **Paridad 1:1 certificada (27 tablas + RLS PG17 en 27/27)** |
| **Lint, Tipado & SonarJS (Frontend)** | `make -C frontend qa-lint` (`vue-tsc`, `prettier`, `eslint`) | 0 errores / CC $\le 15$ | ✅ **100% Limpio (+ `0` hallazgos `modern-web-guidance legacy-scan`)** |
| **Cero Componentes UI Huérfanos** | `make -C frontend qa-orphans` | 100% componentes `.vue` con `.unit.ts` | ✅ **38/38 componentes cubiertos (`48` suites)** |
| **Pruebas Unitarias Frontend** | `make -C frontend qa-unit` (`vitest` + `coverage-v8`) | Cobertura $\ge 95\%$ | ✅ **99.52% líneas / 99.25% sentencias / 97.92% funciones / 95.45% ramas (117/117 pass)** |
| **Salud Topológica AST (Graphify)** | `python3 .agents/scripts/verify_topological_health.py` | 0 acoplamientos inversos | ✅ **2.504 nodos, 6.213 relaciones, 131 comunidades (0 violaciones en 3 grafos: 4.461 nodos, 11.421 relaciones)** |
| **E2E Chromium & WCAG 2.1 AA (Frontend)** | `ui-e2e` Playwright (`frontend/e2e/accessibility.e2e.ts`) contra `ui-prod` | 0 violaciones críticas/serias Axe + geometría viewport | ✅ **8/8 pass (`mobile-chromium` + `desktop-chromium`)** |
| **Contratos OpenAPI & Fuzzing** | `make -C backend qa-contracts` (`schemathesis`) | 0 fallos 5xx / contrato | ✅ **626/626 casos aprobados** |
| **Seguridad Dinámica (DAST)** | `make -C backend qa-dast` (`zaproxy/zap-stable`) | `FAIL-NEW: 0` | ✅ **0 fallos (66 reglas PASS)** |
| **Ingeniería del Caos & Carga** | `make -C backend qa-chaos` (`Pumba` + `Locust` + `Prometheus`) | 0 errores bajo `netem 500ms` | ✅ **2.786 peticiones, 0 fallos** |
| **Auditoría IaC & Contenedores** | `./scripts/auditar-infra.sh` (`trivy config` + `trivy fs`) | 0 HIGH/CRITICAL misconfigs & CVEs | ✅ **0 hallazgos** |

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
23. **Privacidad DTO en Unidades Públicas y Contratos de Cancelación de Reservas (Hito 17.4):** Verifica exposición mínima pública en `GET /api/estructura/unidades` + `UnidadPublicaResponse` en OpenAPI (sin campos financieros), verificación pública de solvencia inexistente (`404`), exigencia `Idempotency-Key` (`422`) y contención RBAC Fantasma (`403`) en `PUT /api/reservas/{reserva_id}/cancelar` (**23/23 pass en 2 ejecuciones consecutivas**).

> **Nota E2E UI (`frontend/test/ui_business_flow.feature` y Playwright):** El Escenario 9 (sesión, modales nativos `<dialog>` verificando `:modal` en Top Layer y rutas RBAC) quedó incorporado en `frontend/test/ui_business_flow.feature`, pero la imagen `sinfallas/karatelabs:latest` carece de `/usr/bin/google-chrome`, impidiendo ejecutar `karatelabs` UI en ese contenedor. Asimismo, `mcr.microsoft.com/playwright:v1.48.2-jammy` carece de `pnpm` y difiere de `@playwright/test@1.64.1`, por lo que la verificación real en navegador se ejecutó en `ui-e2e` contra `ui-prod` usando `./node_modules/.bin/playwright` con `chromium-headless-shell` en `/tmp/pw-browsers`, aprobando **8/8 pruebas** (`mobile-chromium` + `desktop-chromium`, 0 violaciones críticas o serias WCAG 2.1 AA incluyendo `#dialog-contextual-help` con `closedby="any"`, `autofocus` y `tabindex="0"` en `.help-dialog__body`; `0` hallazgos en `modern-web-guidance@latest legacy-scan src --json`).

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
